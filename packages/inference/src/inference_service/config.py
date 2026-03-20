import os


class Settings:
    """Configuration settings for the inference service."""

    def __init__(self) -> None:
        self.model_cache_dir: str = os.environ.get("MODEL_CACHE_DIR", "/models")
        self.max_image_size: int = int(os.environ.get("MAX_IMAGE_SIZE", "4096"))
        self.device: str = os.environ.get("DEVICE", "cuda")


settings = Settings()
