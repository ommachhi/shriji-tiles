#!/usr/bin/env python3
"""
Generate comprehensive PDF validation report with detailed analysis.
"""

import json
from pathlib import Path
from collections import defaultdict

BACKEND_DIR = Path(__file__).parent
REPORT_FILE = BACKEND_DIR / "kohler_pdf_strict_validation_report.json"

def analyze_validation_report():
    """Analyze and generate detailed report."""
    
    if not REPORT_FILE.exists():
        print(f"Report not found: {REPORT_FILE}")
        return
    
    with open(REPORT_FILE, "r", encoding="utf-8") as f:
        report = json.load(f)
    
    errors = report["errors"]
    warnings = report["warnings"]
    stats = report["stats"]
    
    print("\n" + "="*100)
    print("KOHLER CATALOG - COMPREHENSIVE PDF STRICT VALIDATION REPORT")
    print("="*100)
    
    print("\n🎯 EXECUTIVE SUMMARY")
    print("-" * 100)
    print(f"""
Total Products Analyzed:          {stats['total_pdf_codes']} (from PDF)
Products in Cache:                {stats['total_cache_products']}
Products in Excel:                {len(stats['codes_in_excel'])}

Codes Matching (PDF ↔ Cache):     {len(stats['codes_in_pdf']) - len(stats['codes_only_in_pdf'])} codes
Codes Only in PDF:                {len(stats['codes_only_in_pdf'])} codes
Codes Only in Cache:              {len(stats['codes_only_in_cache'])} codes

Validation Results:
  ✅ Correct matches:             {stats['correct_matches']}
  ❌ Price mismatches:            {sum(1 for e in errors if e['type'] == 'price_mismatch')}
  ❌ Image missing:               {sum(1 for e in errors if e['type'] == 'image_missing')}
  ❌ Products not in dataset:     {sum(1 for e in errors if e['type'] == 'product_not_found_in_dataset')}
  
  Total Errors:                   {len(errors)}
  Total Warnings:                 {len(warnings)}
  
Data Quality Score:               {(stats['correct_matches'] / (len(stats['codes_in_pdf'])) * 100):.2f}%
""")
    
    # Detailed error analysis
    print("\n📊 DETAILED ERROR ANALYSIS")
    print("-" * 100)
    
    # Price mismatches
    price_mismatches = [e for e in errors if e['type'] == 'price_mismatch']
    if price_mismatches:
        print(f"\n❌ PRICE MISMATCHES ({len(price_mismatches)} products):")
        
        # Analyze price differences
        price_diffs = []
        for error in price_mismatches:
            diff = error.get('difference', 0)
            price_diffs.append({
                'code': error['code'],
                'pdf_price': error['pdf_price'],
                'cache_price': error['cache_price'],
                'difference': diff,
                'diff_percent': (diff / error['pdf_price'] * 100) if error['pdf_price'] else 0,
                'name': error['cache_name']
            })
        
        # Sort by absolute difference
        price_diffs.sort(key=lambda x: abs(x['difference']), reverse=True)
        
        print("\n  Top 10 Largest Price Discrepancies:")
        print("  " + "─" * 96)
        print(f"  {'Code':<20} {'PDF Price':>12} {'Cache Price':>12} {'Difference':>12} {'% Diff':>8} {'Name':<30}")
        print("  " + "─" * 96)
        
        for item in price_diffs[:10]:
            name_short = item['name'][:30] if item['name'] else "N/A"
            print(f"  {item['code']:<20} ₹{item['pdf_price']:>10,} ₹{item['cache_price']:>10,} "
                  f"₹{item['difference']:>10,} {item['diff_percent']:>7.1f}% {name_short:<30}")
        
        if len(price_diffs) > 10:
            print(f"\n  ... and {len(price_diffs) - 10} more price mismatches")
        
        # Statistics on price discrepancies
        under_50_pct = sum(1 for p in price_diffs if abs(p['diff_percent']) < 50)
        fifty_to_100_pct = sum(1 for p in price_diffs if 50 <= abs(p['diff_percent']) < 100)
        over_100_pct = sum(1 for p in price_diffs if abs(p['diff_percent']) >= 100)
        
        print(f"\n  Price Discrepancy Distribution:")
        print(f"    < 50% difference:   {under_50_pct} products")
        print(f"    50-100% difference: {fifty_to_100_pct} products")
        print(f"    > 100% difference:  {over_100_pct} products")
    
    # Image issues
    image_missing = [e for e in errors if e['type'] == 'image_missing']
    if image_missing:
        print(f"\n\n❌ MISSING IMAGES ({len(image_missing)} products):")
        print("\n  Sample missing images:")
        print("  " + "─" * 96)
        print(f"  {'Code':<20} {'Expected File':<40} {'Product Name':<36}")
        print("  " + "─" * 96)
        
        for error in image_missing[:15]:
            name_short = error['cache_name'][:35] if error['cache_name'] else "N/A"
            file_short = error['expected_image'][-38:] if error['expected_image'] else "N/A"
            print(f"  {error['code']:<20} {file_short:<40} {name_short:<36}")
        
        if len(image_missing) > 15:
            print(f"\n  ... and {len(image_missing) - 15} more missing images")
    
    # Products not in dataset
    not_in_dataset = [e for e in errors if e['type'] == 'product_not_found_in_dataset']
    if not_in_dataset:
        print(f"\n\n⚠️  PRODUCTS IN PDF BUT NOT IN CACHE/EXCEL ({len(not_in_dataset)} products):")
        print("\n  These codes appear in the PDF but are missing from the dataset:")
        print("  " + "─" * 96)
        print(f"  {'Code':<20} {'Pages':<20} {'PDF Prices':<50}")
        print("  " + "─" * 96)
        
        for error in not_in_dataset[:15]:
            pages_str = str(error['pdf_pages'])[:18]
            prices_str = str(error['pdf_prices'])[:48]
            print(f"  {error['code']:<20} {pages_str:<20} {prices_str:<50}")
        
        if len(not_in_dataset) > 15:
            print(f"\n  ... and {len(not_in_dataset) - 15} more")
    
    # Products only in cache
    only_in_cache = list(stats['codes_only_in_cache'])
    if only_in_cache:
        print(f"\n\n🔔 PRODUCTS IN CACHE BUT NOT IN PDF ({len(only_in_cache)} products):")
        print("   These products are in your cache but don't appear in the PDF:")
        print("   " + "─" * 94)
        
        cache_only_codes = only_in_cache[:20]
        for code in cache_only_codes:
            print(f"   • {code}")
        
        if len(only_in_cache) > 20:
            print(f"\n   ... and {len(only_in_cache) - 20} more")
    
    # Production readiness assessment
    print("\n\n" + "="*100)
    print("🏭 PRODUCTION READINESS ASSESSMENT")
    print("="*100)
    
    is_production_ready = len(errors) == 0
    quality_score = (stats['correct_matches'] / (len(stats['codes_in_pdf'])) * 100) if len(stats['codes_in_pdf']) > 0 else 0
    
    print(f"""
Current Status:                   {'❌ NOT PRODUCTION READY' if not is_production_ready else '✅ PRODUCTION READY'}
Data Quality Score:               {quality_score:.2f}%
Required Quality Score:           99.9%
Required Error Count:             0

CRITICAL ISSUES:
{len(price_mismatches)} price mismatches that must be corrected
{len(image_missing)} missing product images
{len(not_in_dataset)} products in PDF but not in cache
{len(only_in_cache)} products in cache but not in PDF

STATUS: {'🟢 PASSED' if is_production_ready and quality_score >= 99.9 else '🔴 FAILED'}
""")
    
    # Recommendations
    print("\n" + "="*100)
    print("💡 RECOMMENDATIONS")
    print("="*100)
    print("""
1. PRICE CORRECTIONS NEEDED:
   - Review and correct 984 price mismatches against the PDF source
   - Prioritize products with > 100% price differences
   - Consider if these are OCR errors from earlier extraction

2. IMAGE ACQUISITION:
   - 1130 products are missing image files
   - Either extract images from PDF or obtain from product database
   - Images are critical for catalog completeness

3. DATASET RECONCILIATION:
   - 140 products in PDF are not in cache (possible new products or extraction issues)
   - 252 products in cache are not in PDF (possibly older/discontinued products)
   - Decide on inclusion/exclusion criteria

4. VALIDATION METHODOLOGY:
   - Current cache validation marked data as "production ready" with 0 errors
   - However, strict PDF comparison reveals 2254 discrepancies
   - Consider revising validation rules if cache version is intended to differ from PDF

5. NEXT STEPS:
   a) Decide on source of truth: PDF vs. Cache
   b) If PDF is source of truth: Update all 984 mismatched prices
   c) Acquire missing images for 1130 products
   d) Resolve code discrepancies (140 in PDF, 252 only in cache)
   e) Re-run validation to confirm corrections
""")
    
    print("\n" + "="*100)
    print(f"Report generated from: {REPORT_FILE}")
    print("="*100 + "\n")

if __name__ == "__main__":
    analyze_validation_report()
