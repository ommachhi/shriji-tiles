from __future__ import annotations

import argparse
import json
from pathlib import Path

from export_catalog_to_excel import export_to_excel
from extractor import (
    DEFAULT_IMAGES_DIR,
    DEFAULT_KOHLER_CACHE_PATH,
    DEFAULT_KOHLER_PDF_PATH,
    ensure_product_preview,
    extract_products_from_pdf,
    image_relative_path,
    normalize_code,
)
from fix_kohler_low_prices import repair_low_prices

OUTPUT_EXCEL = "kohler_catalog_full.xlsx"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild Kohler catalog cache, Excel, and preview images.")
    parser.add_argument("--start-page", type=int, default=1, help="Start page number (1-based).")
    parser.add_argument("--end-page", type=int, default=168, help="End page number (1-based).")
    parser.add_argument(
        "--force-images",
        action="store_true",
        help="Re-render preview images even if files already exist.",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Merge this page range into the existing Kohler cache/excel instead of replacing it.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    base_dir = Path(__file__).resolve().parent
    images_dir = Path(DEFAULT_IMAGES_DIR)
    images_dir.mkdir(parents=True, exist_ok=True)
    (images_dir / "Kohler").mkdir(parents=True, exist_ok=True)

    if args.force_images:
        for preview_file in (images_dir / "Kohler").glob("*.png"):
            try:
                preview_file.unlink()
            except OSError:
                pass

    page_range = (max(args.start_page, 1), max(args.end_page, max(args.start_page, 1)))
    products = extract_products_from_pdf(
        pdf_path=DEFAULT_KOHLER_PDF_PATH,
        page_range=page_range,
        source_key="kohler",
        source_label="Kohler",
    )

    for product in products:
        product["source"] = "kohler"
        product["source_label"] = "Kohler"
        image_path = ensure_product_preview(
            product,
            pdf_path=DEFAULT_KOHLER_PDF_PATH,
            images_dir=images_dir,
            force=args.force_images,
        )
        product["image"] = image_path
        product["image_file"] = image_relative_path(image_path)

    cache_path = Path(DEFAULT_KOHLER_CACHE_PATH)
    if args.append and cache_path.exists():
        try:
            existing_products = json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing_products = []
    else:
        existing_products = []

    merged_by_code = {}
    for item in existing_products:
        if not isinstance(item, dict):
            continue
        code_key = normalize_code(item.get("code", ""))
        if code_key:
            merged_by_code[code_key] = item

    for product in products:
        code_key = normalize_code(product.get("code", ""))
        if code_key:
            merged_by_code[code_key] = product

    merged_products = sorted(
        merged_by_code.values(),
        key=lambda item: (str(item.get("code", "")), str(item.get("name", ""))),
    )

    merged_products, price_changes = repair_low_prices(merged_products)
    cache_path.write_text(json.dumps(merged_products, indent=2, ensure_ascii=False), encoding="utf-8")

    excel_path = base_dir / OUTPUT_EXCEL
    export_to_excel(merged_products, excel_path)

    print(f"range_products={len(products)}")
    print(f"merged_products={len(merged_products)}")
    print(f"price_repairs={len(price_changes)}")
    print(f"cache={cache_path.name}")
    print(f"excel={excel_path.name}")
    print(f"images_dir={images_dir / 'Kohler'}")


if __name__ == "__main__":
    main()
