#!/usr/bin/env python3
"""
Investigate PDF structure and price format.
"""

import fitz
from pathlib import Path

KOHLER_PDF = Path(__file__).parent / "Kohler.pdf"

def investigate_pdf():
    """Extract and display text from specific pages."""
    if not KOHLER_PDF.exists():
        print(f"PDF not found: {KOHLER_PDF}")
        return
    
    doc = fitz.open(KOHLER_PDF)
    
    # Check a few sample pages
    sample_pages = [5, 10, 22, 50, 100]
    
    for page_num in sample_pages:
        if page_num <= len(doc):
            print(f"\n{'='*80}")
            print(f"PAGE {page_num}")
            print(f"{'='*80}")
            
            page = doc[page_num - 1]
            text = page.get_text()
            
            # Print first 2000 chars
            print(text[:2000])
            print("\n[...truncated...]")

if __name__ == "__main__":
    investigate_pdf()
