"""FastAPI application for LintPDF inference service."""

from __future__ import annotations

import io
import logging
import time
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse

from inference_service.config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="LintPDF Inference Service",
    description="Vision inference service for LintPDF AI features",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# Lazy-loaded model singletons
# ---------------------------------------------------------------------------

_image_quality_model: Any = None
_classifier: Any = None
_logo_detector: Any = None
_nsfw_detector: Any = None
_object_detector: Any = None
_embedder: Any = None
_ocr_engine: Any = None
_symbol_detector: Any = None
_translator: Any = None


def _get_image_quality_model():
    global _image_quality_model  # skipcq: PYL-W0603
    if _image_quality_model is None:
        from inference_service.models.image_quality import ImageQualityModel

        _image_quality_model = ImageQualityModel()
    return _image_quality_model


def _get_classifier():
    global _classifier  # skipcq: PYL-W0603
    if _classifier is None:
        from inference_service.models.classifier import DocumentClassifier

        _classifier = DocumentClassifier()
    return _classifier


def _get_logo_detector():
    global _logo_detector  # skipcq: PYL-W0603
    if _logo_detector is None:
        from inference_service.models.logo_detector import LogoDetector

        _logo_detector = LogoDetector()
    return _logo_detector


def _get_nsfw_detector():
    global _nsfw_detector  # skipcq: PYL-W0603
    if _nsfw_detector is None:
        from inference_service.models.nsfw_detector import NSFWDetector

        _nsfw_detector = NSFWDetector()
    return _nsfw_detector


def _get_object_detector():
    global _object_detector  # skipcq: PYL-W0603
    if _object_detector is None:
        from inference_service.models.object_detector import ObjectDetector

        _object_detector = ObjectDetector()
    return _object_detector


def _get_embedder():
    global _embedder  # skipcq: PYL-W0603
    if _embedder is None:
        from inference_service.models.embedder import ImageEmbedder

        _embedder = ImageEmbedder()
    return _embedder


def _get_ocr_engine():
    global _ocr_engine  # skipcq: PYL-W0603
    if _ocr_engine is None:
        from inference_service.models.ocr import OCREngine

        _ocr_engine = OCREngine()
    return _ocr_engine


def _get_symbol_detector():
    global _symbol_detector  # skipcq: PYL-W0603
    if _symbol_detector is None:
        from inference_service.models.symbol_detector import SymbolDetector

        _symbol_detector = SymbolDetector()
    return _symbol_detector


def _get_translator():
    global _translator  # skipcq: PYL-W0603
    if _translator is None:
        from inference_service.models.translator import Translator

        _translator = Translator()
    return _translator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _read_image_bytes(image: UploadFile) -> bytes:
    """Read and validate uploaded image bytes."""
    data = await image.read()
    if not data:
        raise ValueError("Empty image file")
    return data


def _validate_image(data: bytes) -> None:
    """Quick validation that the bytes can be opened as an image."""
    from PIL import Image

    img = Image.open(io.BytesIO(data))
    w, h = img.size
    if w > settings.max_image_size or h > settings.max_image_size:
        raise ValueError(
            f"Image dimensions {w}x{h} exceed maximum {settings.max_image_size}"
        )


def _error_response(error: str, detail: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": error, "detail": detail},
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "grounded-inference",
        "device": settings.device,
    }


@app.post("/inference/image-quality")
async def image_quality(image: UploadFile = File(...)):
    """Assess image quality using MUSIQ metric."""
    try:
        data = await _read_image_bytes(image)
        _validate_image(data)
    except ValueError as exc:
        return _error_response("invalid_input", str(exc))
    except Exception as exc:
        return _error_response("invalid_input", f"Cannot read image: {exc}")

    start = time.perf_counter()
    try:
        model = _get_image_quality_model()
        result = model.predict(data)
    except Exception as exc:
        logger.exception("image-quality inference failed")
        return _error_response("inference_error", str(exc), status_code=500)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

    return {
        "result": result,
        "processing_time_ms": elapsed_ms,
        "model": "musiq",
    }


@app.post("/inference/classify")
async def classify(image: UploadFile = File(...)):
    """Classify a document / print image."""
    try:
        data = await _read_image_bytes(image)
        _validate_image(data)
    except ValueError as exc:
        return _error_response("invalid_input", str(exc))
    except Exception as exc:
        return _error_response("invalid_input", f"Cannot read image: {exc}")

    start = time.perf_counter()
    try:
        model = _get_classifier()
        result = model.predict(data)
    except Exception as exc:
        logger.exception("classify inference failed")
        return _error_response("inference_error", str(exc), status_code=500)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

    return {
        "result": result,
        "processing_time_ms": elapsed_ms,
        "model": "dit-base-finetuned-rvlcdip",
    }


@app.post("/inference/detect-logo")
async def detect_logo(image: UploadFile = File(...)):
    """Detect logos in an image using YOLOv8 + CLIP."""
    try:
        data = await _read_image_bytes(image)
        _validate_image(data)
    except ValueError as exc:
        return _error_response("invalid_input", str(exc))
    except Exception as exc:
        return _error_response("invalid_input", f"Cannot read image: {exc}")

    start = time.perf_counter()
    try:
        model = _get_logo_detector()
        result = model.detect(data)
    except Exception as exc:
        logger.exception("detect-logo inference failed")
        return _error_response("inference_error", str(exc), status_code=500)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

    return {
        "result": result,
        "processing_time_ms": elapsed_ms,
        "model": "yolov8n+openclip-vit-b-32",
    }


@app.post("/inference/detect-nsfw")
async def detect_nsfw(image: UploadFile = File(...)):
    """Detect NSFW content in an image."""
    try:
        data = await _read_image_bytes(image)
        _validate_image(data)
    except ValueError as exc:
        return _error_response("invalid_input", str(exc))
    except Exception as exc:
        return _error_response("invalid_input", f"Cannot read image: {exc}")

    start = time.perf_counter()
    try:
        model = _get_nsfw_detector()
        result = model.detect(data)
    except Exception as exc:
        logger.exception("detect-nsfw inference failed")
        return _error_response("inference_error", str(exc), status_code=500)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

    return {
        "result": result,
        "processing_time_ms": elapsed_ms,
        "model": "nudenet",
    }


@app.post("/inference/detect-objects")
async def detect_objects(
    image: UploadFile = File(...),
    prompt: str = Form(default="object"),
):
    """Detect objects matching a text prompt using Grounding DINO."""
    try:
        data = await _read_image_bytes(image)
        _validate_image(data)
    except ValueError as exc:
        return _error_response("invalid_input", str(exc))
    except Exception as exc:
        return _error_response("invalid_input", f"Cannot read image: {exc}")

    start = time.perf_counter()
    try:
        model = _get_object_detector()
        result = model.detect(data, prompt=prompt)
    except Exception as exc:
        logger.exception("detect-objects inference failed")
        return _error_response("inference_error", str(exc), status_code=500)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

    return {
        "result": result,
        "processing_time_ms": elapsed_ms,
        "model": "grounding-dino-tiny",
    }


@app.post("/inference/embed-image")
async def embed_image(image: UploadFile = File(...)):
    """Generate a DINOv2 embedding for an image."""
    try:
        data = await _read_image_bytes(image)
        _validate_image(data)
    except ValueError as exc:
        return _error_response("invalid_input", str(exc))
    except Exception as exc:
        return _error_response("invalid_input", f"Cannot read image: {exc}")

    start = time.perf_counter()
    try:
        model = _get_embedder()
        result = model.embed(data)
    except Exception as exc:
        logger.exception("embed-image inference failed")
        return _error_response("inference_error", str(exc), status_code=500)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

    return {
        "result": result,
        "processing_time_ms": elapsed_ms,
        "model": "dinov2-base",
    }


@app.post("/inference/detect-outlines")
async def detect_outlines(image: UploadFile = File(...)):
    """Detect text regions using OCR (PaddleOCR)."""
    try:
        data = await _read_image_bytes(image)
        _validate_image(data)
    except ValueError as exc:
        return _error_response("invalid_input", str(exc))
    except Exception as exc:
        return _error_response("invalid_input", f"Cannot read image: {exc}")

    start = time.perf_counter()
    try:
        model = _get_ocr_engine()
        result = model.detect(data)
    except Exception as exc:
        logger.exception("detect-outlines inference failed")
        return _error_response("inference_error", str(exc), status_code=500)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

    return {
        "result": result,
        "processing_time_ms": elapsed_ms,
        "model": "paddleocr",
    }


@app.post("/inference/detect-symbols")
async def detect_symbols(image: UploadFile = File(...)):
    """Detect regulatory symbols using CLIP template matching."""
    try:
        data = await _read_image_bytes(image)
        _validate_image(data)
    except ValueError as exc:
        return _error_response("invalid_input", str(exc))
    except Exception as exc:
        return _error_response("invalid_input", f"Cannot read image: {exc}")

    start = time.perf_counter()
    try:
        model = _get_symbol_detector()
        result = model.detect(data)
    except Exception as exc:
        logger.exception("detect-symbols inference failed")
        return _error_response("inference_error", str(exc), status_code=500)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

    return {
        "result": result,
        "processing_time_ms": elapsed_ms,
        "model": "openclip-vit-b-32",
    }


@app.post("/inference/translate")
async def translate(
    text: str = Form(...),
    source_lang: str = Form(default="en"),
    target_lang: str = Form(default="fr"),
):
    """Translate text between languages using OPUS-MT."""
    if not text or not text.strip():
        return _error_response("invalid_input", "Text is required")

    start = time.perf_counter()
    try:
        model = _get_translator()
        result = model.translate(
            text=text, source_lang=source_lang, target_lang=target_lang
        )
    except Exception as exc:
        logger.exception("translate inference failed")
        return _error_response("inference_error", str(exc), status_code=500)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

    return {
        "result": result,
        "processing_time_ms": elapsed_ms,
        "model": f"opus-mt-{source_lang}-{target_lang}",
    }
