#!/usr/bin/env python3
"""Debug script to check formatting in a Word document."""

import sys
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn

def check_formatting(input_path):
    doc = Document(input_path)
    
    for i, para in enumerate(doc.paragraphs):
        if not para.text.strip():
            continue
            
        print(f"\n--- Paragraph {i} ---")
        print(f"Text preview: {para.text[:100]}")
        
        for j, run in enumerate(para.runs):
            if not run.text.strip():
                continue
                
            rpr = run._r.find(qn('w:rPr'))
            
            # Check highlight
            highlight = None
            if rpr is not None:
                h = rpr.find(qn('w:highlight'))
                if h is not None:
                    highlight = h.get(qn('w:val'), 'NO_VAL')
            
            # Check underline
            underline = None
            if rpr is not None:
                u = rpr.find(qn('w:u'))
                if u is not None:
                    underline = u.get(qn('w:val'), 'NO_VAL')
            
            if highlight or underline:
                print(f"  Run {j}: '{run.text[:50]}'")
                print(f"    Highlight: {highlight}")
                print(f"    Underline: {underline}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python debug_formatting.py input.docx")
        sys.exit(1)
    
    check_formatting(sys.argv[1])
