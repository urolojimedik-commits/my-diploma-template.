# -*- coding: utf-8 -*-
"""Тахмини саҳифабандӣ барои мундариҷа (модели хаттӣ, TNR14, 1.5)."""
import json, os, re, sys
from docx import Document
from docx.shared import Cm

PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Кори_курсӣ_Воситаҳои_аёнӣ_ва_мултимедиявӣ.docx")

PAGE_H = 25.7  # cm usable
LINE = 0.741   # 14pt x 1.5
CPL = 60       # chars per line approx TNR14 at 16.5cm

doc = Document(PATH)
page = 1
y = 0.0
result = {}
order = []

def new_page():
    global page, y
    page += 1; y = 0.0

def add_h(h):
    global y
    if y + h > PAGE_H and y > 0:
        new_page()
    y += h

def lines_for(text, cpl=CPL):
    if not text.strip():
        return 0
    # word wrap approx
    words = text.split()
    lines, cur = 1, 0
    for w in words:
        add = len(w) + (1 if cur else 0)
        if cur + add > cpl and cur:
            lines += 1; cur = len(w)
        else:
            cur += add
    return lines

def record(text):
    t = text.strip()
    key = None
    if t == "МУҚАДДИМА": key = "Муқаддима"
    elif t.startswith("БОБИ 1."): key = "БОБИ 1"
    elif t.startswith("БОБИ 2."): key = "БОБИ 2"
    elif t.startswith("БОБИ 3."): key = "БОБИ 3"
    elif t == "ХУЛОСА": key = "Хулоса"
    elif t.startswith("РӮЙХАТИ АДАБИЁТ"): key = "АДАБИЁТ"
    elif t == "ЗАМИМА": key = "Замима"
    elif re.match(r"^[123]\.[123]\.", t): key = t[:3]
    if key and key not in result:
        result[key] = page
        order.append((key, page, t[:60]))

# Estimate images aspect from files
from PIL import Image
imgdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "images")
aspects = {}
for f in os.listdir(imgdir):
    with Image.open(os.path.join(imgdir, f)) as im:
        aspects[f] = im.size[1] / im.size[0]
fig_aspect_cycle = [aspects.get("fig_paivio.png", .45), aspects.get("fig_vocab.png", .58),
                    aspects.get("fig_types.png", .68), aspects.get("fig_tpack.png", .8), aspects.get("fig_dyn.png", .58)]
fig_idx = 0

for el in doc.element.body.iterchildren():
    tag = el.tag.split('}')[-1]
    if tag == 'p':
        # find paragraph
        # text
        texts = el.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')
        text = "".join(n.text or "" for n in texts)
        # page break?
        brs = el.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}br')
        is_break = any(b.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type') == 'page' for b in brs)
        if is_break:
            new_page()
            continue
        # style
        pstyle = el.find('./{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pPr/{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pStyle')
        style = pstyle.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val') if pstyle is not None else ""
        # image in paragraph?
        pics = el.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}blip')
        if pics:
            asp = fig_aspect_cycle[fig_idx % len(fig_aspect_cycle)]; fig_idx += 1
            add_h(13.5 * asp + 0.4)
            continue
        if not text.strip():
            add_h(LINE * 0.7)
            continue
        if style == "Heading1":
            record(text)
            add_h(LINE * lines_for(text, 38) + 0.9)
        elif style in ("Heading2", "Heading3"):
            record(text)
            add_h(LINE * lines_for(text, 55) + 0.7)
        else:
            # estimate font size small for captions/biblio loosely by length
            add_h(LINE * lines_for(text))
    elif tag == 'tbl':
        rows = el.findall('./{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr')
        ncols = max(1, len(rows[0].findall('./{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc'))) if rows else 1
        total = 0.6  # caption spacing approx handled as paragraph
        for r in rows:
            cells = r.findall('./{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc')
            maxlines = 1
            for c in cells:
                texts = c.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')
                txt = "".join(n.text or "" for n in texts)
                maxlines = max(maxlines, lines_for(txt, max(12, int(58 / ncols))))
            total += maxlines * 0.55 + 0.15
        add_h(total)

print("Total pages (est):", page)
for k, p, t in order:
    print(k, p, t)
json.dump(result, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "toc.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("toc.json written")
