"""Modal deployment configuration for the LintPDF inference service.

Deploy:
    modal deploy src/inference_service/modal_deploy.py

Run locally with hot-reload:
    modal serve src/inference_service/modal_deploy.py
"""

import modal

# ---------------------------------------------------------------------------
# Modal app definition
# ---------------------------------------------------------------------------

app = modal.App("lintpdf-inference")

# ---------------------------------------------------------------------------
# GPU image with all inference dependencies
# ---------------------------------------------------------------------------

inference_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install(
        "libgl1-mesa-glx",
        "libglib2.0-0",
        "libsm6",
        "libxrender1",
        "libxext6",
    )
    .pip_install(
        "fastapi>=0.115.0",
        "uvicorn[standard]>=0.30.0",
        "python-multipart>=0.0.9",
        "Pillow>=10.0.0",
        "numpy>=1.24.0",
        # ML / AI frameworks — install torch with CUDA 12.1 index to match
        # Modal's A10G driver, avoiding CUDA version mismatch segfaults.
        "torch>=2.0.0",
        "torchvision>=0.15.0",
        "transformers>=4.40.0",
        "pyiqa>=0.1.10",
        "ultralytics>=8.0.0",
        "open-clip-torch>=2.24.0",
        "nudenet==3.4.1",
        # CPU-only PaddlePaddle — avoids CUDA conflicts on Modal; OCR is
        # fast enough on CPU while heavy GPU work uses PyTorch models.
        "paddlepaddle>=2.5.0",
        "paddleocr>=2.7.0",
    )
    # Bundle the local ``inference_service`` package into the image so
    # the ``serve_app`` entrypoint can import it. Modal's auto-mount
    # only picks up the deploy script itself; the surrounding package
    # has to be added explicitly. Without this the container fails on
    # ``ModuleNotFoundError: No module named 'inference_service'``.
    .add_local_python_source("inference_service")
)

# ---------------------------------------------------------------------------
# Persistent volume for cached model weights
# ---------------------------------------------------------------------------

model_cache = modal.Volume.from_name("lintpdf-model-cache", create_if_missing=True)

# ---------------------------------------------------------------------------
# Web endpoint (ASGI)
# ---------------------------------------------------------------------------


@app.function(
    image=inference_image,
    gpu="A10G",
    volumes={"/models": model_cache},
    secrets=[modal.Secret.from_name("lintpdf-inference-secrets")],
    # Scale profile (tuned 2026-04-21 session 2 — tier-1 measured
    # p50 job latency = 20 min on max_containers=5 with full-ai-scan;
    # 1.18.2 bumped to 15; this bump to 100 lets a 100-file burst
    # finish in one wave instead of seven.
    #
    # max_containers=100: burst ceiling, NOT a baseline. With
    #   min_containers=1 and scale-to-one (post-2026-04-28), Modal
    #   only charges for one warm container plus the actual warm-
    #   container time during bursts. Raising the cap from 15 to
    #   100 costs nothing extra until a workload actually fans out
    #   that wide. A 100-file burst consumes ~700 container-minutes
    #   either way; this bump changes wall clock from ~45 min →
    #   ~7 min at the same spend.
    # scaledown_window=180: unchanged — idle containers above the
    #   min retire in 3 min, keeping cost close to baseline between
    #   bursts.
    # min_containers=1: bumped from 0 (2026-04-28) to keep one
    #   container always warm. The post-merge audit-cycle smoke
    #   showed two real cold-start failures on the OCR
    #   ``/inference/detect-outlines`` endpoint where PaddleOCR's
    #   ~150-180 s first-hit latency exceeded the engine's per-call
    #   timeout, leaving ``page.detected_text_regions`` permanently
    #   ``None`` in production. Keeping one container warm
    #   eliminates the cold-start tax for the dominant single-job
    #   case at ~$0.40/day baseline cost.
    scaledown_window=180,
    min_containers=1,
    max_containers=100,
    timeout=300,
    memory=8192,
)
@modal.asgi_app()
def serve_app():
    """Return the full inference service ASGI application."""
    from inference_service.app import app as asgi_app

    return asgi_app
