from __future__ import annotations

from pathlib import Path

from extractor import DEFAULT_CACHE_PATH
from build_excel_database import OUTPUT_EXCEL, main as build_excel_main
from regenerate_aquant_p4_49_images import regenerate_images_from_excel
from regression_suite import main_regression


def delete_existing_excels(base_dir: Path) -> list[str]:
    removed: list[str] = []
    patterns = [
        "aquant_catalog*.xlsx",
        "catalog_pages_*_codeimg*.xlsx",
    ]

    for pattern in patterns:
        for excel_file in base_dir.glob(pattern):
            try:
                excel_file.unlink(missing_ok=True)
                removed.append(excel_file.name)
            except PermissionError:
                pass

    return sorted(removed)


def delete_existing_images(images_dir: Path) -> int:
    images_dir.mkdir(parents=True, exist_ok=True)
    removed = 0
    for image_file in images_dir.rglob("*.png"):
        try:
            image_file.unlink(missing_ok=True)
            removed += 1
        except PermissionError:
            pass

    for folder in sorted((path for path in images_dir.rglob("*") if path.is_dir()), key=lambda item: len(item.parts), reverse=True):
        try:
            folder.rmdir()
        except OSError:
            pass
    return removed


def validate_outputs(excel_path: Path, images_dir: Path) -> tuple[int, int]:
    if not excel_path.exists():
        raise FileNotFoundError(f"Expected Excel not found: {excel_path}")

    images = sorted(str(path.relative_to(images_dir)).replace("\\", "/") for path in images_dir.rglob("*.png"))
    duplicates = len(images) - len(set(images))
    return len(images), duplicates


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    images_dir = base_dir / "images"
    excel_path = base_dir / OUTPUT_EXCEL

    removed_excels = delete_existing_excels(base_dir)
    removed_images = delete_existing_images(images_dir)

    print(f"reset_removed_excels={len(removed_excels)}")
    print(f"reset_removed_images={removed_images}")

    built_excel = build_excel_main()
    regenerated, skipped, removed_unreferenced = regenerate_images_from_excel(
        built_excel,
        images_dir,
        Path(DEFAULT_CACHE_PATH),
    )

    image_count, duplicate_count = validate_outputs(excel_path, images_dir)

    print(f"excel={excel_path.name}")
    print(f"regenerated={regenerated}")
    print(f"skipped={skipped}")
    print(f"removed_unreferenced={removed_unreferenced}")
    print(f"final_image_count={image_count}")
    print(f"duplicate_image_names={duplicate_count}")

    print("running_regression_suite=1")
    regression_exit_code = main_regression()
    print(f"regression_exit_code={regression_exit_code}")
    if regression_exit_code != 0:
        raise SystemExit(regression_exit_code)


if __name__ == "__main__":
    main()
