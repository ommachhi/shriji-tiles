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

def _is_kohler_category_block(block: dict) -> bool:
    text = block["text"]
    x0 = block["rect"][0]
    x1 = block["rect"][2]
    if x0 < 180 or x1 > 380:
        return False
    if KOHLER_CODE_PATTERN.search(text) or PRICE_PATTERN.search(text):
        return False
    if text.isdigit() or text == "MODEL DESCRIPTION CODE MRP":
        return False
    return len(text.split()) <= 4

category_blocks = [b for b in blocks if _is_kohler_category_block(b)]
model_name_blocks = [b for b in blocks if b["rect"][0] <= 120 and not b["text"].isdigit() and b["text"] != "MODEL DESCRIPTION CODE MRP"]

price_blocks = []
for b in blocks:
    match = PRICE_PATTERN.search(b["text"])
    if match:
        p = _parse_price(match.group(1))
        if p and p > 0:
            price_blocks.append({"block": b, "price": p, "center_y": (b["rect"][1] + b["rect"][3])/2})
price_blocks.sort(key=lambda item: item["center_y"])

all_codes = []
for b in blocks:
    if b["text"].lower().startswith(("must order", "order with")):
        continue
    for m in KOHLER_CODE_PATTERN.finditer(b["text"]):
        all_codes.append({"code": m.group(1), "block": b, "center_y": (b["rect"][1] + b["rect"][3])/2})

results = []
for i, p_info in enumerate(price_blocks):
    price_y = p_info["center_y"]
    prev_p_y = price_blocks[i-1]["center_y"] if i > 0 else 0
    
    codes_in_same = [c["code"] for c in all_codes if c["block"] is p_info["block"]]
    if codes_in_same:
        best_code = codes_in_same[-1]
    else:
        valid_codes = [c for c in all_codes if prev_p_y - 10 <= c["center_y"] <= price_y + 15]
        if valid_codes:
            valid_codes.sort(key=lambda c: abs(c["center_y"] - price_y))
            best_code = valid_codes[0]["code"]
        else:
            best_code = None
            
    if not best_code:
        continue
        
    current_category = None
    for cb in category_blocks:
        if cb["rect"][1] < price_y:
            current_category = cb["text"]
            
    model_name = None
    model_name_y = None
    for mb in model_name_blocks:
        if mb["rect"][1] <= price_y + 5:
            passed_cat = False
            for cb in category_blocks:
                if mb["rect"][1] < cb["rect"][1] < price_y:
                    passed_cat = True
            if not passed_cat:
                model_name = mb["text"]
                model_name_y = mb["rect"][1]
                
    start_y = prev_p_y
    for cb in category_blocks:
        if start_y < cb["rect"][1] < price_y:
            start_y = cb["rect"][1]
            
    if model_name_y and model_name_y > start_y:
        start_y = model_name_y
                
    desc_blocks = []
    for b in blocks:
        cy = (b["rect"][1] + b["rect"][3])/2
        if start_y + 5 < cy <= price_y + 15:
            if b in category_blocks or b in model_name_blocks:
                continue
            if b["text"].lower().startswith(("must order", "order with")):
                continue
            if PRICE_PATTERN.search(b["text"]):
                pre_price = b["text"][:PRICE_PATTERN.search(b["text"]).start()].strip()
                pre_price = re.sub(KOHLER_CODE_PATTERN, " ", pre_price).strip()
                if pre_price: desc_blocks.append(pre_price)
                continue
            if bool(re.fullmatch(r"\s*K-[A-Z0-9-]+\s*", b["text"], re.I)):
                continue
            desc_blocks.append(b["text"])
            
    combined_details = " ".join(desc_blocks)
    combined_details = re.sub(KOHLER_CODE_PATTERN, " ", combined_details)
    combined_details = re.sub(r"\s{2,}", " ", combined_details).strip(" -:")
    
    if model_name:
        if current_category and not combined_details.lower().startswith(current_category.lower()):
            final_details = f"{model_name} {combined_details}".strip()
        elif not combined_details.lower().startswith(model_name.lower()):
            final_details = f"{model_name} {combined_details}".strip()
        else:
            final_details = combined_details
    else:
        final_details = combined_details
        
    print(f"[{best_code}] Name: {final_details}")
