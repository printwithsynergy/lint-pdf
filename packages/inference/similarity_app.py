"""Slim Modal app — OpenCLIP embedding for duplicate-detector inspector.

The only Modal survivor after the wholesale Claude pivot (WS-A).
Every other Modal surface (audit, narrow inference monolith) is
gone; this app is a single ~50-line ASGI wrapper around the
OpenCLIP ViT-L-14 image encoder. Used exclusively by
``lintpdf.analyzers.similarity`` on the engine side.

Deploy:
    modal deploy packages/inference/similarity_app.py

Env:
    LINTPDF_SIMILARITY_MODAL_URL  consumed by the engine after
                                  ``modal deploy`` emits the URL.
"""

from __future__ import annotations

import base64
import io
from typing import Any

import modal

app = modal.App("lintpdf-similarity")

# Base image — keep the tag pinned. The OpenCLIP checkpoint is ~1.7GB;
# baking it into the image saves a cold-start download every time
# Modal scales to a fresh container.
similarity_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install(
        "torch==2.3.0",
        "torchvision==0.18.0",
        "open_clip_torch==2.24.0",
        "pillow>=10.0.0",
        "fastapi>=0.115.0",
    )
    .run_commands(
        # Pre-download the ViT-L-14 checkpoint at image-build time so
        # the container never calls HuggingFace from user turf.
        "python -c 'import open_clip; open_clip.create_model_and_transforms(\"ViT-L-14\", pretrained=\"openai\")'"
    )
)


@app.cls(
    image=similarity_image,
    gpu="A10G",
    # Scale-to-zero on 5 min of idle. Cold starts on A10G
    # with the baked checkpoint are ~15-20s — acceptable for
    # the duplicate-detector use case.
    scaledown_window=300,
    max_containers=4,
    timeout=60,
)
class SimilarityService:
    @modal.enter()
    def load_model(self) -> None:
        import open_clip
        import torch

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        (
            self.model,
            _preprocess_train,
            self.preprocess,
        ) = open_clip.create_model_and_transforms(
            "ViT-L-14", pretrained="openai"
        )
        self.model.to(self.device).eval()
        self.torch = torch
        self.np = __import__("numpy")

    @modal.asgi_app()
    def api(self):
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel

        app = FastAPI()

        class EmbedRequest(BaseModel):
            png_base64: str

        class EmbedResponse(BaseModel):
            embedding: list[float]
            dim: int

        @app.get("/ready")
        def ready() -> dict[str, Any]:
            return {"status": "ok", "model": "openclip-vit-l-14"}

        @app.post("/embed", response_model=EmbedResponse)
        def embed(req: EmbedRequest) -> EmbedResponse:
            try:
                png_bytes = base64.b64decode(req.png_base64)
            except Exception as exc:
                raise HTTPException(
                    status_code=400, detail=f"png_base64 decode failed: {exc!s}"
                ) from exc

            from PIL import Image

            img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
            tensor = self.preprocess(img).unsqueeze(0).to(self.device)
            with self.torch.no_grad():
                features = self.model.encode_image(tensor)
                features = features / features.norm(dim=-1, keepdim=True)
            vec = features.squeeze(0).cpu().numpy().tolist()
            return EmbedResponse(embedding=vec, dim=len(vec))

        return app
