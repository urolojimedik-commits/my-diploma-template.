# -*- coding: utf-8 -*-
"""Саҳифабандии дақиқтар: метрикаи Liberation Serif (= Times), PIL не, SFD."""
import json, os, re, sys, glob

def load_sfd(path):
    widths = {}
    enc = None
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("Encoding:"):
                parts = line.split()
                try: enc = int(parts[1])
                except Exception: enc = None
            elif line.startswith("Width:") and enc is not None:
                try: widths[enc] = int(line.split()[1]) / 2048.0  # units per em in sfd scaled? check below
                except Exception: pass
                enc = None
    return widths

# SFD Liberation: UPM is 2048? Width values e.g. A ~1401/2048=0.684em plausible. We'll normalize using 'M'
REG = load_sfd("/tmp/liberation-fonts-2.1.5/src/LiberationSerif-Regular.sfd")
BOLD = load_sfd("/tmp/liberation-fonts-2.1.5/src/LiberationSerif-Bold.sfd")

def text_width(text, size, bold=False):
    d = BOLD if bold else REG
    default = d.get(ord("М"), 0.85)
    return sum(d.get(ord(ch), default) for ch in text) * size

from docx import Document
PATH = glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "*.docx"))[0]
doc = Document(PATH)
TEXT_W = 16.5 / 2.54 * 72  # 467.7 pt
PAGE_H = 25.7 / 2.54 * 72  # 728.5 pt
FIRST_INDENT = 1.25 / 2.54 * 72

page, y = 1, 0.0
result, order = {}, []

def newline():
    global page, y
    page += 1; y = 0.0

def add_line(h):
    global y
    if y + h > PAGE_H and y > 0:
        newline()
    y += h

def wrap_count(text, size, bold, width, first_indent=0.0):
    words = text.split()
    if not words: return 0
    lines, cur_w, avail = 1, 0.0, width - first_indent
    space_w = text_width(" ", size, bold)
    for w in words:
        ww = text_width(w, size, bold)
        add = ww if cur_w == 0 else ww + space_w
        if cur_w + add > avail and cur_w > 0:
            lines += 1; cur_w = ww; avail = width
        else:
            cur_w += add
    return lines

def record(text):
    t = text.strip(); key = None
    if t == "МУҚАДДИМА": key = "Муқаддима"
    elif t.startswith("БОБИ 1."): key = "БОБИ 1"
    elif t.startswith("БОБИ 2."): key = "БОБИ 2"
    elif t.startswith("БОБИ 3."): key = "БОБИ 3"
    elif t == "ХУЛОСА": key = "Хулоса"
    elif t.startswith("РӮЙХАТИ АДАБИЁТ"): key = "АДАБИЁТ"
    elif t == "ЗАМИМА": key = "Замима"
    elif re.match(r"^[123]\.[123]\.", t): key = t[:3]
    if key and key not in result:
        result[key] = page; order.append((key, page))

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
figs = []
for el in doc.element.body.iterchildren():
    tag = el.tag.split('}')[-1]
    if tag == 'p':
        texts = el.findall(f'.//{W}t')
        text = "".join(n.text or "" for n in texts)
        brs = el.findall(f'.//{W}br')
        if any(b.get(f'{W}type') == 'page' for b in brs):
            newline(); continue
        exts = el.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}ext')
        if exts:
            cy = int(exts[0].get('cy')) / 914400 * 72
            add_line(cy) if y + cy <= PAGE_H else (newline(), add_line(cy))
            # image cannot split: if doesn't fit move whole
            continue
        pstyle_el = el.find(f'./{W}pPr/{W}pStyle')
        style = pstyle_el.get(f'{W}val') if pstyle_el is not None else ""
        # run props
        runs = el.findall(f'./{W}r')
        size, bold = 14.0, False
        for r in runs:
            sz = r.find(f'./{W}rPr/{W}sz')
            if sz is not None: size = int(sz.get(f'{W}val')) / 2
            if r.find(f'./{W}rPr/{W}b') is not None: bold = True
            break
        if not text.strip():
            add_line(size * 1.15 * 1.5); continue
        if style == "Heading1":
            record(text)
            y_sp = 12 + 6
            n = wrap_count(text, 16, True, TEXT_W)
            for _ in range(n): add_line(16 * 1.15 * 1.5)
            y += y_sp
        elif style in ("Heading2", "Heading3"):
            record(text)
            n = wrap_count(text, 14, True, TEXT_W)
            for _ in range(n): add_line(14 * 1.15 * 1.5)
            y += 18
            if y > PAGE_H: newline()
        else:
            indent = FIRST_INDENT if size >= 13.5 else 0.0
            n = wrap_count(text, size, bold, TEXT_W, indent)
            lh = size * 1.15 * 1.5
            for _ in range(n): add_line(lh)
    elif tag == 'tbl':
        rows = el.findall(f'./{W}tr')
        if not rows: continue
        ncols = max(1, len(rows[0].findall(f'./{W}tc')))
        col_w = TEXT_W / ncols - 11
        for r in rows:
            maxlines = 1
            for c in r.findall(f'./{W}tc'):
                txt = "".join(n.text or "" for n in c.findall(f'.//{W}t'))
                maxlines = max(maxlines, wrap_count(txt, 11, False, col_w))
            rh = maxlines * 11 * 1.15 * 1.5 + 4
            # row splits approx line-wise
            remaining = rh
            while remaining > 0:
                step = min(remaining, 11 * 1.15 * 1.5)
                add_line(step); remaining -= step

print("Estimated pages:", page)
for k, p in order: print(k, p)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "toc.json")
json.dump(result, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("width check M em:", REG.get(ord("M")), "space:", REG.get(32), "a:", REG.get(ord("а")))
