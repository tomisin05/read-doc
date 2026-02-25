#!/usr/bin/env python3
"""Check which paragraphs are detected as structural (tags/cites)."""

import sys
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn

def run_is_bold(run):
    rpr = run._r.find(qn('w:rPr'))
    if rpr is None:
        return False
    b = rpr.find(qn('w:b'))
    return b is not None

def paragraph_is_structural(para):
    style_name = (para.style.name or '').lower()
    if any(k in style_name for k in ('heading', 'block', 'tag', 'cite', 'title')):
        return True
    runs = [r for r in para.runs if r.text.strip()]
    if not runs:
        return False
    return all(run_is_bold(r) for r in runs)

def check_structure(input_path):
    doc = Document(input_path)
    
    for i, para in enumerate(doc.paragraphs[:20]):  # First 20 paragraphs
        if not para.text.strip():
            continue
        
        is_struct = paragraph_is_structural(para)
        marker = "[STRUCTURAL]" if is_struct else "[BODY]"
        
        print(f"{marker} Para {i}: {para.text[:80]}")
        if not is_struct:
            runs = [r for r in para.runs if r.text.strip()]
            bold_count = sum(1 for r in runs if run_is_bold(r))
            print(f"  -> {bold_count}/{len(runs)} runs are bold")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python check_structure.py input.docx")
        sys.exit(1)
    check_structure(sys.argv[1])
