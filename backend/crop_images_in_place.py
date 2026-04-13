#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png"}
JPEG_SUFFIXES = {".jpg", ".jpeg"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Batch crop product images in-place by detecting the main object and "
            "removing extra background margins."
        )
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "images",
        help="Folder that contains the images to crop. Defaults to ./images.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Also scan subfolders inside the images directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without overwriting any file.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N supported images.",
    )
    parser.add_argument(
        "--min-margin",
        type=int,
        default=3,
        help="Skip images when every side already has <= this many extra pixels.",
    )
    return parser.parse_args()


def list_image_files(images_dir: Path, recursive: bool) -> list[Path]:
    iterator = images_dir.rglob("*") if recursive else images_dir.glob("*")
    files = [path for path in iterator if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES]
    files.sort(key=lambda path: path.name.lower())
    return files


def read_image(path: Path) -> np.ndarray | None:
    try:
        data = np.fromfile(str(path), dtype=np.uint8)
        if data.size == 0:
            return None
        return cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
    except Exception:
        return None


def write_image(path: Path, image: np.ndarray) -> None:
    suffix = path.suffix.lower()
    encode_suffix = suffix if suffix in SUPPORTED_SUFFIXES else ".png"
    save_image = image
    params: list[int] = []

    if encode_suffix in JPEG_SUFFIXES:
        if save_image.ndim == 3 and save_image.shape[2] == 4:
            save_image = cv2.cvtColor(save_image, cv2.COLOR_BGRA2BGR)
        params = [cv2.IMWRITE_JPEG_QUALITY, 100]
    elif encode_suffix == ".png":
        params = [cv2.IMWRITE_PNG_COMPRESSION, 3]

    ok, encoded = cv2.imencode(encode_suffix, save_image, params)
    if not ok:
        raise RuntimeError(f"Failed to encode image as {encode_suffix}")

    temp_path = path.with_name(f"{path.name}.tmp")
    encoded.tofile(str(temp_path))
    temp_path.replace(path)


def border_pixels(image_lab: np.ndarray, thickness: int) -> np.ndarray:
    top = image_lab[:thickness, :, :].reshape(-1, 3)
    bottom = image_lab[-thickness:, :, :].reshape(-1, 3)
    left = image_lab[:, :thickness, :].reshape(-1, 3)
    right = image_lab[:, -thickness:, :].reshape(-1, 3)
    return np.vstack((top, bottom, left, right))


def alpha_mask(image: np.ndarray) -> np.ndarray | None:
    if image.ndim != 3 or image.shape[2] != 4:
        return None

    alpha = image[:, :, 3]
    if np.count_nonzero(alpha < 250) == 0:
        return None

    mask = np.where(alpha > 8, 255, 0).astype(np.uint8)
    if 0 < np.count_nonzero(mask) < mask.size:
        return mask
    return None


def choose_threshold_mask(blurred_gray: np.ndarray) -> np.ndarray:
    candidates: list[tuple[float, np.ndarray]] = []
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

    for threshold_flag in (cv2.THRESH_BINARY, cv2.THRESH_BINARY_INV):
        _, mask = cv2.threshold(blurred_gray, 0, 255, threshold_flag | cv2.THRESH_OTSU)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        ratio = float(np.count_nonzero(mask)) / float(mask.size)
        if 0.002 <= ratio <= 0.85:
            score = abs(ratio - 0.18)
            candidates.append((score, mask))

    adaptive = cv2.adaptiveThreshold(
        blurred_gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        3,
    )
    adaptive = cv2.morphologyEx(adaptive, cv2.MORPH_OPEN, kernel, iterations=1)
    ratio = float(np.count_nonzero(adaptive)) / float(adaptive.size)
    if 0.002 <= ratio <= 0.85:
        score = abs(ratio - 0.18)
        candidates.append((score, adaptive))

    if not candidates:
        return np.zeros_like(blurred_gray)

    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def background_difference_mask(image_bgr: np.ndarray) -> np.ndarray:
    image_lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
    border_thickness = max(2, min(image_bgr.shape[:2]) // 40)
    border = border_pixels(image_lab, border_thickness).astype(np.float32)
    background = np.median(border, axis=0)

    border_distance = np.linalg.norm(border - background, axis=1)
    distance = np.linalg.norm(image_lab.astype(np.float32) - background, axis=2)
    threshold = max(12.0, float(border_distance.mean() + (border_distance.std() * 2.5) + 4.0))
    return np.where(distance > threshold, 255, 0).astype(np.uint8)


def detect_footer_cutoff(image: np.ndarray) -> int | None:
    base = image[:, :, :3] if image.ndim == 3 and image.shape[2] == 4 else image
    gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
    image_h = gray.shape[0]
    if image_h < 180:
        return None

    row_mean = gray.mean(axis=1)
    row_std = gray.std(axis=1)
    smooth_kernel = np.ones(5, dtype=np.float32) / 5.0
    smooth_mean = np.convolve(row_mean, smooth_kernel, mode="same")
    smooth_std = np.convolve(row_std, smooth_kernel, mode="same")
    gradients = np.abs(np.diff(smooth_mean))

    start = int(image_h * 0.55)
    end = int(image_h * 0.94)
    if end - start < 24:
        return None

    bright_threshold = max(220.0, float(np.percentile(smooth_mean[start:end], 65)))
    min_footer_height = max(36, int(image_h * 0.10))
    run_length = 0

    for row in range(start, end):
        mean_value = float(smooth_mean[row])
        std_value = float(smooth_std[row])
        if mean_value >= bright_threshold and std_value <= 18.0:
            run_length += 1
        else:
            run_length = 0
            continue

        if run_length < 4:
            continue

        candidate = row - run_length + 1
        footer_height = image_h - candidate
        if footer_height < min_footer_height:
            break

        lower_slice = gray[candidate : min(image_h, candidate + min_footer_height), :]
        dark_ratio = float((lower_slice < 225).mean()) if lower_slice.size else 0.0

        if dark_ratio < 0.02:
            continue

        return candidate

    return None


def crop_footer_if_needed(image: np.ndarray) -> np.ndarray:
    cutoff = detect_footer_cutoff(image)
    if cutoff is None:
        return image

    cropped = image[:cutoff, :]
    if cropped.shape[0] < max(80, int(image.shape[0] * 0.45)):
        return image
    return cropped


def build_foreground_mask(image: np.ndarray) -> np.ndarray:
    base = image[:, :, :3] if image.ndim == 3 and image.shape[2] == 4 else image
    gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    diff_mask = background_difference_mask(base)
    threshold_mask = choose_threshold_mask(blurred)
    edge_mask = cv2.Canny(blurred, 40, 140)
    edge_mask = cv2.dilate(edge_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)), iterations=1)

    combined = cv2.bitwise_or(diff_mask, threshold_mask)
    combined = cv2.bitwise_or(combined, edge_mask)

    alpha = alpha_mask(image)
    if alpha is not None:
        combined = cv2.bitwise_or(combined, alpha)

    combined = cv2.morphologyEx(
        combined,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)),
        iterations=2,
    )
    combined = cv2.morphologyEx(
        combined,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
        iterations=1,
    )
    combined = cv2.dilate(
        combined,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
        iterations=1,
    )
    return combined


def is_banner_like(x: int, y: int, w: int, h: int, image_w: int, image_h: int) -> bool:
    touches_width = x <= 1 and (x + w) >= image_w - 1
    wide_strip = w >= int(image_w * 0.70) and h <= int(image_h * 0.35)
    near_bottom = y >= int(image_h * 0.55) or (y + h) >= image_h - 1
    return (touches_width and h <= int(image_h * 0.25)) or (wide_strip and near_bottom)


def find_crop_box(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    image_h, image_w = mask.shape[:2]
    min_component_area = max(60, int(image_h * image_w * 0.0006))

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates: list[tuple[float, tuple[int, int, int, int]]] = []

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_component_area:
            continue

        x, y, w, h = cv2.boundingRect(contour)
        if is_banner_like(x, y, w, h, image_w, image_h):
            continue

        candidates.append((area, (x, y, w, h)))

    if not candidates:
        return None

    largest_area, main_box = max(candidates, key=lambda item: item[0])
    main_x, main_y, main_w, main_h = main_box
    gap_x = max(4, int(image_w * 0.04))
    gap_y = max(4, int(image_h * 0.04))

    selected_boxes: list[tuple[int, int, int, int]] = []
    for area, (x, y, w, h) in candidates:
        area_is_significant = area >= max(min_component_area, largest_area * 0.08)
        is_close_to_main = not (
            x > (main_x + main_w + gap_x)
            or (x + w) < (main_x - gap_x)
            or y > (main_y + main_h + gap_y)
            or (y + h) < (main_y - gap_y)
        )
        if area_is_significant or is_close_to_main:
            selected_boxes.append((x, y, w, h))

    if not selected_boxes:
        selected_boxes.append(main_box)

    min_x = min(x for x, _, _, _ in selected_boxes)
    min_y = min(y for _, y, _, _ in selected_boxes)
    max_x = max(x + w for x, _, w, _ in selected_boxes)
    max_y = max(y + h for _, y, _, h in selected_boxes)

    pad_x = max(1, int((max_x - min_x) * 0.01))
    pad_y = max(1, int((max_y - min_y) * 0.01))

    min_x = max(0, min_x - pad_x)
    min_y = max(0, min_y - pad_y)
    max_x = min(image_w, max_x + pad_x)
    max_y = min(image_h, max_y + pad_y)

    if max_x <= min_x or max_y <= min_y:
        return None

    return min_x, min_y, max_x, max_y


def should_skip_crop(box: tuple[int, int, int, int], image_shape: tuple[int, ...], min_margin: int) -> bool:
    image_h, image_w = image_shape[:2]
    min_x, min_y, max_x, max_y = box

    left = min_x
    top = min_y
    right = image_w - max_x
    bottom = image_h - max_y

    if max(left, top, right, bottom) <= min_margin:
        return True

    crop_area = (max_x - min_x) * (max_y - min_y)
    image_area = image_w * image_h
    return crop_area >= int(image_area * 0.985) and max(left, top, right, bottom) <= (min_margin * 2)


def crop_image(image: np.ndarray, min_margin: int) -> tuple[np.ndarray | None, str]:
    if image is None or image.size == 0:
        return None, "invalid image"

    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    original_shape = image.shape
    image = crop_footer_if_needed(image)
    footer_changed = image.shape[:2] != original_shape[:2]
    mask = build_foreground_mask(image)
    box = find_crop_box(mask)
    if box is None:
        if footer_changed:
            return image, f"removed footer, kept {image.shape[1]}x{image.shape[0]}"
        return None, "no object detected"

    if should_skip_crop(box, image.shape, min_margin):
        if footer_changed:
            return image, f"removed footer, kept {image.shape[1]}x{image.shape[0]}"
        return None, "already tightly cropped"

    min_x, min_y, max_x, max_y = box
    cropped = image[min_y:max_y, min_x:max_x]
    if cropped.size == 0:
        return None, "empty crop"

    return cropped, f"cropped to {max_x - min_x}x{max_y - min_y}"


def process_file(path: Path, min_margin: int, dry_run: bool) -> tuple[str, str]:
    image = read_image(path)
    if image is None:
        return "skipped", "invalid or unreadable image"

    cropped, detail = crop_image(image, min_margin=min_margin)
    if cropped is None:
        if detail in {"already tightly cropped", "no object detected"}:
            return "skipped", detail
        return "failed", detail

    if dry_run:
        return "cropped", f"{detail} (dry-run)"

    write_image(path, cropped)
    return "cropped", detail


def main() -> int:
    args = parse_args()
    images_dir = args.images_dir.resolve()

    if not images_dir.exists():
        print(f"ERROR: Images folder not found: {images_dir}")
        return 1

    image_files = list_image_files(images_dir, recursive=args.recursive)
    if args.limit is not None:
        image_files = image_files[: max(0, args.limit)]

    if not image_files:
        print(f"No supported images found in: {images_dir}")
        return 0

    cropped_count = 0
    skipped_count = 0
    failed_count = 0

    for index, path in enumerate(image_files, start=1):
        try:
            status, detail = process_file(path, min_margin=args.min_margin, dry_run=args.dry_run)
        except Exception as error:
            status, detail = "failed", str(error)

        if status == "cropped":
            cropped_count += 1
        elif status == "skipped":
            skipped_count += 1
        else:
            failed_count += 1

        print(f"[{index}/{len(image_files)}] {path.name}: {status} - {detail}")

    print()
    print("Done")
    print(f"Folder   : {images_dir}")
    print(f"Processed: {len(image_files)}")
    print(f"Cropped  : {cropped_count}")
    print(f"Skipped  : {skipped_count}")
    print(f"Failed   : {failed_count}")

    return 1 if failed_count else 0


if __name__ == "__main__":
    sys.exit(main())
