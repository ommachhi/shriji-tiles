from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import fitz

from export_catalog_to_excel import export_to_excel
from extractor import DEFAULT_KOHLER_CACHE_PATH, DEFAULT_KOHLER_PDF_PATH, normalize_code

OUTPUT_EXCEL = "kohler_catalog_full.xlsx"
PRICE_NUMBER_PATTERN = re.compile(r"([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.\d{1,2})?|[0-9]+(?:\.\d{1,2})?)")
CODE_PATTERN = re.compile(r"\bK\s*-\s*[A-Z0-9-]+\b", re.I)
HEADER_PATTERN = re.compile(
    r"^\s*(?:MODEL(?:\s+DESCRIPTION)?\s+CODE(?:\s+DESCRIPTION)?(?:\s+RUNNING\s+LENGTH)?(?:\s+SIZE)?\s+MRP)\s*",
    re.I,
)
MRP_TAIL_PATTERN = re.compile(r"\bMRP\b.*$", re.I)
BANNED_COLOR_TOKENS = ("MRP", "MODEL", "UPTO", "HEIGHT", "INCL", "ROUGH", "COMPATIBLE", "K-")


def _clean_price_text(text: str) -> str:
    cleaned = str(text or "")
    cleaned = CODE_PATTERN.sub(" ", cleaned)
    cleaned = re.sub(r",\s+", ",", cleaned)
    cleaned = re.sub(r"\s+\.\s*", ".", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _extract_prices_from_text(text: str) -> list[int]:
    values = []
    for token in PRICE_NUMBER_PATTERN.findall(_clean_price_text(text)):
        try:
            value = float(token.replace(",", ""))
        except ValueError:
            continue
        if value > 10:
            values.append(int(round(value)))
    return values


def _clean_kohler_copy(text: str) -> str:
    cleaned = _clean_price_text(text)
    cleaned = HEADER_PATTERN.sub("", cleaned)
    cleaned = CODE_PATTERN.sub(" ", cleaned)
    cleaned = MRP_TAIL_PATTERN.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -:,.;")
    return cleaned


def _clean_kohler_color(value: str | None) -> str | None:
    cleaned = _clean_kohler_copy(str(value or ""))
    if not cleaned:
        return None
    if any(token in cleaned.upper() for token in BANNED_COLOR_TOKENS):
        return None
    if any(char.isdigit() for char in cleaned):
        return None
    return cleaned


def clean_kohler_products(products: list[dict]) -> list[dict]:
    for product in products:
        cleaned_name = _clean_kohler_copy(str(product.get("name") or ""))
        cleaned_details = _clean_kohler_copy(str(product.get("details") or ""))
        if cleaned_name:
            product["name"] = cleaned_name
        if cleaned_details:
            product["details"] = cleaned_details
        product["color"] = _clean_kohler_color(product.get("color"))
    return products


def _page_lines(page: fitz.Page) -> list[dict]:
    line_words: dict[tuple[int, int], list[tuple]] = {}
    for word in page.get_text("words"):
        key = (int(word[5]), int(word[6]))
        line_words.setdefault(key, []).append(word)

    lines = []
    for words in line_words.values():
        words.sort(key=lambda item: int(item[7]))
        text = " ".join(str(word[4]).strip() for word in words if str(word[4]).strip())
        if not text:
            continue
        rect = fitz.Rect(
            min(float(word[0]) for word in words),
            min(float(word[1]) for word in words),
            max(float(word[2]) for word in words),
            max(float(word[3]) for word in words),
        )
        prices = _extract_prices_from_text(text) if "MRP" in text.upper() else []
        lines.append({"text": text, "rect": rect, "prices": prices})

    return lines


def _guess_price_from_page(page: fitz.Page, code: str) -> int | None:
    code_key = normalize_code(code)
    lines = _page_lines(page)
    code_lines = [line for line in lines if code_key in normalize_code(line["text"])]
    if not code_lines:
        return None

    best_price = None
    best_cost = float("inf")
    for code_line in code_lines:
        code_center_y = (code_line["rect"].y0 + code_line["rect"].y1) / 2.0
        for line in lines:
            if not line["prices"]:
                continue
            price_center_y = (line["rect"].y0 + line["rect"].y1) / 2.0
            dy = abs(code_center_y - price_center_y)
            dx_penalty = 0.0 if line["rect"].x0 >= code_line["rect"].x1 - 10 else 80.0
            cost = dy * 3.0 + dx_penalty
            if cost < best_cost:
                best_cost = cost
                best_price = max(line["prices"])
    return best_price


def repair_low_prices(
    products: list[dict],
    pdf_path: Path | str = DEFAULT_KOHLER_PDF_PATH,
    threshold: int = 100,
) -> tuple[list[dict], list[dict]]:
    pdf_path = Path(pdf_path)
    changes: list[dict] = []

    if not pdf_path.exists():
        return products, changes

    with fitz.open(pdf_path) as document:
        for product in products:
            try:
                current_price = int(product.get("price") or 0)
            except (TypeError, ValueError):
                current_price = 0

            if current_price > threshold:
                continue

            combined_text = " ".join(
                str(product.get(field) or "").strip() for field in ("name", "details", "size", "color")
            )
            candidates = _extract_prices_from_text(combined_text)

            page_number = int(product.get("page_number") or 0)
            if 0 <= page_number < len(document):
                guessed = _guess_price_from_page(document.load_page(page_number), str(product.get("code") or ""))
                if guessed:
                    candidates.append(guessed)

            if not candidates:
                continue

            new_price = max(candidates)
            if new_price <= threshold or new_price == current_price:
                continue

            changes.append(
                {
                    "code": product.get("code"),
                    "old_price": current_price,
                    "new_price": new_price,
                    "page_number": page_number,
                }
            )
            product["price"] = new_price

    return clean_kohler_products(products), changes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fix obvious low OCR prices in the Kohler catalog outputs.")
    parser.add_argument("--threshold", type=int, default=100, help="Repair prices less than or equal to this value.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent
    cache_path = Path(DEFAULT_KOHLER_CACHE_PATH)
    if not cache_path.exists():
        raise FileNotFoundError(f"Cache file not found: {cache_path}")

    products = json.loads(cache_path.read_text(encoding="utf-8"))
    products = clean_kohler_products(products)
    products, changes = repair_low_prices(products, threshold=args.threshold)
    cache_path.write_text(json.dumps(products, indent=2, ensure_ascii=False), encoding="utf-8")
    export_to_excel(products, base_dir / OUTPUT_EXCEL)

    print(f"changes={len(changes)}")
    print(f"cache={cache_path.name}")
    print(f"excel={OUTPUT_EXCEL}")
    for change in changes[:25]:
        print(change)


if __name__ == "__main__":
    main()
