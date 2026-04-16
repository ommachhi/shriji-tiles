#!/usr/bin/env python3
import json
from pathlib import Path

report = json.loads(Path('kohler_audit_report.json').read_text(encoding='utf-8'))

print('\n' + '='*100)
print('KOHLER CATALOG - CRITICAL ISSUES & RECOMMENDATIONS')
print('='*100)

errors = report.get('errors', {})
warnings = report.get('warnings', {})

# Issue 1: Missing Images
print('\n[ISSUE 1] ❌ MISSING IMAGE FILES (18 products)')
print('-'*100)
missing_imgs = errors.get('missing_image_file', [])
print(f'Count: {len(missing_imgs)}\n')
for p in missing_imgs:
    print(f'  Code: {p["code"]:22s} | Image: {p.get("image_file", "N/A"):32s} | Price: ₹{p["price"]}')
    print(f'        Name: {p["name"][:80]}')
    print()

# Issue 2: Missing Names
print('\n[ISSUE 2] ❌ MISSING PRODUCT NAMES (1 product)')
print('-'*100)
missing_names = errors.get('missing_name', [])
for p in missing_names:
    print(f'  Code: {p["code"]:22s} | Page: {p["page"]:3d} | Price: ₹{p["price"]}')

# Issue 3: Low Prices (critical OCR issue)
print('\n\n[ISSUE 3] 🔴 SUSPICIOUSLY LOW PRICES (192 products) - CRITICAL OCR ERROR')
print('-'*100)
print('These prices appear to be OCR truncation errors (single/double digit values)')
low_prices = warnings.get('low_price', [])
price_dist = {}
for p in low_prices:
    price_dist.setdefault(p['price'], []).append(p)

print(f'\nDistribution of low prices:')
for price in sorted(price_dist.keys())[:15]:
    count = len(price_dist[price])
    print(f'  ₹{price:>4d}  → {count:3d} products')
    if count <= 2:
        for p in price_dist[price]:
            print(f'           • {p["code"]:22s} | {p["name"][:70]}')

print('\n\n[ISSUE 4] ⚠️ SMALL IMAGE FILES (4 products - may be corrupted)')
print('-'*100)
small_imgs = warnings.get('small_image', [])
for p in small_imgs:
    print(f'  {p["code"]:22s} | {p["name"][:70]}')

print('\n\n' + '='*100)
print('RECOMMENDATIONS & FIXES')
print('='*100)

print('''
1. MISSING IMAGE FILES (18 products):
   ✓ Codes affected: EX28093IN-8-*, EX28094IN-8-*, etc.
   → Action: Need to manually add these images to images/Kohler/ directory
   → These are Components ® faucet variants that may not have been extracted

2. MISSING PRODUCT NAME (1 product):
   ✓ Code: K-26286IN-G-BL (Page 138)
   → Action: Manually verify PDF page 138 and update extractor or cache

3. LOW PRICE ERRORS (192 products - CRITICAL):
   ✓ Prices like 1, 2, 3, 4, 5, 6, etc. instead of 1000+, 2000+, etc.
   → Root Cause: OCR parsing capturing only last 1-2 digits
   → Action: Run price repair with threshold 200+ to catch all OCR truncations
   → Command: python fix_kohler_low_prices.py --threshold 200

4. SMALL IMAGE FILES (4 products):
   ✓ File size < 5KB (typically PNG images are 20-100KB)
   → Action: Re-render these image previews
   → Commands:
     - Delete existing small PNGs from images/Kohler/
     - Run: python rebuild_kohler_catalog.py --force-images
''')

print('='*100)
