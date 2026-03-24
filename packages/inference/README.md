# LintPDF Inference Service

GPU inference service for LintPDF AI features. Deployed as a FastAPI application on [Modal](https://modal.com) for GPU model serving.

## Endpoints

| Endpoint                     | Method | Description                         |
| ---------------------------- | ------ | ----------------------------------- |
| `/health`                    | GET    | Health check                        |
| `/inference/image-quality`   | POST   | Image quality assessment (MUSIQ)    |
| `/inference/classify`        | POST   | Document/print classification (DiT) |
| `/inference/detect-logo`     | POST   | Logo detection (YOLOv8 + CLIP)      |
| `/inference/detect-nsfw`     | POST   | NSFW content detection (NudeNet)    |
| `/inference/detect-objects`  | POST   | Object detection (Grounding DINO)   |
| `/inference/embed-image`     | POST   | Image embedding (DINOv2)            |
| `/inference/detect-outlines` | POST   | OCR text detection (PaddleOCR)      |
| `/inference/detect-symbols`  | POST   | Regulatory symbol detection (CLIP)  |
| `/inference/translate`       | POST   | Text translation (OPUS-MT)          |

All image endpoints accept multipart file upload with field name `image`.

## Deploy on Modal

```bash
modal deploy src/inference_service/modal_deploy.py
```

## Run locally (hot-reload)

```bash
modal serve src/inference_service/modal_deploy.py
```

## Environment Variables

| Variable          | Description                                             |
| ----------------- | ------------------------------------------------------- |
| `MODEL_CACHE_DIR` | Directory for cached model weights (default: `/models`) |
| `MAX_IMAGE_SIZE`  | Maximum image dimension in pixels (default: `4096`)     |
| `DEVICE`          | Compute device (default: `cuda`)                        |
