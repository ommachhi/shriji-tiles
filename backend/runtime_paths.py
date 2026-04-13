from __future__ import annotations

import os
import sys
from pathlib import Path


def get_backend_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent


def get_images_dir() -> Path:
    custom_images_dir = os.environ.get("PRODUCT_CATALOG_IMAGES_DIR", "").strip()
    if custom_images_dir:
        return Path(custom_images_dir).resolve()
    return get_backend_base_dir() / "images"
