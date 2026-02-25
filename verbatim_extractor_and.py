#!/usr/bin/env python3
"""
Verbatim Debate Card Extractor (AND mode)
==========================================
Extracts text that is BOTH highlighted AND underlined from a verbatim-formatted .docx file.
Keeps the full card structure (tags, cites, block headers) but removes un-marked body text.

Usage:
    python verbatim_extractor_and.py input.docx
"""

import argparse
import sys
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn


def run_is_highlighted(run):
    """Return True if this run has ANY highlight color set (any color, not 'none')."""
    rpr = run._r.find(qn('w:rPr'))
    if rpr is None:
        return False

    
    # highlight = rpr.find(qn('w:highlight'))
    # if highlight is None:
    #     return False
    # val = highlight.get(qn('w:val'), '')
    # return val.lower() not in ('', 'none')

    # Check standard highlight
    highlight = rpr.find(qn('w:highlight'))
    if highlight is not None:
        val = highlight.get(qn('w:val'), '')
        if val.lower() not in ('', 'none'):
            return True
    
    # Check background shading (often used when pasting from web)
    shd = rpr.find(qn('w:shd'))
    if shd is not None:
        fill = shd.get(qn('w:fill'), '')
        # 'auto' or empty means no shading
        if fill.lower() not in ('', 'auto', 'ffffff', 'none'):
            return True
    
    return False

def run_is_underlined(run):
    """Return True if this run has underline formatting."""
    rpr = run._r.find(qn('w:rPr'))
    if rpr is None:
        return False
    u = rpr.find(qn('w:u'))
    if u is None:
        return False
    val = u.get(qn('w:val'), '')
    return val.lower() not in ('', 'none')


def run_is_bold(run):
    """Return True if this run is bold (used to detect tags/cites)."""
    rpr = run._r.find(qn('w:rPr'))
    if rpr is None:
        return False
    b = rpr.find(qn('w:b'))
    return b is not None


def paragraph_is_structural(para):
    """
    Heuristic: a paragraph is a 'structural' paragraph (tag, cite, block header)
    if ALL of its non-empty runs are bold, or if the paragraph style suggests a heading.
    """
    style_name = (para.style.name or '').lower()
    if any(k in style_name for k in ('heading', 'block', 'tag', 'cite', 'title')):
        return True

    runs = [r for r in para.runs if r.text.strip()]
    if not runs:
        return False
    return all(run_is_bold(r) for r in runs)


def filter_paragraph_runs(para):
    """
    Remove runs that are NOT both highlighted AND underlined.
    Returns True if any runs remain.
    """
    if paragraph_is_structural(para):
        return True

    runs_to_remove = []
    prev_kept = False
    for run in para.runs:
        if not run.text.strip():
            continue
        
        # Keep only if BOTH highlighted AND underlined
        keep = run_is_highlighted(run) and run_is_underlined(run)

        if not keep:
            runs_to_remove.append(run)
        else:
            if prev_kept and not run.text.startswith(' '):
                run.text = ' ' + run.text
            prev_kept = True

    for run in runs_to_remove:
        run._r.getparent().remove(run._r)

    remaining = [r for r in para.runs if r.text.strip()]
    return len(remaining) > 0


def extract(input_path, output_path):
    print(f"[•] Loading: {input_path}")
    out_doc = Document(input_path)

    paras_to_remove = []
    prev_was_structural = False

    for para in out_doc.paragraphs:
        is_structural = paragraph_is_structural(para)
        
        # Keep structural paragraphs and the paragraph immediately after (cite)
        if is_structural or prev_was_structural:
            prev_was_structural = is_structural
            continue
        
        prev_was_structural = False

        has_content = filter_paragraph_runs(para)
        if not has_content:
            paras_to_remove.append(para)

    removed = 0
    for para in paras_to_remove:
        para._element.getparent().remove(para._element)
        removed += 1

    # Clean up consecutive empty paragraphs
    all_paras = out_doc.element.body.findall('.//' + qn('w:p'))
    prev_empty = False
    for p_el in all_paras:
        texts = ''.join(t.text or '' for t in p_el.iter(qn('w:t')))
        is_empty = not texts.strip()
        if is_empty and prev_empty:
            p_el.getparent().remove(p_el)
        prev_empty = is_empty

    print(f"[✓] Removed {removed} body paragraphs with no marked content")
    out_doc.save(output_path)
    print(f"[✓] Saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Verbatim Debate Card Extractor — keeps BOTH highlighted AND underlined runs only'
    )
    parser.add_argument('input', help='Input .docx file')
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[✗] File not found: {input_path}")
        sys.exit(1)

    output_path = input_path.parent / f"{input_path.stem}_read-doc{input_path.suffix}"
    extract(str(input_path), str(output_path))


if __name__ == '__main__':
    main()
