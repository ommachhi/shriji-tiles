#!/usr/bin/env python3
import json
from pathlib import Path

report = json.loads(Path('kohler_audit_report.json').read_text(encoding='utf-8'))
summary = report.get('summary', {})
errors = report.get('errors', {})
warnings = report.get('warnings', {})

print('\n' + '='*80)
print('AUDIT SUMMARY - CURRENT STATE')
print('='*80)
print(f'Total Products Extracted: {summary.get("total_products_extracted", 0):>6d}')
print(f'OK Products:              {summary.get("ok_products", 0):>6d}')
print(f'Error Count:              {summary.get("error_count", 0):>6d}')
print(f'Error Rate:               {summary.get("error_rate_percent", 0):>6.2f}%')
print(f'\nLow Prices (<100):        {len(warnings.get("low_price", [])):>6d}')
print(f'Missing Images:           {len(errors.get("missing_image_file", [])):>6d}')
print(f'Missing Names:            {len(errors.get("missing_name", [])):>6d}')
print(f'Small Images (<5KB):      {len(warnings.get("small_image", [])):>6d}')
print('='*80)
