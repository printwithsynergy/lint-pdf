"""Tests for the inference service FastAPI endpoints.

Uses httpx TestClient to exercise each endpoint without requiring GPU
dependencies.  Model classes gracefully degrade to placeholder mode when
the underlying ML libraries are not installed.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

# Ensure the source package is importable
_src = str(Path(__file__).resolve().parent.parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from fastapi.testclient import TestClient  # noqa: E402

from inference_service.app import app  # noqa: E402

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_test_image(width: int = 64, height: int = 64) -> bytes:
    """Create a small valid PNG image in memory."""
    from PIL import Image

    img = Image.new("RGB", (width, height), color=(128, 128, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "grounded-inference"


# ---------------------------------------------------------------------------
# Image quality
# ---------------------------------------------------------------------------


def test_image_quality():
    image_bytes = _make_test_image()
    response = client.post(
        "/inference/image-quality",
        files={"image": ("test.png", image_bytes, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert "processing_time_ms" in data
    assert "model" in data
    assert "score" in data["result"]


# ---------------------------------------------------------------------------
# Classify
# ---------------------------------------------------------------------------


def test_classify():
    image_bytes = _make_test_image()
    response = client.post(
        "/inference/classify",
        files={"image": ("test.png", image_bytes, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert "category" in data["result"]
    assert "confidence" in data["result"]
    assert "top_3" in data["result"]


# ---------------------------------------------------------------------------
# Detect logo
# ---------------------------------------------------------------------------


def test_detect_logo():
    image_bytes = _make_test_image()
    response = client.post(
        "/inference/detect-logo",
        files={"image": ("test.png", image_bytes, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert "detections" in data["result"]


# ---------------------------------------------------------------------------
# Detect NSFW
# ---------------------------------------------------------------------------


def test_detect_nsfw():
    image_bytes = _make_test_image()
    response = client.post(
        "/inference/detect-nsfw",
        files={"image": ("test.png", image_bytes, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert "detections" in data["result"]


# ---------------------------------------------------------------------------
# Detect objects
# ---------------------------------------------------------------------------


def test_detect_objects():
    image_bytes = _make_test_image()
    response = client.post(
        "/inference/detect-objects",
        files={"image": ("test.png", image_bytes, "image/png")},
        data={"prompt": "logo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert "detections" in data["result"]


# ---------------------------------------------------------------------------
# Embed image
# ---------------------------------------------------------------------------


def test_embed_image():
    image_bytes = _make_test_image()
    response = client.post(
        "/inference/embed-image",
        files={"image": ("test.png", image_bytes, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert "embedding" in data["result"]
    assert "dimension" in data["result"]


# ---------------------------------------------------------------------------
# Detect outlines (OCR)
# ---------------------------------------------------------------------------


def test_detect_outlines():
    image_bytes = _make_test_image()
    response = client.post(
        "/inference/detect-outlines",
        files={"image": ("test.png", image_bytes, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert "text_regions" in data["result"]


# ---------------------------------------------------------------------------
# Detect symbols
# ---------------------------------------------------------------------------


def test_detect_symbols():
    image_bytes = _make_test_image()
    response = client.post(
        "/inference/detect-symbols",
        files={"image": ("test.png", image_bytes, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert "symbols" in data["result"]


# ---------------------------------------------------------------------------
# Translate
# ---------------------------------------------------------------------------


def test_translate():
    response = client.post(
        "/inference/translate",
        data={"text": "Hello world", "source_lang": "en", "target_lang": "fr"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert "translated_text" in data["result"]
    assert data["result"]["source_lang"] == "en"
    assert data["result"]["target_lang"] == "fr"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_image_quality_empty_file():
    """Uploading an empty file should return an error."""
    response = client.post(
        "/inference/image-quality",
        files={"image": ("empty.png", b"", "image/png")},
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data


def test_image_quality_invalid_file():
    """Uploading non-image data should return an error."""
    response = client.post(
        "/inference/image-quality",
        files={"image": ("bad.png", b"not an image", "image/png")},
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data


def test_translate_empty_text():
    """Empty text should return an error."""
    response = client.post(
        "/inference/translate",
        data={"text": "", "source_lang": "en", "target_lang": "fr"},
    )
    # FastAPI may reject the empty form or our handler catches it
    assert response.status_code in (400, 422)


def test_missing_image_field():
    """Omitting the image field should return a 422."""
    response = client.post("/inference/classify")
    assert response.status_code == 422
