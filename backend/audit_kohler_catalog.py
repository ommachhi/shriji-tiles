#!/usr/bin/env python3
"""
Comprehensive Kohler catalog audit: verify extraction, prices, images, and data completeness.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from datetime import datetime

import fitz

from extractor import (
    DEFAULT_KOHLER_CACHE_PATH,
    DEFAULT_KOHLER_PDF_PATH,
    DEFAULT_IMAGES_DIR,
    extract_products_from_pdf,
    normalize_code,
)


def audit_kohler_catalog() -> dict:
    """Run comprehensive audit on Kohler catalog."""
    
    pdf_path = Path(DEFAULT_KOHLER_PDF_PATH)
    cache_path = Path(DEFAULT_KOHLER_CACHE_PATH)
    images_dir = Path(DEFAULT_IMAGES_DIR) / "Kohler"
    
    if not pdf_path.exists():
        return {"error": f"PDF not found: {pdf_path}"}
    
    # Load cache
    cached_products = {}
    if cache_path.exists():
        try:
            cached_data = json.loads(cache_path.read_text(encoding="utf-8"))
            for item in cached_data:
                code_key = normalize_code(item.get("code", ""))
                if code_key:
                    cached_products[code_key] = item
        except (OSError, json.JSONDecodeError):
            pass
    
    # Get all available images
    available_images = set()
    image_to_size = {}
    if images_dir.exists():
        for img_file in images_dir.glob("*.png"):
            available_images.add(img_file.name.replace(".png", "").upper())
            try:
                size = img_file.stat().st_size
                image_to_size[img_file.name] = size
            except OSError:
                pass
    
    # Extract all products from PDF (full range)
    print("Extracting products from Kohler PDF...")
    extracted_products = extract_products_from_pdf(
        pdf_path=pdf_path,
        page_range=None,  # Full PDF
        source_key="kohler",
        source_label="Kohler",
    )
    
    # Build report structure
    report = {
        "timestamp": datetime.now().isoformat(),
        "pdf_path": str(pdf_path),
        "cache_path": str(cache_path),
        "images_dir": str(images_dir),
        "summary": {
            "total_products_extracted": len(extracted_products),
            "total_products_cached": len(cached_products),
            "total_images": len(available_images),
        },
        "errors": {
            "missing_price": [],
            "missing_image_file": [],
            "price_zero_or_low": [],
            "missing_code": [],
            "missing_name": [],
            "duplicate_codes": [],
            "image_mismatch": [],
            "incomplete_data": [],
        },
        "warnings": {
            "low_price": [],
            "small_image": [],
            "special_variants": [],
        },
        "detailed_products": [],
    }
    
    seen_codes = {}
    low_price_threshold = 100
    small_image_threshold = 5000  # bytes
    
    # Audit each extracted product
    for idx, product in enumerate(extracted_products, 1):
        code = str(product.get("code", "")).strip()
        code_key = normalize_code(code)
        name = str(product.get("name", "")).strip()
        price = product.get("price", 0)
        image_path = product.get("image", "")
        page_num = product.get("page_number", 0)
        
        product_info = {
            "index": idx,
            "code": code,
            "code_normalized": code_key,
            "name": name[:80] if name else "",
            "price": price,
            "page": page_num + 1,
            "image": image_path,
            "errors": [],
            "warnings": [],
            "status": "OK",
        }
        
        # 1. Check for missing/invalid code
        if not code:
            product_info["errors"].append("Missing product code")
            report["errors"]["missing_code"].append(product_info)
            product_info["status"] = "ERROR"
            report["detailed_products"].append(product_info)
            continue
        
        # 2. Check for duplicate codes
        if code_key in seen_codes:
            product_info["errors"].append(f"Duplicate code (first seen at index {seen_codes[code_key]})")
            report["errors"]["duplicate_codes"].append(product_info)
            product_info["status"] = "ERROR"
        else:
            seen_codes[code_key] = idx
        
        # 3. Check for missing name
        if not name:
            product_info["errors"].append("Missing product name")
            report["errors"]["missing_name"].append(product_info)
            product_info["status"] = "ERROR"
        
        # 4. Check price
        if not price or price <= 0:
            product_info["errors"].append(f"Missing or zero price (value={price})")
            report["errors"]["missing_price"].append(product_info)
            product_info["status"] = "ERROR"
        elif price < low_price_threshold:
            product_info["warnings"].append(f"Very low price: ₹{price} (likely OCR truncation)")
            report["warnings"]["low_price"].append(product_info)
        
        # 5. Check image
        if image_path:
            # Extract filename from path
            image_file = image_path.split("/")[-1]
            image_key = image_file.replace(".png", "").upper()
            
            product_info["image_file"] = image_file
            
            if not images_dir.exists() or not (images_dir / image_file).exists():
                product_info["errors"].append(f"Image file missing: {image_file}")
                report["errors"]["missing_image_file"].append(product_info)
                product_info["status"] = "ERROR"
            else:
                # Check image size
                img_path = images_dir / image_file
                try:
                    size = img_path.stat().st_size
                    if size < small_image_threshold:
                        product_info["warnings"].append(f"Small image file: {size} bytes (may be corrupted)")
                        report["warnings"]["small_image"].append(product_info)
                except OSError:
                    pass
        else:
            product_info["errors"].append("No image path provided")
            report["errors"]["missing_image_file"].append(product_info)
            product_info["status"] = "ERROR"
        
        # 6. Check against cache
        if code_key in cached_products:
            cached = cached_products[code_key]
            cached_price = cached.get("price", 0)
            cached_image = cached.get("image", "")
            
            if price != cached_price:
                product_info["warnings"].append(f"Price mismatch with cache: extracted={price}, cached={cached_price}")
            
            if image_path and not cached_image:
                product_info["warnings"].append("Cache has no image but extracted product has one")
        
        # 7. Detect incomplete data
        data_fields = [code, name, price, image_path]
        if sum(1 for f in data_fields if f) < 3:
            product_info["errors"].append("Incomplete data (missing multiple critical fields)")
            report["errors"]["incomplete_data"].append(product_info)
            product_info["status"] = "ERROR"
        
        # 8. Detect variants/special cases
        if "-BRD" in code or "-RGD" in code or "-AF" in code:
            product_info["warnings"].append(f"Variant code detected: {code}")
            report["warnings"]["special_variants"].append(product_info)
        
        report["detailed_products"].append(product_info)
    
    # Summary statistics
    error_count = sum(len(v) for v in report["errors"].values())
    warning_count = sum(len(v) for v in report["warnings"].values())
    ok_count = len(extracted_products) - len([p for p in report["detailed_products"] if p["status"] == "ERROR"])
    
    report["summary"].update({
        "ok_products": ok_count,
        "error_count": error_count,
        "warning_count": warning_count,
        "error_rate_percent": round(100 * error_count / len(extracted_products), 2) if extracted_products else 0,
    })
    
    return report


def format_report(report: dict) -> str:
    """Format audit report for display."""
    
    if "error" in report:
        return f"ERROR: {report['error']}\n"
    
    lines = []
    lines.append("\n" + "="*80)
    lines.append("KOHLER CATALOG AUDIT REPORT")
    lines.append("="*80)
    lines.append(f"Generated: {report.get('timestamp', 'N/A')}\n")
    
    # Summary
    summary = report.get("summary", {})
    lines.append("SUMMARY:")
    lines.append("-" * 80)
    lines.append(f"  Total Products Extracted:  {summary.get('total_products_extracted', 0)}")
    lines.append(f"  Total Products Cached:     {summary.get('total_products_cached', 0)}")
    lines.append(f"  Total Images Available:    {summary.get('total_images', 0)}")
    lines.append(f"  OK Products:               {summary.get('ok_products', 0)}")
    lines.append(f"  Products with Errors:      {summary.get('error_count', 0)}")
    lines.append(f"  Products with Warnings:    {summary.get('warning_count', 0)}")
    lines.append(f"  Error Rate:                {summary.get('error_rate_percent', 0)}%\n")
    
    # Detailed errors
    errors = report.get("errors", {})
    if any(errors.values()):
        lines.append("ERRORS FOUND:")
        lines.append("=" * 80)
        
        if errors.get("missing_code"):
            lines.append(f"\n🔴 MISSING CODE ({len(errors['missing_code'])} products):")
            for p in errors["missing_code"][:5]:
                lines.append(f"   Page {p['page']}: {p['name'][:60]}")
            if len(errors["missing_code"]) > 5:
                lines.append(f"   ... and {len(errors['missing_code']) - 5} more")
        
        if errors.get("missing_price"):
            lines.append(f"\n🔴 MISSING/ZERO PRICE ({len(errors['missing_price'])} products):")
            for p in errors["missing_price"][:5]:
                lines.append(f"   {p['code']:20s} ({p['name'][:40]}) - Price: {p['price']}")
            if len(errors["missing_price"]) > 5:
                lines.append(f"   ... and {len(errors['missing_price']) - 5} more")
        
        if errors.get("missing_image_file"):
            lines.append(f"\n🔴 MISSING IMAGE FILE ({len(errors['missing_image_file'])} products):")
            for p in errors["missing_image_file"][:5]:
                lines.append(f"   {p['code']:20s} ({p['name'][:40]}) - Image: {p.get('image_file', 'N/A')}")
            if len(errors["missing_image_file"]) > 5:
                lines.append(f"   ... and {len(errors['missing_image_file']) - 5} more")
        
        if errors.get("missing_name"):
            lines.append(f"\n🔴 MISSING NAME ({len(errors['missing_name'])} products):")
            for p in errors["missing_name"][:5]:
                lines.append(f"   {p['code']:20s} Page {p['page']}")
            if len(errors["missing_name"]) > 5:
                lines.append(f"   ... and {len(errors['missing_name']) - 5} more")
        
        if errors.get("duplicate_codes"):
            lines.append(f"\n🔴 DUPLICATE CODES ({len(errors['duplicate_codes'])} products):")
            for p in errors["duplicate_codes"][:5]:
                lines.append(f"   {p['code']:20s} (Index {p['index']}, Page {p['page']})")
            if len(errors["duplicate_codes"]) > 5:
                lines.append(f"   ... and {len(errors['duplicate_codes']) - 5} more")
        
        if errors.get("price_zero_or_low"):
            lines.append(f"\n🔴 PRICE ZERO OR VERY LOW ({len(errors['price_zero_or_low'])} products):")
            for p in errors["price_zero_or_low"][:5]:
                lines.append(f"   {p['code']:20s} - ₹{p['price']} ({p['name'][:40]})")
            if len(errors["price_zero_or_low"]) > 5:
                lines.append(f"   ... and {len(errors['price_zero_or_low']) - 5} more")
    
    # Detailed warnings
    warnings = report.get("warnings", {})
    if any(warnings.values()):
        lines.append("\n\nWARNINGS:")
        lines.append("=" * 80)
        
        if warnings.get("low_price"):
            lines.append(f"\n⚠️  SUSPICIOUSLY LOW PRICE ({len(warnings['low_price'])} products):")
            for p in warnings["low_price"][:5]:
                lines.append(f"   {p['code']:20s} - ₹{p['price']:6d} ({p['name'][:40]})")
            if len(warnings["low_price"]) > 5:
                lines.append(f"   ... and {len(warnings['low_price']) - 5} more")
        
        if warnings.get("small_image"):
            lines.append(f"\n⚠️  SMALL IMAGE FILE ({len(warnings['small_image'])} products):")
            for p in warnings["small_image"][:5]:
                lines.append(f"   {p['code']:20s} ({p['name'][:40]})")
            if len(warnings["small_image"]) > 5:
                lines.append(f"   ... and {len(warnings['small_image']) - 5} more")
        
        if warnings.get("special_variants"):
            lines.append(f"\n⚠️  VARIANT CODES ({len(warnings['special_variants'])} products):")
            for p in warnings["special_variants"][:10]:
                lines.append(f"   {p['code']:20s} - ₹{p['price']:6d}")
            if len(warnings["special_variants"]) > 10:
                lines.append(f"   ... and {len(warnings['special_variants']) - 10} more")
    
    # Top products (sample)
    lines.append("\n\nSAMPLE PRODUCTS (First 10 OK):")
    lines.append("=" * 80)
    ok_products = [p for p in report.get("detailed_products", []) if p["status"] == "OK"]
    for p in ok_products[:10]:
        lines.append(f"  ✓ {p['code']:20s} | ₹{p['price']:8d} | {p['name'][:50]}")
    
    lines.append("\n" + "="*80 + "\n")
    
    return "\n".join(lines)


def save_report_json(report: dict, output_path: Path) -> None:
    """Save report as JSON."""
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    
    print("Starting Kohler catalog audit...\n")
    report = audit_kohler_catalog()
    
    # Print formatted report
    print(format_report(report))
    
    # Save JSON report
    json_report_path = base_dir / "kohler_audit_report.json"
    save_report_json(report, json_report_path)
    print(f"✓ JSON report saved to: {json_report_path}")
    
    # Save text summary
    text_report_path = base_dir / "kohler_audit_report.txt"
    text_report_path.write_text(format_report(report), encoding="utf-8")
    print(f"✓ Text report saved to: {text_report_path}")


if __name__ == "__main__":
    main()
