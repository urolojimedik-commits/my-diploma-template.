# -*- coding: utf-8 -*-
"""Builds DOCX #1 — «КОРИ КУРСӢ БО ИШОРАҲОИ САНҶИШӢ.docx»."""
import json, os, sys, collections
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.enum.section import WD_SECTION_START

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_copy as RC
import frontmatter as FM
import doc1_stats as S
import build_marked as BM
from docxlib import *

OUT = "КОРИ КУРСӢ БО ИШОРАҲОИ САНҶИШӢ.docx"
AUTHOR, INIT = RC.AUTHOR, RC.INIT

def para(doc, text, size=12, bold=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=0.0,
         italic=False, space_after=4, space_before=0, left=0.0, hanging=0.0):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.first_line_indent = Cm(indent)
    pf.left_indent = Cm(left)
    if hanging: pf.first_line_indent = Cm(-hanging)
    pf.space_after = Pt(space_after); pf.space_before = Pt(space_before)
    pf.line_spacing = 1.15
    p.alignment = align
    r = p.add_run(text)
    r.font.name = "Times New Roman"; r.font.size = Pt(size); r.bold = bold; r.italic = italic
    return p

def head(doc, text, size=14, before=12, after=6, align=WD_ALIGN_PARAGRAPH.LEFT):
    return para(doc, text, size=size, bold=True, align=align, space_before=before, space_after=after)

def build():
    doc = BM.new_doc()
    BM.page_number_footer(doc)

    # ---------------- FRONT MATTER ----------------
    para(doc, "ҲУҶҶАТИ АУДИТ", 18, True, WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    para(doc, "ба кори курсии «Ултрасадои гурдаҳо: анатомияи ултрасадоӣ ва нишондиҳандаҳои меъёрӣ»",
         13, True, WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    para(doc, "Нусхаи қайдшуда (marked copy). Файли аслии донишҷӯ тағйир дода нашудааст.",
         11, False, WD_ALIGN_PARAGRAPH.CENTER, italic=True, space_after=12)

    # meta table (numbers filled after render — use placeholders replaced later)
    meta_tbl = doc.add_table(rows=0, cols=2); meta_tbl.style = "Table Grid"; set_cell_margins(meta_tbl)
    meta = [("Ҳаҷми кор", "57 саҳифа; 4 боб; муқаддима; хулоса; 20 сарчашма; 10 ҷадвал"),
            ("Ҳаҷми матни таҳлилшуда", "117 273 аломат"),
            ("Ҳаҷми матни хондашуда", "100 % — ҳамаи 57 саҳифа, аз ҷумла ҳамаи ҷадвалҳо"),
            ("Санаи аудит", "22 ноябри 2026"),
            ("Шумораи умумӣ қайдҳо", "{{TOTAL}}"),
            ("Қайдҳои зард / сурх / сабз", "{{COUNTS}}")]
    for k, v in meta:
        cells = meta_tbl.add_row().cells
        p0 = cells[0].paragraphs[0]; p0.paragraph_format.first_line_indent = Cm(0)
        r0 = p0.add_run(k); r0.bold = True; r0.font.name = "Times New Roman"; r0.font.size = Pt(10.5)
        p1 = cells[1].paragraphs[0]; p1.paragraph_format.first_line_indent = Cm(0)
        r1 = p1.add_run(v); r1.font.name = "Times New Roman"; r1.font.size = Pt(10.5)
        cells[0].width = Cm(4.8); cells[1].width = Cm(11.7)
    doc.add_paragraph()

    for kind, text in FM.ANNOTATION:
        if kind == "h": head(doc, text, 14, before=10)
        else: para(doc, text, 11.5, space_after=5)

    head(doc, "ШАРТҲОИ РАНГҲО", 14, before=12)
    lt = doc.add_table(rows=0, cols=3); lt.style = "Table Grid"; set_cell_margins(lt)
    fills = {"yellow": "FFFF00", "red": "FFC7CE", "green": "C6EFCE"}
    for colour, name, desc in FM.LEGEND:
        cells = lt.add_row().cells
        p = cells[0].paragraphs[0]; p.paragraph_format.first_line_indent = Cm(0)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(" МИСОЛ "); r.font.size = Pt(10); set_run_shading(r, fills[colour])
        if colour == "red": set_run_color(r, "C00000")
        p2 = cells[1].paragraphs[0]; p2.paragraph_format.first_line_indent = Cm(0)
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rr = p2.add_run(name); rr.bold = True; rr.font.name = "Times New Roman"; rr.font.size = Pt(10.5)
        p3 = cells[2].paragraphs[0]; p3.paragraph_format.first_line_indent = Cm(0)
        rr3 = p3.add_run(desc); rr3.font.name = "Times New Roman"; rr3.font.size = Pt(10.5)
        cells[0].width = Cm(2.3); cells[1].width = Cm(2.2); cells[2].width = Cm(12.0)

    para(doc, "Қайдҳо ҳамчун шарҳи Word (Word comment) ба ҳар як қисми матн замима шудаанд. "
              "Барои дидани онҳо: Review → Show Comments. Ҳамин қайдҳо дар файли дуюм — «ТАХЛИЛИ КАМБУДИҲОИ КОРИ КУРСӢ» — ҳамчун рӯйхати рақамгузорӣ оварда шудаанд.",
         10.5, italic=True, space_after=8)

    # summary of the 5 main problems (helps the reader)
    head(doc, "ПАНҶ КАМБУДИИ АСОСИИ КОР", 13, before=10)
    for i, t in enumerate([
        "САРЛАВҲА ВА МУҚАДДИМА: саҳифаи сарлавҳа нест; мубрамият, мақсад, вазифаҳо, объект, предмет, усулҳо ва сохтор муайян нашудаанд.",
        "САРЧАШМАҲО: 20 сарчашма, вале дар матн ЯГОН истинод нест; 2 сарчашма тасдиқ нашуд; 2 сарчашма такроранд; барои манбаъҳои электронӣ URL ва санаи муроҷиат нест.",
        "ИСТИЛОҲОТ: «ҳалқумчаи пешоб» ба ҷои «пешоббарор»; «ғайриинвазивӣ» ба ҷои «инвазивӣ»; «эхогеннокӣ» ба ҷои «эхогения»; тартиби шохаҳои артерия нодуруст.",
        "РАҚАМҲО: ғафсии умумии паренхима «15–25 мм» — аз меъёри адабӣ (15–20 мм) зиёд, бе сарчашма.",
        "ФОРМАТ: рақами саҳифа нест; ҷадвалҳо бо фосила сохта шудаанд; сарлавҳаҳо рақамгузории номуназзам доранд; ХУЛОСА дар мобайни саҳифа оғоз мешавад."], 1):
        para(doc, f"{i}. {t}", 11, space_after=3, left=0.5, hanging=0.5)

    # ---------------- MARKED COPY ----------------
    doc.add_section(WD_SECTION_START.NEW_PAGE)
    head(doc, "НУСХАИ ҚАЙДШУДАИ КОР", 15, before=0, after=6, align=WD_ALIGN_PARAGRAPH.CENTER)
    para(doc, "Матн аз рӯйи файли аслии PDF (57 саҳифа) барқарор карда шудааст. Сохтор, рақамгузорӣ, тартиби бобҳо ва мазмуни ҷадвалҳо нигоҳ дошта шудаанд. "
              "Ҷадвалҳо аз нав ҳамчун ҷадвали воқеии Word сохта шудаанд, вале мазмуни катакҳо тағйир наёфтааст.",
         10.5, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    RC.render_copy(doc)

    # ---------------- BACK MATTER ----------------
    doc.add_page_break()
    for kind, text in FM.CLOSING:
        if kind == "h":
            head(doc, text, 15, before=0, after=8, align=WD_ALIGN_PARAGRAPH.CENTER)
        elif kind == "li":
            para(doc, "— " + text, 11, space_after=4, left=0.6, hanging=0.6)
        else:
            para(doc, text, 11, indent=0.9, space_after=5)

    # ---------------- STATISTICS ----------------
    doc.add_page_break()
    head(doc, "ОМОРИ ҚАЙДҲО АЗ РӮЙИ НАВЪ", 15, before=0, after=8, align=WD_ALIGN_PARAGRAPH.CENTER)
    c = collections.Counter()
    for (code, colour), n in RC.CMT.items(): c[code] += n
    st = doc.add_table(rows=1, cols=3); st.style = "Table Grid"; set_cell_margins(st)
    for i, hh in enumerate(["Навъи қайд", "Ранг", "Шумора"]):
        cell = st.rows[0].cells[i]; cell.text = ""
        p = cell.paragraphs[0]; p.paragraph_format.first_line_indent = Cm(0)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(hh); r.bold = True; r.font.name = "Times New Roman"; r.font.size = Pt(10.5)
        cell_shading(cell, "E8E8E8")
    for name, codes in S.GROUPS:
        n = sum(c.get(k, 0) for k in codes)
        colours = {RC.CMT.get((k, "yellow"), None) for k in codes}
        # determine dominant colour
        dom = "сабз" if all(k.startswith(("С","Б","Х","М")) and k not in ("С1","С2","С3","С4","С6","С7","С8","С10","С11","С13","С18","С19","С20","С21","С23","С24","С26","С27","С30","С32","С33","С36","С38") for k in codes) else ""
        row = st.add_row().cells
        for i, v in enumerate([name, dom or "омехта", str(n)]):
            cell = row[i]; cell.text = ""
            p = cell.paragraphs[0]; p.paragraph_format.first_line_indent = Cm(0)
            r = p.add_run(v); r.font.name = "Times New Roman"; r.font.size = Pt(10)
            if i: p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    # total row
    trow = st.add_row().cells
    tot_all = sum(sum(c.get(k, 0) for k in cds) for _, cds in S.GROUPS)
    for i, v in enumerate(["ҲАМАГӢ", "—", str(tot_all)]):
        cell = trow[i]; cell.text = ""
        p = cell.paragraphs[0]; p.paragraph_format.first_line_indent = Cm(0)
        r = p.add_run(v); r.bold = True; r.font.name = "Times New Roman"; r.font.size = Pt(10)
        if i: p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cell_shading(cell, "E8E8E8")
    for r_ in st.rows:
        r_.cells[0].width = Cm(10.2); r_.cells[1].width = Cm(2.6); r_.cells[2].width = Cm(1.9)
    total = sum(c.values())
    y = RC.TOTAL["yellow"]; rr = RC.TOTAL["red"]; g = RC.TOTAL["green"]
    para(doc, f"Ҳамагӣ: {total} қайд — зард: {y}, сурх: {rr}, сабз: {g}.", 11, bold=True, space_before=8, space_after=6)
    para(doc, "Шарҳ: шумораи зиёди қайдҳои зард асосан аз сабаби фосилаи набуда баъди нуқта (Л1) мебошад, ки дар тамоми матн такрор мешавад — "
              "ин як камбудии системавӣ аст, на садҳо хатои алоҳида.", 10.5, italic=True, space_after=6)

    # replace placeholders
    for p in doc.paragraphs:
        for r in p.runs:
            if "{{TOTAL}}" in r.text:
                r.text = r.text.replace("{{TOTAL}}", str(total))
            if "{{COUNTS}}" in r.text:
                r.text = r.text.replace("{{COUNTS}}", f"{y} / {rr} / {g}")
    for t in doc.tables:
        for row2 in t.rows:
            for cell in row2.cells:
                for p in cell.paragraphs:
                    for r in p.runs:
                        if "{{TOTAL}}" in r.text:
                            r.text = r.text.replace("{{TOTAL}}", str(total))
                        if "{{COUNTS}}" in r.text:
                            r.text = r.text.replace("{{COUNTS}}", f"{y} / {rr} / {g}")
    return doc, total, y, rr, g

if __name__ == "__main__":
    doc, total, y, rr, g = build()
    doc.save(OUT)
    print("saved", OUT)
    print("paragraphs", len(doc.paragraphs), "tables", len(doc.tables), "comments", len(doc.comments))
    print("total", total, "yellow", y, "red", rr, "green", g)
