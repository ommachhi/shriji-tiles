from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import fitz

from extractor import (
    DEFAULT_IMAGES_DIR,
    DEFAULT_KOHLER_CACHE_PATH,
    DEFAULT_KOHLER_PDF_PATH,
    image_relative_path,
    normalize_code,
)

KOHLER_CODE_PATTERN = re.compile(r"^K-[A-Z0-9-]+$", re.I)


def clean_code(value: str) -> str:
    code = str(value or "").strip().upper()
    code = re.sub(r"\s+", "", code)
    return code


def collect_code_rects(page: fitz.Page) -> dict[str, list[fitz.Rect]]:
    by_code: dict[str, list[fitz.Rect]] = defaultdict(list)

    # First pass: word-level extraction is usually most precise for row matching.
    for word in page.get_text("words"):
        if len(word) < 5:
            continue
        token = str(word[4] or "").strip().strip(".,;:()[]{}")
        code = clean_code(token)
        if not KOHLER_CODE_PATTERN.match(code):
            continue
        by_code[code].append(fitz.Rect(word[0], word[1], word[2], word[3]))

    # Fallback pass: block-level extraction captures cases where OCR grouping misses words.
    for block in page.get_text("dict").get("blocks", []):
        if block.get("type") != 0:
            continue
        text = " ".join(
            span.get("text", "")
            for line in block.get("lines", [])
            for span in line.get("spans", [])
        )
        if not text:
            continue
        for match in re.finditer(r"\bK-[A-Z0-9-]+\b", text, re.I):
            code = clean_code(match.group(0))
            if not KOHLER_CODE_PATTERN.match(code):
                continue
            by_code[code].append(fitz.Rect(*block.get("bbox", (0, 0, 0, 0))))

    return by_code


def collect_image_rects(page: fitz.Page) -> list[fitz.Rect]:
    rects: list[fitz.Rect] = []
    for block in page.get_text("dict").get("blocks", []):
        if block.get("type") != 1:
            continue
        rect = fitz.Rect(*block.get("bbox", (0, 0, 0, 0)))
        if rect.width < 16 or rect.height < 16:
            continue
        rects.append(rect)
    return rects


def row_band_for_rect(target: fitz.Rect, same_page_code_rects: list[fitz.Rect]) -> tuple[float, float]:
    center_y = (target.y0 + target.y1) / 2.0
    centers = sorted((r.y0 + r.y1) / 2.0 for r in same_page_code_rects)

    previous_center = None
    next_center = None
    for y in centers:
        if y < center_y:
            previous_center = y
        elif y > center_y and next_center is None:
            next_center = y
            break

    top = (previous_center + center_y) / 2.0 if previous_center is not None else center_y - 26.0
    bottom = (center_y + next_center) / 2.0 if next_center is not None else center_y + 26.0
    if bottom <= top:
        top, bottom = center_y - 24.0, center_y + 24.0
    return top, bottom


def pick_row_image(code_rect: fitz.Rect, all_code_rects: list[fitz.Rect], image_rects: list[fitz.Rect]) -> fitz.Rect | None:
    band_top, band_bottom = row_band_for_rect(code_rect, all_code_rects)
    code_center_y = (code_rect.y0 + code_rect.y1) / 2.0

    best: fitz.Rect | None = None
    best_cost = float("inf")

    def _score(image_rect: fitz.Rect, overlap_ratio: float, y_soft_penalty: float) -> float:
        image_center_y = (image_rect.y0 + image_rect.y1) / 2.0
        center_gap_y = abs(code_center_y - image_center_y)

        # Prefer left column images for each row in Kohler layout.
        left_penalty = 0.0 if image_rect.x1 <= code_rect.x0 + 36 else 140.0
        horizontal_gap = abs(code_rect.x0 - image_rect.x1)

        size_penalty = 0.0
        if image_rect.width * image_rect.height < 1800:
            size_penalty += 180.0
        if image_rect.width > code_rect.width * 6.0:
            size_penalty += 120.0
        if image_rect.height > (band_bottom - band_top) * 3.0:
            size_penalty += 80.0

        return (
            center_gap_y * 0.65
            + horizontal_gap * 0.12
            + left_penalty
            + size_penalty
            + y_soft_penalty
            - overlap_ratio * 28.0
        )

    # Primary pass: strict overlap with the row band.
    for image_rect in image_rects:
        overlap_y = max(0.0, min(image_rect.y1, band_bottom) - max(image_rect.y0, band_top))
        if overlap_y <= 0:
            continue

        overlap_ratio = overlap_y / max(1.0, min(image_rect.height, band_bottom - band_top))
        cost = _score(image_rect, overlap_ratio=overlap_ratio, y_soft_penalty=0.0)
        if cost < best_cost:
            best_cost = cost
            best = image_rect

    if best is not None:
        return best

    # Fallback: nearest vertical candidate when strict overlap is unavailable.
    for image_rect in image_rects:
        image_center_y = (image_rect.y0 + image_rect.y1) / 2.0
        y_distance = abs(code_center_y - image_center_y)
        if y_distance > 85:
            continue

        overlap_ratio = 0.0
        y_soft_penalty = y_distance * 0.9
        cost = _score(image_rect, overlap_ratio=overlap_ratio, y_soft_penalty=y_soft_penalty)
        if cost < best_cost:
            best_cost = cost
            best = image_rect

    return best

def render_clip(page: fitz.Page, rect: fitz.Rect, destination: Path) -> None:
    page_rect = page.rect
    pad_x = max(2.0, min(8.0, rect.width * 0.03))
    pad_y = max(2.0, min(8.0, rect.height * 0.03))
    clip = fitz.Rect(
        max(page_rect.x0, rect.x0 - pad_x),
        max(page_rect.y0, rect.y0 - pad_y),
        min(page_rect.x1, rect.x1 + pad_x),
        min(page_rect.y1, rect.y1 + pad_y),
    )
    pix = page.get_pixmap(matrix=fitz.Matrix(2.7, 2.7), clip=clip, alpha=False)
    destination.parent.mkdir(parents=True, exist_ok=True)
    pix.save(destination)


def choose_code_rect(code: str, code_rects: dict[str, list[fitz.Rect]]) -> fitz.Rect | None:
    matches = code_rects.get(code, [])
    if not matches:
        return None

    # Code column is usually right side; pick right-most occurrence for stable row mapping.
    return sorted(matches, key=lambda r: (r.x0, r.y0), reverse=True)[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair Kohler images row-by-row using Kohler.pdf")
    parser.add_argument("--pdf", default=str(DEFAULT_KOHLER_PDF_PATH), help="Path to Kohler PDF")
    parser.add_argument("--cache", default=str(DEFAULT_KOHLER_CACHE_PATH), help="Path to Kohler cache JSON")
    parser.add_argument("--images-dir", default=str(DEFAULT_IMAGES_DIR), help="Root images directory")
    parser.add_argument("--force", action="store_true", help="Overwrite existing code images")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    cache_path = Path(args.cache)
    images_dir = Path(args.images_dir)
    kohler_dir = images_dir / "Kohler"
    kohler_dir.mkdir(parents=True, exist_ok=True)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if not cache_path.exists():
        raise FileNotFoundError(f"Cache not found: {cache_path}")

    cache_data = json.loads(cache_path.read_text(encoding="utf-8"))
    if not isinstance(cache_data, list):
        raise ValueError("Kohler cache is not a list")

    page_cache: dict[int, tuple[dict[str, list[fitz.Rect]], list[fitz.Rect], list[fitz.Rect]]] = {}

    generated = 0
    skipped_existing = 0
    missing_code_rect = 0
    missing_image_rect = 0
    unresolved_codes: list[str] = []

    with fitz.open(pdf_path) as document:
        for item in cache_data:
            if not isinstance(item, dict):
                continue

            code = clean_code(item.get("code", ""))
            page_number = item.get("page_number")
            if not code or page_number is None:
                continue

            try:
                page_index = int(page_number)
            except (TypeError, ValueError):
                continue
            if page_index < 0 or page_index >= len(document):
                continue

            destination = kohler_dir / f"{code}.png"
            if destination.exists() and not args.force:
                skipped_existing += 1
                item["image"] = f"/images/Kohler/{code}.png"
                item["image_file"] = image_relative_path(destination)
                continue

            if page_index not in page_cache:
                page = document[page_index]
                code_rects = collect_code_rects(page)
                image_rects = collect_image_rects(page)
                all_code_rects = [rect for rects in code_rects.values() for rect in rects]
                page_cache[page_index] = (code_rects, image_rects, all_code_rects)

            code_rects, image_rects, all_code_rects = page_cache[page_index]
            code_rect = choose_code_rect(code, code_rects)
            if code_rect is None:
                missing_code_rect += 1
                unresolved_codes.append(code)
                if destination.exists():
                    destination.unlink(missing_ok=True)
                item["image"] = None
                item["image_file"] = ""
                continue

            image_rect = pick_row_image(code_rect, all_code_rects, image_rects)
            if image_rect is None:
                missing_image_rect += 1
                unresolved_codes.append(code)
                if destination.exists():
                    destination.unlink(missing_ok=True)
                item["image"] = None
                item["image_file"] = ""
                continue

            page = document[page_index]
            render_clip(page, image_rect, destination)
            generated += 1
            item["image"] = f"/images/Kohler/{code}.png"
            item["image_file"] = image_relative_path(destination)

    cache_path.write_text(json.dumps(cache_data, indent=2, ensure_ascii=False), encoding="utf-8")

    report_path = cache_path.with_name("kohler_rowwise_repair_report.json")
    report_path.write_text(
        json.dumps(
            {
                "generated": generated,
                "skipped_existing": skipped_existing,
                "missing_code_rect": missing_code_rect,
                "missing_image_rect": missing_image_rect,
                "unresolved_codes": sorted(set(unresolved_codes)),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"generated={generated}")
    print(f"skipped_existing={skipped_existing}")
    print(f"missing_code_rect={missing_code_rect}")
    print(f"missing_image_rect={missing_image_rect}")
    print(f"unresolved_codes={len(set(unresolved_codes))}")
    print(f"cache_updated={cache_path.name}")
    print(f"report={report_path.name}")
    print(f"images_dir={kohler_dir}")

if __name__ == "__main__":
    main()
