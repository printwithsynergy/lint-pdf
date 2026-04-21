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
    #   min_containers=0 and scale-to-zero, Modal only charges for
    #   actual warm-container time — so raising the cap from 15 to
    #   100 costs zero until a workload actually fans out that wide.
    #   A 100-file burst consumes ~700 container-minutes either way;
    #   this bump changes wall clock from ~45 min → ~7 min at the
    #   same spend.
    # scaledown_window=180: unchanged — idle containers retire in
    #   3 min, keeping cost close to zero between bursts.
    # min_containers=0: unchanged — pure scale-to-zero, no baseline cost.
    scaledown_window=180,
    min_containers=0,
    max_containers=100,
    timeout=300,
    memory=8192,
)
@modal.asgi_app()
def serve_app():
    """Return the full inference service ASGI application."""
    from inference_service.app import app as asgi_app

    return asgi_app
