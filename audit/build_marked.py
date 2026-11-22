# -*- coding: utf-8 -*-
"""DOCX #1 — marked audited copy of the coursework."""
import json, re, sys, os
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import defects as D
import curated as C
import curated2 as C2
import frontmatter as FM
from tables import T
from docxlib import *

BLOCKS = json.load(open("audit/blocks.json"))
AUTHOR, INIT = "Муассиса (аудит)", "АУ"

Y_FILL, R_FILL, G_FILL = "FFFF00", "FF0000", "00B050"
CMT = {}

def new_doc():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin, sec.right_margin = Cm(3.0), Cm(1.5)
    sec.top_margin, sec.bottom_margin = Cm(2.0), Cm(2.0)
    st = doc.styles["Normal"]
    st.font.name = "Times New Roman"; st.font.size = Pt(14)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    pf = st.paragraph_format
    pf.line_spacing = 1.15
    pf.space_after = Pt(0); pf.space_before = Pt(0)
    return doc

def page_number_footer(doc):
    p = doc.sections[0].footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = add_field(p, " PAGE ")
    r.font.name = "Times New Roman"; r.font.size = Pt(12)

# ---------- inline segmentation ----------
def spans_for(text, page):
    """Return list of (start,end,colour,code,note) for this block."""
    out = []
    for h in D.find_all(text):
        out.append(h)
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

def add_rich(doc, text, spans, para, pt=14, bold=False, align=None, indent=True, comment=True):
    if align is not None: para.alignment = align
    if indent:
        para.paragraph_format.first_line_indent = Cm(1.25)
    else:
        para.paragraph_format.first_line_indent = Cm(0)
    para.paragraph_format.line_spacing = 1.15
    para.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY if align is None else align
    # split text into segments covered by spans
    pos = 0
    segs = []
    for s, e, colour, code, note in spans:
        if s > pos: segs.append((pos, s, None, None, None))
        segs.append((s, e, colour, code, note))
        pos = e
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
        if comment and colour:
            c = doc.add_comment([r], text=f"[{code}] {note}", author=AUTHOR, initials=INIT)
            key = (code, note)
            CMT.setdefault(key, {"colour": colour, "n": 0, "pages": []})
            CMT[key]["n"] += 1
            pg = None
            CMT[key]["pages"].append(pg)
    return para

def add_body(doc, text, page, kind="p"):
    spans = spans_for(text, page)
    p = doc.add_paragraph()
    if kind == "li":
        p.paragraph_format.left_indent = Cm(0.75)
        p.paragraph_format.first_line_indent = Cm(0)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        # strip leading marker and re-add cleanly
        m = re.match(r"^([•▪➢❖✓→]|\d{1,2}\.|[a-e]\)|[a-e]\.)\s*", text)
        marker = ""
        rest = text
        if m:
            marker = m.group(1)
            rest = text[m.end():]
        r = p.add_run(marker + " ")
        r.font.name = "Times New Roman"; r.font.size = Pt(14)
        add_rich(doc, rest, [(max(0,s - m.end()), max(0,e - m.end()), c_, cd, nt)
                             for (s, e, c_, cd, nt) in spans if e > m.end()], p,
                 indent=False, comment=True)
    else:
        add_rich(doc, text, spans, p)
    p.paragraph_format.space_after = Pt(0)
    return p

def add_heading(doc, text, kind, page):
    spans = spans_for(text, page)
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(12 if kind != "h1" else 0); pf.space_after = Pt(12 if kind == "h1" else 6)
    pf.line_spacing = 1.15
    pf.first_line_indent = Cm(0)
    if kind == "h1":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pf.page_break_before = True
        size = 14
    elif kind == "h2":
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        size = 14
    elif kind == "h3c":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        size = 14
    else:
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        size = 14
    add_rich(doc, text, spans, p, pt=size, bold=True,
             align=p.alignment, indent=False, comment=True)
    for r in p.runs:
        r.bold = True
        if not (r.font.color and r.font.color.rgb and str(r.font.color.rgb) in ("FFFFFF",)):
            r.font.color.rgb = RGBColor(0, 0, 0)
    return p

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
    hdr = tbl.rows[0]
    repeat_header(hdr)
    for i, h in enumerate(spec["header"]):
        cell = hdr.cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        r = p.add_run(h); r.bold = True; r.font.name = "Times New Roman"; r.font.size = Pt(11)
        cell_shading(cell, "E8E8E8")
    for row in spec["rows"]:
        cells = tbl.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            p.paragraph_format.first_line_indent = Cm(0)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(v); r.font.name = "Times New Roman"; r.font.size = Pt(11)
    for i, w in enumerate(spec["widths"]):
        for row in tbl.rows:
            row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(6)
    return tbl

# ---------- document ----------
def build():
    doc = new_doc()
    page_number_footer(doc)

    # --- title block (front matter the original lacks — flagged) ---
    for line, sz, bold in (("Вазорати тандурустӣ ва ҳифзи иҷтимоии аҳолии Ҷумҳурии Тоҷикистон", 12, False),):
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(line); r.font.name = "Times New Roman"; r.font.size = Pt(sz); r.bold = bold
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("[НОМИ МУАССИСАИ ТАЪЛИМӢ]"); r.font.name="Times New Roman"; r.font.size=Pt(12)
    set_run_shading(r, Y_FILL)
    doc.add_comment([r], text="[С0] САРЛАВҲАИ РАСМӢ НЕСТ: дар файли аслӣ саҳифаи якум (сарлавҳа) мавҷуд нест — кор аз «НАҚША» оғоз мешавад. "
        "Барои кори курсӣ саҳифаи сарлавҳа бо номи муассиса, мавзӯъ, муаллиф, роҳбар, шаҳр ва сол ҳатмист. "
        "Ин блок ҳамчун ҷои холӣ илова шудааст — маълумоти воқеиро дохил кунед.",
        author=AUTHOR, initials=INIT)

    for _ in range(4):
        doc.add_paragraph()

    # --- actual reconstruction ---
    PARAS = json.load(open("audit/paras.json"))
    for idx, item in enumerate(PARAS):
        kind, page = item["kind"], item["page"]
        if kind == "table":
            add_table(doc, item["key"])
            continue
        text = item["text"]
        if idx == 0:
            parts = text.split("\n")
            for j, line in enumerate(parts):
                p = doc.add_paragraph()
                p.paragraph_format.first_line_indent = Cm(0)
                if j < 2:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    r = p.add_run(line); r.font.name = "Times New Roman"
                    r.font.size = Pt(16); r.bold = True
                    if j == 1:
                        set_run_shading(r, Y_FILL)
                        doc.add_comment([r], text="[С0.1] Номи кор дар болои «НАҚША» ҷойгир шудааст, на дар саҳифаи алоҳидаи сарлавҳа; "
                            "нусхаи аслӣ номи муассиса, муаллиф, роҳбар ва солро надорад. Тибқи талаботи муассиса саҳифаи сарлавҳа ҳатмист.",
                            author=AUTHOR, initials=INIT)
                elif line.strip() == "НАҚША:":
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    r = p.add_run(line); r.font.name = "Times New Roman"; r.font.size = Pt(14); r.bold = True
                else:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    r = p.add_run(line); r.font.name = "Times New Roman"; r.font.size = Pt(13)
            continue
        if kind == "toc":
            for line in text.split("\n"):
                p = doc.add_paragraph()
                p.paragraph_format.first_line_indent = Cm(0)
                r = p.add_run(line); r.font.name = "Times New Roman"; r.font.size = Pt(13)
            continue
        if kind == "h1":
            add_heading(doc, text, "h1", page)
        elif kind == "h2":
            add_heading(doc, text, "h2", page)
        elif kind in ("h3c", "h3l"):
            add_heading(doc, text, kind, page)
        else:
            add_body(doc, text, page, kind)

    return doc

if __name__ == "__main__":
    doc = build()
    doc.save("/tmp/probe1.docx")
    print("blocks:", len(BLOCKS), "comments:", len(CMT))
    print(sum(v["n"] for v in CMT.values()))
