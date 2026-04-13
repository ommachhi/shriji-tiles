#!/usr/bin/env python3
"""Regenerate all product images with improved cropping."""

from pathlib import Path
from regenerate_aquant_p4_49_images import regenerate_images_from_excel

def main() -> None:
    base_dir = Path(__file__).resolve().parent
    images_dir = base_dir / "images"
    excel_path = base_dir / "aquant_catalog_full.xlsx"

    if not excel_path.exists():
        print(f"Excel not found: {excel_path}")
        return

    # Delete old images
    removed = 0
    for image_file in images_dir.rglob("*.png"):
        try:
            image_file.unlink()
            removed += 1
        except Exception:
            pass
    for folder in sorted((path for path in images_dir.rglob("*") if path.is_dir()), key=lambda item: len(item.parts), reverse=True):
        try:
            folder.rmdir()
        except OSError:
            pass
    print(f"Removed old images: {removed}")

    # Regenerate with improved cropping
    regenerated, skipped, removed_unreferenced = regenerate_images_from_excel(excel_path, images_dir)
    print(f"Regenerated: {regenerated}")
    print(f"Skipped: {skipped}")
    print(f"Removed unreferenced: {removed_unreferenced}")

if __name__ == "__main__":
    main()
