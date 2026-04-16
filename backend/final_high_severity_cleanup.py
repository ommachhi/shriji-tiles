from __future__ import annotations

import json
from pathlib import Path

from export_catalog_to_excel import export_to_excel
from extractor import DEFAULT_IMAGES_DIR, DEFAULT_KOHLER_PDF_PATH, ensure_product_preview

BASE_DIR = Path(__file__).resolve().parent
CACHE_PATH = BASE_DIR / "kohler_cache.json"
EXCEL_PATH = BASE_DIR / "kohler_catalog_full.xlsx"

# Names derived from PDF table rows for these exact codes.
NAME_FIXES = {
    "K-702239IN-RH0-AF": "Framed Door Right Out",
    "K-702239IN-RH0-BL": "Framed Door Right Out",
    "K-702239IN-RH0-RGD": "Framed Door Right Out",
    "K-702241IN-RH0-AF": "Framed 1D1P-S Right Out",
    "K-702241IN-RH0-BL": "Framed 1D1P-S Right Out",
    "K-702241IN-RH0-RGD": "Framed 1D1P-S Right Out",
}

IMAGE_FIX_CODES = [
    "K-38896IN-4FS",
    "K-72830IN-L-AF",
    "K-72830IN-L-BL",
    "K-97167IN-AF",
    "K-97167IN-BL",
    "K-97168IN-AF",
    "K-97168IN-BL",
    "K-11628IN-BL",
    "K-16347IN-AF",
    "K-25348IN-BRD",
    "K-8524T-BV",
]


def main() -> None:
    data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))

    by_code = {str(item.get("code", "")).upper(): item for item in data}

    name_updates = 0
    details_updates = 0

    for code, fixed_name in NAME_FIXES.items():
        item = by_code.get(code)
        if not item:
            continue
        if str(item.get("name") or "").strip() != fixed_name:
            item["name"] = fixed_name
            name_updates += 1
        if not str(item.get("details") or "").strip():
            item["details"] = fixed_name
            details_updates += 1

    # Force regenerate previews from final cache metadata.
    image_updates = 0
    image_missing_after = []
    small_after = []

    images_dir = Path(DEFAULT_IMAGES_DIR)

    for code in IMAGE_FIX_CODES:
        item = by_code.get(code)
        if not item:
            continue

        current_image = str(item.get("image") or "").strip()
        if not current_image:
            item["image"] = f"/images/Kohler/{code}.png"
            current_image = item["image"]

        ensure_product_preview(
            product=item,
            pdf_path=DEFAULT_KOHLER_PDF_PATH,
            images_dir=images_dir,
            force=True,
        )

        image_file = Path(str(item.get("image") or "").split("?", 1)[0]).name
        file_path = images_dir / "Kohler" / image_file
        if not file_path.exists():
            image_missing_after.append(code)
        else:
            image_updates += 1
            size = file_path.stat().st_size
            if size < 5000:
                small_after.append((code, size))

    CACHE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    export_to_excel(data, EXCEL_PATH)

    print(f"name_updates={name_updates}")
    print(f"details_updates={details_updates}")
    print(f"images_processed={image_updates}")
    print(f"images_missing_after={len(image_missing_after)}")
    for code in image_missing_after:
        print(f"MISSING {code}")
    print(f"small_images_after={len(small_after)}")
    for code, size in small_after:
        print(f"SMALL {code} {size}")


if __name__ == "__main__":
    main()
