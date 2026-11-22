# -*- coding: utf-8 -*-
"""Renders the marked copy (title page + 57 pages of content + tables) into a Document."""
import json, re, sys, os, collections
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import defects as D, curated as C, curated2 as C2
from tables import T
from docxlib import *

AUTHOR, INIT = "Муассиса (аудит)", "АУ"
CMT = collections.OrderedDict()
CODE_PAGES = collections.defaultdict(set)
TOTAL = collections.Counter()

def spans_for(text):
    out = list(D.find_all(text))
    for anchor, colour, code, note in list(C.CURATED) + list(C2.CURATED):
        start = 0
        while True:
            i = text.find(anchor, start)
            if i < 0: break
            out.append((i, i + len(anchor), colour, code, note))
            start = i + len(anchor)
    out.sort(key=lambda h: (h[0], -(h[1] - h[0])))
    kept = []
    for h in out:
        if any(not (h[1] <= k[0] or h[0] >= k[1]) for k in kept):
            continue
        kept.append(h)
    return kept

def add_rich(doc, text, para, spans, pt=14, bold=False, align=None, indent=True, page=None):
    pf = para.paragraph_format
    pf.first_line_indent = Cm(1.25) if indent else Cm(0)
    pf.line_spacing = 1.15
    para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY if align is None else align
    pos = 0; segs = []
    for s, e, colour, code, note in spans:
        if s > pos: segs.append((pos, s, None, None, None))
        segs.append((s, e, colour, code, note)); pos = e
    if pos < len(text): segs.append((pos, len(text), None, None, None))
    for s, e, colour, code, note in segs:
        chunk = text[s:e]
        if not chunk: continue
        r = para.add_run(chunk)
        r.font.name = "Times New Roman"; r.font.size = Pt(pt)
        if bold: r.bold = True
        if colour:
            if colour == "yellow":
                set_run_shading(r, "FFFF00")
            elif colour == "red":
                set_run_shading(r, "FFC7CE"); set_run_color(r, "C00000"); r.bold = True
                set_run_underline(r, "single", "C00000")
            else:
                set_run_shading(r, "C6EFCE"); set_run_color(r, "006100")
            doc.add_comment([r], text=f"[{code}] {note}", author=AUTHOR, initials=INIT)
            CMT[(code, colour)] = CMT.get((code, colour), 0) + 1
            TOTAL[colour] += 1
            if page: CODE_PAGES[code].add(page)
    return para

def add_table(doc, key):
    spec = T[key]
    if spec.get("caption"):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(6); p.paragraph_format.space_after = Pt(3)
        r = p.add_run(spec["caption"]); r.font.name = "Times New Roman"; r.font.size = Pt(12); r.italic = True
    tbl = doc.add_table(rows=1, cols=len(spec["header"]))
    tbl.style = "Table Grid"
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_cell_margins(tbl)
    hdr = tbl.rows[0]; repeat_header(hdr)
    for i, hh in enumerate(spec["header"]):
        cell = hdr.cells[i]; cell.text = ""
        p = cell.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        r = p.add_run(hh); r.bold = True; r.font.name = "Times New Roman"; r.font.size = Pt(10)
        cell_shading(cell, "E8E8E8")
    for row in spec["rows"]:
        cells = tbl.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]; p.paragraph_format.first_line_indent = Cm(0)
            r = p.add_run(v); r.font.name = "Times New Roman"; r.font.size = Pt(10)
    for i, w in enumerate(spec["widths"]):
        for row in tbl.rows:
            row.cells[i].width = Cm(w)
    sp = doc.add_paragraph(); sp.paragraph_format.space_after = Pt(4)

def add_heading(doc, text, kind, page):
    spans = spans_for(text)
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(10); pf.space_after = Pt(8 if kind == "h1" else 6)
    pf.line_spacing = 1.15; pf.first_line_indent = Cm(0)
    pf.keep_with_next = True
    if kind == "h1":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER; pf.page_break_before = True
    elif kind == "h3c":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    else:
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    add_rich(doc, text, p, spans, pt=14, bold=True, align=p.alignment, indent=False, page=page)
    return p

def add_body(doc, text, page, kind="p"):
    spans = spans_for(text)
    p = doc.add_paragraph()
    if kind == "li":
        p.paragraph_format.left_indent = Cm(0.75)
        p.paragraph_format.first_line_indent = Cm(0)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        m = re.match(r"^([•▪➢❖✓→]|\d{1,2}\.|[a-e]\)|[a-e]\.|[o])\s*", text)
        marker = ""; rest = text; shift = 0
        if m:
            marker = m.group(1); rest = text[m.end():]; shift = m.end()
            r = p.add_run(marker + " ")
            r.font.name = "Times New Roman"; r.font.size = Pt(14)
        shifted = [(max(0, s - shift), max(0, e - shift), c_, cd, nt)
                   for (s, e, c_, cd, nt) in spans if e > shift]
        add_rich(doc, rest, p, shifted, indent=False, page=page)
    else:
        add_rich(doc, text, p, spans, page=page)
    p.paragraph_format.space_after = Pt(0)

def title_block(doc):
    para = doc.add_paragraph(); para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = para.add_run("Вазорати тандурустӣ ва ҳифзи иҷтимоии аҳолии Ҷумҳурии Тоҷикистон")
    r.font.name = "Times New Roman"; r.font.size = Pt(12)
    p2 = doc.add_paragraph(); p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = p2.add_run("[НОМИ МУАССИСАИ ТАЪЛИМӢ]"); r2.font.name = "Times New Roman"; r2.font.size = Pt(12)
    set_run_shading(r2, "FFFF00")
    doc.add_comment([r2],
        text="[С0] САРЛАВҲАИ РАСМӢ НЕСТ: дар файли аслӣ саҳифаи сарлавҳа мавҷуд нест — кор аз «НАҚША» оғоз мешавад. "
             "Барои кори курсӣ саҳифаи сарлавҳа бо номи муассиса, мавзӯъ, муаллиф, роҳбар, шаҳр ва сол ҳатмист. "
             "Ин блок ҳамчун ҷои холӣ илова шудааст — маълумоти воқеиро дохил кунед.",
        author=AUTHOR, initials=INIT)
    CMT[("С0", "yellow")] = CMT.get(("С0", "yellow"), 0) + 1
    TOTAL["yellow"] += 1
    for _ in range(3):
        doc.add_paragraph()

def render_copy(doc):
    PARAS = json.load(open("audit/paras.json"))
    title_block(doc)
    for idx, item in enumerate(PARAS):
        kind, page = item["kind"], item["page"]
        if kind == "table":
            add_table(doc, item["key"]); continue
        text = item["text"]
        if idx == 0:
            for j, line in enumerate(text.split("\n")):
                p = doc.add_paragraph(); p.paragraph_format.first_line_indent = Cm(0)
                if j < 2:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    r = p.add_run(line); r.font.name = "Times New Roman"; r.font.size = Pt(16); r.bold = True
                    if j == 1:
                        set_run_shading(r, "FFFF00")
                        doc.add_comment([r],
                            text="[С0.1] Номи кор дар болои «НАҚША» ҷойгир шудааст, на дар саҳифаи алоҳидаи сарлавҳа; "
                                 "нусхаи аслӣ номи муассиса, муаллиф, роҳбар ва солро надорад. Тибқи талаботи муассиса саҳифаи сарлавҳа ҳатмист.",
                            author=AUTHOR, initials=INIT)
                        CMT[("С0.1", "yellow")] = CMT.get(("С0.1", "yellow"), 0) + 1
                        TOTAL["yellow"] += 1
                elif line.strip() == "НАҚША:":
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    r = p.add_run(line); r.font.name = "Times New Roman"; r.font.size = Pt(14); r.bold = True
                else:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    r = p.add_run(line); r.font.name = "Times New Roman"; r.font.size = Pt(12)
            continue
        if kind == "toc":
            for line in text.split("\n"):
                p = doc.add_paragraph(); p.paragraph_format.first_line_indent = Cm(0)
                p.paragraph_format.space_after = Pt(2)
                r = p.add_run(line); r.font.name = "Times New Roman"; r.font.size = Pt(12)
                if re.match(r"^(БОБИ|МУҚАДДИМА|ХУЛОСА|РӮЙХАТИ|НАҚША)", line):
                    r.bold = True
            continue
        if kind == "h1":
            add_heading(doc, text, "h1", page)
        elif kind == "h2":
            add_heading(doc, text, "h2", page)
        elif kind in ("h3c", "h3l"):
            add_heading(doc, text, kind, page)
        else:
            add_body(doc, text, page, kind)
