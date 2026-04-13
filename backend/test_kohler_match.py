import json
import re

with open('test_kohler.json', 'r', encoding='utf-8') as f:
    blocks = json.load(f)

KOHLER_CODE_PATTERN = re.compile(r"\b(K-[A-Z0-9-]+)\b", re.I)
PRICE_PATTERN = re.compile(
    r"(?:₹|Rs\.?|INR|MRP)[^0-9]*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.\d{1,2})?|[0-9]+(?:\.\d{1,2})?)",
    re.I,
)

def _parse_price(value: str):
    digits = re.sub(r"[^0-9]", "", value)
    return int(digits) if digits else None

def _is_pure_code(text: str) -> bool:
    return bool(re.fullmatch(r"\s*K-[A-Z0-9-]+\s*", text, re.I))

# simulated EvoFit+ group
evofit_blocks = [b for b in blocks if 490 < b['rect'][1] < 600]

all_codes = []
for b in evofit_blocks:
    for m in KOHLER_CODE_PATTERN.finditer(b['text']):
        all_codes.append({'code': m.group(1), 'center_y': (b['rect'][1]+b['rect'][3])/2, 'block': b})

prices = []
for b in evofit_blocks:
    match = PRICE_PATTERN.search(b['text'])
    if match:
        p = _parse_price(match.group(1))
        if p and p > 0:
            prices.append({'price': p, 'center_y': (b['rect'][1]+b['rect'][3])/2, 'block': b})

print(f"Codes: {[c['code'] for c in all_codes]}")
print(f"Prices: {[p['price'] for p in prices]}")

# match
used_codes = set()
for p in prices:
    codes_in_b = [c['code'] for c in all_codes if c['block'] == p['block']]
    if codes_in_b: best = codes_in_b[-1]
    else:
        best_dist = float('inf')
        best = None
        for c in all_codes:
            if c['code'] in used_codes: continue
            dist = abs(c['center_y'] - p['center_y'])
            if dist < best_dist and dist < 30:
                best_dist = dist
                best = c['code']
    if best:
        used_codes.add(best)
        print(f"Price {p['price']} matched with {best}")
