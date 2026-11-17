# -*- coding: utf-8 -*-
"""Сохтани ҳуҷҷати ниҳоии DOCX-и кори курсӣ."""
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

import cw
from cw import TEXT_W, TEXT_H, LH, TLH, CM, count_lines, block_height, Layout

import front
import ch1
import ch2
import back

TITLE = "Секретсияи экзокринии ғадуди зери меъда ва механизмҳои танзими он"
OUT_DIR = os.path.join(cw.BASE, "docx")
DOCX = os.path.join(OUT_DIR, "Kori_kursi_sekretsiyai_pankreas.docx")

BODY = front.INTRO + ch1.BLOCKS + ch2.BLOCKS + back.CONCLUSION + back.REFS


# ------------------------------------------------------------------ TOC
def toc_plan(blocks):
    entries = [(1 if b["t"] == "h1" else 2, b["x"]) for b in blocks if b["t"] in ("h1", "h2")]
    lines = 0
    for lvl, t in entries:
        w = TEXT_W - (0.75 * CM if lvl == 2 else 0) - 30  # ҷои рақами саҳифа
        lines += count_lines(t, w, 14, bold=(lvl == 1))
    pages = max(1, math.ceil(lines * LH / TEXT_H))
    return entries, pages


# ------------------------------------------------------------------ услубҳо
def set_run_font(run, size=14, bold=False, italic=False):
    run.font.name = "Times New Roman"
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor(0, 0, 0)
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), "Times New Roman")


def setup_styles(doc):
    st = doc.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(14)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    pf = st.paragraph_format
    pf.line_spacing = 1.5
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf.first_line_indent = Cm(1.25)
    pf.widow_control = True

    for name, size, before, after, indent in (("Heading 1", 14, 0, 6, 0),
                                              ("Heading 2", 14, 8, 6, 1.25)):
        s = doc.styles[name]
        s.font.name = "Times New Roman"
        s.font.size = Pt(size)
        s.font.bold = True
        s.font.italic = False
        s.font.color.rgb = RGBColor(0, 0, 0)
        rpr = s.element.get_or_add_rPr()
        rf = rpr.find(qn("w:rFonts"))
        if rf is None:
            rf = OxmlElement("w:rFonts")
            rpr.insert(0, rf)
        for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rf.set(qn(a), "Times New Roman")
        p = s.paragraph_format
        p.line_spacing = 1.5
        p.space_before = Pt(before)
        p.space_after = Pt(after)
        p.first_line_indent = Cm(indent)
        p.left_indent = Cm(0)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if name == "Heading 1" else WD_ALIGN_PARAGRAPH.LEFT
        p.keep_with_next = True
        p.page_break_before = (name == "Heading 1")


def para(doc, text="", align=WD_ALIGN_PARAGRAPH.JUSTIFY, size=14, bold=False,
         italic=False, indent=1.25, before=0, after=0, spacing=1.5,
         keep_next=False, left=0.0):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = align
    pf.first_line_indent = Cm(indent)
    pf.left_indent = Cm(left)
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = spacing
    pf.keep_with_next = keep_next
    if text:
        set_run_font(p.add_run(text), size, bold, italic)
    return p


# ------------------------------------------------------------------ ҷадвалҳо
def set_cell(cell, text, bold=False, size=11.5, align=WD_ALIGN_PARAGRAPH.LEFT, keep=False):
    cell.text = ""
    p = cell.paragraphs[0]
    pf = p.paragraph_format
    pf.alignment = align
    pf.first_line_indent = Cm(0)
    pf.left_indent = Cm(0)
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.line_spacing = 1.0
    pf.keep_with_next = keep
    set_run_font(p.add_run(str(text)), size, bold)


def add_table(doc, b):
    cap = para(doc, b["cap"], align=WD_ALIGN_PARAGRAPH.LEFT, size=12, bold=True,
               indent=0, before=6, after=3, spacing=1.0, keep_next=True)
    n_rows = len(b["rows"]) + 1
    n_cols = len(b["head"])
    t = doc.add_table(rows=n_rows, cols=n_cols)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False

    tblPr = t._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)

    widths = [Cm(w) for w in b["widths"]]
    for i, w in enumerate(widths):
        t.columns[i].width = w
    for r, row in enumerate([b["head"]] + b["rows"]):
        tr = t.rows[r]
        cant = OxmlElement("w:cantSplit")
        tr._tr.get_or_add_trPr().append(cant)
        last = (r == n_rows - 1)
        for c, val in enumerate(row):
            cell = tr.cells[c]
            cell.width = widths[c]
            set_cell(cell, val, bold=(r == 0), size=b["size"],
                     align=WD_ALIGN_PARAGRAPH.CENTER if r == 0 else WD_ALIGN_PARAGRAPH.LEFT,
                     keep=not last)
        if r == 0:
            hdr = OxmlElement("w:tblHeader")
            tr._tr.get_or_add_trPr().append(hdr)
    if b.get("src"):
        para(doc, b["src"], align=WD_ALIGN_PARAGRAPH.LEFT, size=10, italic=True,
             indent=0, before=2, after=6, spacing=1.0)
    else:
        para(doc, "", indent=0, after=6, spacing=1.0)
    return cap


# ------------------------------------------------------------------ расмҳо
def add_figure(doc, b, base):
    path = os.path.join(base, b["path"])
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf.first_line_indent = Cm(0)
    pf.space_before = Pt(6)
    pf.space_after = Pt(3)
    pf.line_spacing = 1.0
    pf.keep_with_next = True
    p.add_run().add_picture(path, width=Cm(b["w"]))
    para(doc, b["cap"], align=WD_ALIGN_PARAGRAPH.CENTER, size=12, indent=0,
         before=0, after=6 if not b.get("src") else 2, spacing=1.0,
         keep_next=bool(b.get("src")))
    if b.get("src"):
        para(doc, b["src"], align=WD_ALIGN_PARAGRAPH.CENTER, size=10, italic=True,
             indent=0, before=0, after=8, spacing=1.0)


# ------------------------------------------------------------------ саҳифаи унвонӣ
def title_page(doc):
    def tp(text, size=14, bold=False, align=WD_ALIGN_PARAGRAPH.CENTER, before=0, after=0):
        return para(doc, text, align=align, size=size, bold=bold, indent=0,
                    before=before, after=after, spacing=1.0)

    tp("ВАЗОРАТИ МАОРИФ ВА ИЛМИ ҶУМҲУРИИ ТОҶИКИСТОН", 14, True)
    tp("")
    tp("_________________________________________________", 14)
    tp("(номи муассисаи таҳсилоти олии касбӣ)", 10, False, after=12)
    tp("Факултети _______________________________________", 14)
    tp("Кафедраи ________________________________________", 14, after=36)

    tp("КОРИ КУРСӢ", 16, True, after=6)
    tp("аз фанни «Физиологияи нормалӣ»", 14, after=18)
    tp("Мавзӯъ:", 14, after=6)
    tp("«Секретсияи экзокринии ғадуди зери меъда\nва механизмҳои танзими он»", 14, True, after=48)

    tp("Иҷрокунанда: донишҷӯи курси ____, гурӯҳи ____", 14,
       align=WD_ALIGN_PARAGRAPH.RIGHT)
    tp("_________________________________", 14, align=WD_ALIGN_PARAGRAPH.RIGHT)
    tp("(имову насаб)", 10, align=WD_ALIGN_PARAGRAPH.RIGHT, after=18)
    tp("Роҳбар: ____________________________", 14, align=WD_ALIGN_PARAGRAPH.RIGHT)
    tp("_________________________________", 14, align=WD_ALIGN_PARAGRAPH.RIGHT)
    tp("(вазифа, дараҷаи илмӣ, имову насаб)", 10,
       align=WD_ALIGN_PARAGRAPH.RIGHT, after=18)
    tp("Баҳо: ______________", 14, align=WD_ALIGN_PARAGRAPH.RIGHT, after=0)

    for _ in range(4):
        tp("")
    tp("Душанбе — соли 20___", 14, True)


# ------------------------------------------------------------------ TOC
def add_toc(doc, entries, pages_map):
    h = doc.add_paragraph(style="Heading 1")
    h.paragraph_format.page_break_before = True
    h.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    h.paragraph_format.space_after = Pt(12)
    set_run_font(h.add_run("МУНДАРИҶА"), 14, True)

    for lvl, text in entries:
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.first_line_indent = Cm(0)
        pf.left_indent = Cm(0.75 if lvl == 2 else 0)
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        pf.line_spacing = 1.5
        pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
        tabs = pf.tab_stops
        tabs.add_tab_stop(Cm(16.5), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        set_run_font(p.add_run(text + "\t" + str(pages_map[(lvl, text)])), 14, lvl == 1)


# ------------------------------------------------------------------ асосӣ
def build():
    entries, toc_pages = toc_plan(BODY)
    lay = Layout()
    lay.page = 2 + toc_pages   # саҳифаи 1 — унвонӣ, саҳифаҳои TOC — баъд аз он
    total_body_pages, placed = lay.run(BODY)
    total_pages = total_body_pages
    pages_map = {(lvl, t): pg for lvl, t, pg in placed}

    doc = Document()
    setup_styles(doc)
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin, sec.right_margin = Cm(3.0), Cm(1.5)
    sec.top_margin, sec.bottom_margin = Cm(2.0), Cm(2.0)
    sec.header_distance, sec.footer_distance = Cm(1.25), Cm(1.25)
    sec.different_first_page_header_footer = True

    # рақами саҳифа дар поён
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.paragraph_format.first_line_indent = Cm(0)
    def _fld(kind=None, instr=None, text=None):
        run = fp.add_run()
        set_run_font(run, 12)
        if kind:
            e = OxmlElement("w:fldChar")
            e.set(qn("w:fldCharType"), kind)
            run._r.append(e)
        if instr is not None:
            e = OxmlElement("w:instrText")
            e.set(qn("xml:space"), "preserve")
            e.text = instr
            run._r.append(e)
        if text is not None:
            e = OxmlElement("w:t")
            e.text = text
            run._r.append(e)

    _fld(kind="begin")
    _fld(instr=" PAGE ")
    _fld(kind="separate")
    _fld(text="2")
    _fld(kind="end")

    title_page(doc)
    add_toc(doc, entries, pages_map)

    for b in BODY:
        kind = b["t"]
        if kind == "h1":
            p = doc.add_paragraph(style="Heading 1")
            p.paragraph_format.page_break_before = True
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.keep_with_next = True
            set_run_font(p.add_run(b["x"]), 14, True)
        elif kind == "h2":
            p = doc.add_paragraph(style="Heading 2")
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.first_line_indent = Cm(1.25)
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.keep_with_next = True
            set_run_font(p.add_run(b["x"]), 14, True)
        elif kind == "p":
            para(doc, b["x"])
        elif kind == "pc":
            para(doc, b["x"], align=WD_ALIGN_PARAGRAPH.CENTER, indent=0)
        elif kind == "li":
            para(doc, b["x"], indent=0, left=0.75)
        elif kind == "formula":
            p = doc.add_paragraph()
            pf = p.paragraph_format
            pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pf.first_line_indent = Cm(0)
            pf.space_before = Pt(6)
            pf.space_after = Pt(6)
            set_run_font(p.add_run(b["x"] + "    " + b["n"]), 14, italic=True)
        elif kind == "tbl":
            add_table(doc, b)
        elif kind == "fig":
            add_figure(doc, b, cw.BASE)
        elif kind == "pb":
            doc.add_page_break()

    cp = doc.core_properties
    cp.title = "Кори курсӣ: " + TITLE
    cp.subject = "Физиологияи нормалӣ"
    cp.author = ""
    cp.comments = ""

    os.makedirs(OUT_DIR, exist_ok=True)
    doc.save(DOCX)
    print("TOC entries:", len(entries), "| TOC pages:", toc_pages)
    print("Total pages (simulation):", total_pages)
    print("saved:", DOCX)
    return total_pages, toc_pages


if __name__ == "__main__":
    build()
