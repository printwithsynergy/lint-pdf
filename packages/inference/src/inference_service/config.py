import os


def _resolve_device(requested: str) -> str:
    """Resolve the compute device, falling back to CPU if CUDA is unavailable."""
    if requested != "cuda":
        return requested
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"


class Settings:
    """Configuration settings for the inference service."""

    def __init__(self) -> None:
        self.model_cache_dir: str = os.environ.get("MODEL_CACHE_DIR", "/models")
        self.max_image_size: int = int(os.environ.get("MAX_IMAGE_SIZE", "4096"))
        self.device: str = _resolve_device(os.environ.get("DEVICE", "cuda"))


settings = Settings()
