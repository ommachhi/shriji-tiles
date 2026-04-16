from __future__ import annotations

import json
import re
from pathlib import Path

import fitz

from export_catalog_to_excel import export_to_excel
from extractor import (
    DEFAULT_KOHLER_CACHE_PATH,
    DEFAULT_KOHLER_PDF_PATH,
    extract_products_from_pdf,
    normalize_code,
)

OUTPUT_EXCEL = "kohler_catalog_full.xlsx"

PRIORITY_CODES = [
    "K-1404IN-K-0",
    "K-1709IN-K-0",
    "K-18777IN-K-0",
    "K-20627IN-K-0",
    "K-72830IN-L-AF",
    "K-72830IN-L-BL",
    "K-97167IN-AF",
    "K-97167IN-BL",
    "K-97168IN-AF",
    "K-97168IN-BL",
]

MRP_PATTERN = re.compile(r"MRP\s*[`'\s]*([0-9]{1,3}(?:,[0-9]{2,3})+|[0-9]+)(?:\.\d{1,2})?", re.I)


def _parse_amount(value: str) -> int | None:
    digits = re.sub(r"[^0-9]", "", str(value or ""))
    if not digits:
        return None
    return int(digits)


def _normalized(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "")).upper()


def _find_price_and_page_from_pdf(pdf_path: Path, code: str) -> tuple[int | None, int | None]:
    target = _normalized(code)
    with fitz.open(pdf_path) as doc:
        for page_index, page in enumerate(doc):
            lines = [line.strip() for line in page.get_text("text").splitlines() if line.strip()]
            normalized_lines = [_normalized(line) for line in lines]

            for idx, norm_line in enumerate(normalized_lines):
                if target not in norm_line:
                    continue

                # Prefer MRP below the code line.
                for j in range(idx, min(len(lines), idx + 10)):
                    match = MRP_PATTERN.search(lines[j])
                    if match:
                        amount = _parse_amount(match.group(1))
                        if amount and amount > 0:
                            return amount, page_index

                # Fallback: nearby lines above.
                for j in range(max(0, idx - 4), idx):
                    match = MRP_PATTERN.search(lines[j])
                    if match:
                        amount = _parse_amount(match.group(1))
                        if amount and amount > 0:
                            return amount, page_index

    return None, None


def _best_extracted_row_for_code(pdf_path: Path, code: str, page_number: int | None) -> dict:
    if page_number is None:
        rows = extract_products_from_pdf(pdf_path=pdf_path, page_range=None, source_key="kohler", source_label="Kohler")
    else:
        page_1_based = page_number + 1
        rows = extract_products_from_pdf(
            pdf_path=pdf_path,
            page_range=(page_1_based, page_1_based),
            source_key="kohler",
            source_label="Kohler",
        )

    key = normalize_code(code)
    candidates = [row for row in rows if normalize_code(row.get("code", "")) == key]
    if not candidates:
        return {}

    # Choose most descriptive row.
    candidates.sort(
        key=lambda row: (
            len(str(row.get("name", "") or "")) + len(str(row.get("details", "") or "")),
            1 if row.get("image") else 0,
        ),
        reverse=True,
    )
    return candidates[0]


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    cache_path = Path(DEFAULT_KOHLER_CACHE_PATH)
    pdf_path = Path(DEFAULT_KOHLER_PDF_PATH)

    if not cache_path.exists():
        raise FileNotFoundError(f"Cache file not found: {cache_path}")
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    products = json.loads(cache_path.read_text(encoding="utf-8"))
    by_code = {normalize_code(item.get("code", "")): item for item in products if item.get("code")}

    updates: list[tuple[str, int, int]] = []
    inserts: list[tuple[str, int]] = []
    missing: list[str] = []

    for code in PRIORITY_CODES:
        actual_price, page_number = _find_price_and_page_from_pdf(pdf_path, code)
        if not actual_price:
            missing.append(code)
            continue

        key = normalize_code(code)
        existing = by_code.get(key)

        if existing is not None:
            old_price = int(existing.get("price") or 0)
            if old_price != actual_price:
                existing["price"] = actual_price
                updates.append((code, old_price, actual_price))
            continue

        row = _best_extracted_row_for_code(pdf_path, code, page_number)
        new_item = {
            "code": code,
            "name": row.get("name") or code,
            "price": actual_price,
            "color": row.get("color"),
            "details": row.get("details") or row.get("name") or code,
            "size": row.get("size"),
            "image": row.get("image") or f"/images/Kohler/{code}.png",
            "page_number": row.get("page_number") if row.get("page_number") is not None else page_number,
            "image_bbox": row.get("image_bbox"),
            "source": "kohler",
            "source_label": "Kohler",
        }
        products.append(new_item)
        by_code[key] = new_item
        inserts.append((code, actual_price))

    products.sort(key=lambda item: (str(item.get("code", "")), str(item.get("name", ""))))
    cache_path.write_text(json.dumps(products, indent=2, ensure_ascii=False), encoding="utf-8")

    excel_path = base_dir / OUTPUT_EXCEL
    export_to_excel(products, excel_path)

    print(f"priority_codes={len(PRIORITY_CODES)}")
    print(f"updated={len(updates)}")
    print(f"inserted={len(inserts)}")
    print(f"missing_in_pdf={len(missing)}")
    print(f"cache={cache_path.name}")
    print(f"excel={excel_path.name}")

    for code, old_price, new_price in updates:
        print(f"UPDATE {code}: {old_price} -> {new_price}")
    for code, price in inserts:
        print(f"INSERT {code}: {price}")
    for code in missing:
        print(f"MISSING {code}")


if __name__ == "__main__":
    main()
