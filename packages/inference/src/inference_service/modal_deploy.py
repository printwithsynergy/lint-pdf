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

app = modal.App("grounded-inference")

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
        # ML / AI frameworks
        "torch>=2.0.0",
        "torchvision>=0.15.0",
        "transformers>=4.40.0",
        "pyiqa>=0.1.10",
        "ultralytics>=8.0.0",
        "open-clip-torch>=2.24.0",
        "nudenet>=3.4.0",
        "paddlepaddle-gpu>=2.5.0",
        "paddleocr>=2.7.0",
    )
)

# ---------------------------------------------------------------------------
# Persistent volume for cached model weights
# ---------------------------------------------------------------------------

model_cache = modal.Volume.from_name("grounded-model-cache", create_if_missing=True)

# ---------------------------------------------------------------------------
# Web endpoint (ASGI)
# ---------------------------------------------------------------------------


@app.function(
    image=inference_image,
    gpu="A10G",
    volumes={"/models": model_cache},
    secrets=[modal.Secret.from_name("grounded-inference-secrets")],
    scaledown_window=300,
    min_containers=0,
    max_containers=5,
)
@modal.asgi_app()
def serve_app():
    """Return the full inference service ASGI application."""
    from inference_service.app import app as asgi_app

    return asgi_app
