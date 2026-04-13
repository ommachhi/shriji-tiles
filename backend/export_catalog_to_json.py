"""Export complete catalog data from Excel files to JSON for production deployment."""

import json
from pathlib import Path

from openpyxl import load_workbook

from extractor import normalize_code, normalize_text, DEFAULT_IMAGES_DIR, image_relative_path


def export_excel_to_json(excel_path: Path, source_key: str, source_label: str) -> list[dict]:
    """Convert Excel catalog to list of product dictionaries."""
    products = []
    
    if not excel_path.exists():
        print(f"Excel file not found: {excel_path}")
        return products
    
    try:
        wb = load_workbook(excel_path, data_only=True)
        ws = wb.active
        
        # Skip header row
        for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            if row_idx == 1:  # Header
                continue
            
            if not row or not row[0]:  # Empty row
                continue
            
            code = str(row[0]).strip() if row[0] else ""
            name = str(row[1]).strip() if row[1] else ""
            price = row[2] if row[2] else 0
            finish = str(row[3]).strip() if row[3] else ""
            
            if not code:
                continue
            
            # Build image filename
            images_dir = Path(DEFAULT_IMAGES_DIR)
            possible_image = images_dir / f"{normalize_code(code)}.png"
            has_image = possible_image.exists()
            
            product = {
                "code": normalize_code(code),
                "name": normalize_text(name),
                "price": price if isinstance(price, (int, float)) else 0,
                "finish": normalize_text(finish),
                "source": source_key,
                "source_label": source_label,
            }
            
            if has_image:
                product["image"] = image_relative_path(code, source_key)
            
            products.append(product)
        
        print(f"✓ Exported {len(products)} products from {excel_path.name}")
        return products
    
    except Exception as e:
        print(f"✗ Error loading {excel_path}: {e}")
        return products


def main():
    backend_dir = Path(__file__).parent
    
    all_products = []
    
    # Export Aquant
    aquant_excel = backend_dir / "aquant_catalog_full.xlsx"
    aquant_products = export_excel_to_json(aquant_excel, "aquant", "Aquant")
    all_products.extend(aquant_products)
    
    # Export Kohler
    kohler_excel = backend_dir / "kohler_catalog_full.xlsx"
    kohler_products = export_excel_to_json(kohler_excel, "kohler", "Kohler")
    all_products.extend(kohler_products)
    
    # Save combined output
    output_path = backend_dir / "products_complete.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_products, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Total: {len(all_products)} products exported to {output_path}")
    print(f"  - Aquant: {len(aquant_products)}")
    print(f"  - Kohler: {len(kohler_products)}")


if __name__ == "__main__":
    main()
