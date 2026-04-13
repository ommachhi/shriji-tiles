import fitz
import json

doc = fitz.open('Kohler.pdf')
page = doc[13]

results = []
for block in page.get_text('dict')['blocks']:
    if block['type'] == 0:
        lines = block.get('lines', [])
        text = ' '.join(span['text'] for line in lines for span in line.get('spans', []))
        results.append({
            'rect': block['bbox'],
            'text': text
        })

for i, res in enumerate(results):
    print(f"{i}: {res['rect']} {res['text'].encode('utf-8')}")
