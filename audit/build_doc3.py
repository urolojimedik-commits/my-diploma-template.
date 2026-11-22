# -*- coding: utf-8 -*-
"""DOCX #3 — «ХУЛОСАИ РОҲБАРИ ИЛМӢ.docx» (100-ball rubric)."""
import os, sys
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import doc3_data as D3
import build_marked as BM
from docxlib import *

OUT = "ХУЛОСАИ РОҲБАРИ ИЛМӢ.docx"

def para(doc, text, size=12, bold=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=0.0,
         italic=False, space_after=5, space_before=0, left=0.0, hanging=0.0, color=None):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.first_line_indent = Cm(indent); pf.left_indent = Cm(left)
    if hanging: pf.first_line_indent = Cm(-hanging)
    pf.space_after = Pt(space_after); pf.space_before = Pt(space_before)
    pf.line_spacing = 1.15
    p.alignment = align
    r = p.add_run(text)
    r.font.name = "Times New Roman"; r.font.size = Pt(size); r.bold = bold; r.italic = italic
    if color: r.font.color.rgb = RGBColor(*color)
    return p

def head(doc, text, size=14, before=14, after=6, align=WD_ALIGN_PARAGRAPH.LEFT):
    return para(doc, text, size=size, bold=True, align=align, space_before=before, space_after=after)

def cellp(cell, text, size=9.5, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.08
    p.alignment = align
    r = p.add_run(text); r.font.name = "Times New Roman"; r.font.size = Pt(size); r.bold = bold
    return r

def build():
    doc = BM.new_doc()
    BM.page_number_footer(doc)

    para(doc, "ХУЛОСАИ РОҲБАРИ ИЛМӢ", 18, True, WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    para(doc, "дар бораи кори курсии донишҷӯ", 12, False, WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    para(doc, "Мавзӯъ: «Ултрасадои гурдаҳо: анатомияи ултрасадоӣ ва нишондиҳандаҳои меъёрӣ»",
         12.5, True, WD_ALIGN_PARAGRAPH.CENTER, space_after=12)

    # evaluation profile
    t0 = doc.add_table(rows=0, cols=2); t0.style = "Table Grid"; set_cell_margins(t0)
    for k, v in [("Ҳуҷҷатҳои замимашуда", "1) КОРИ КУРСӢ БО ИШОРАҲОИ САНҶИШӢ; 2) ТАХЛИЛИ КАМБУДИҲОИ КОРИ КУРСӢ"),
                 ("Санаи баҳогузорӣ", "22 ноябри 2026"),
                 ("Ҳаҷми кор", "57 саҳифа, 4 боб, 20 сарчашма, 10 ҷадвал"),
                 ("Баҳои умумӣ", "{{TOTAL}} / 100"),
                 ("Баҳои тавсияшуда", "{{GRADE}}")]:
        cells = t0.add_row().cells
        p0 = cells[0].paragraphs[0]; p0.paragraph_format.first_line_indent = Cm(0)
        r0 = p0.add_run(k); r0.bold = True; r0.font.name = "Times New Roman"; r0.font.size = Pt(10.5)
        p1 = cells[1].paragraphs[0]; p1.paragraph_format.first_line_indent = Cm(0)
        r1 = p1.add_run(v); r1.font.name = "Times New Roman"; r1.font.size = Pt(10.5)
        if k == "Баҳои умумӣ": r1.bold = True
        cells[0].width = Cm(5.2); cells[1].width = Cm(11.3)

    # ---- 1. rubric ----
    doc.add_page_break()
    head(doc, "1. БАҲОГУЗОРИИ МУФАССАЛ АЗ РӮЙИ 100 БАЛЛ", 15, before=0)
    para(doc, "Меъёрҳои баҳогузорӣ тибқи талаботи умумии баҳогузории корҳои курсии муассисаҳои тиббӣ муайян карда шудаанд. "
              "Ҳар меъёр аз рӯйи корҳои воқеии кор баҳо гирифт.", 10.5, italic=True)

    total = 0; maxt = 0
    for name, mx, got, minus, plus, fix in D3.RUBRIC:
        total += got; maxt += mx
        # heading with score
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.space_before = Pt(12); pf.space_after = Pt(4); pf.first_line_indent = Cm(0)
        r = p.add_run(f"{name}")
        r.bold = True; r.font.name = "Times New Roman"; r.font.size = Pt(12.5)
        r2 = p.add_run(f"   — {got} / {mx}")
        r2.bold = True; r2.font.name = "Times New Roman"; r2.font.size = Pt(12.5)
        if got / mx >= 0.8: set_run_color(r2, "006100")
        elif got / mx >= 0.55: set_run_shading(r2, "FFEB9C")
        else: set_run_shading(r2, "FFC7CE"); set_run_color(r2, "C00000")

        # mini bar
        pb = doc.add_paragraph(); pb.paragraph_format.first_line_indent = Cm(0)
        pb.paragraph_format.space_after = Pt(6)
        filled = int(round(30 * got / mx))
        rb = pb.add_run("█" * filled + "░" * (30 - filled))
        rb.font.name = "Consolas"; rb.font.size = Pt(9)
        set_run_color(rb, "006100" if got / mx >= 0.8 else ("BF8F00" if got / mx >= 0.55 else "C00000"))

        for label, text, fill in (("Чӣ кам шуд:", minus, "FFC7CE"),
                                  ("Чӣ дуруст аст:", plus, "C6EFCE"),
                                  ("Роҳи ислоҳ:", fix, "DDEBF7")):
            pp = doc.add_paragraph()
            ppf = pp.paragraph_format
            ppf.left_indent = Cm(0.2); ppf.space_after = Pt(3); ppf.line_spacing = 1.12
            ppf.first_line_indent = Cm(0)
            rr = pp.add_run(label + " ")
            rr.bold = True; rr.font.name = "Times New Roman"; rr.font.size = Pt(10.5)
            set_run_shading(rr, fill)
            rr2 = pp.add_run(text)
            rr2.font.name = "Times New Roman"; rr2.font.size = Pt(10.5)

    # total row
    head(doc, "ҶАМЪБАСТ", 13, before=14, after=5)
    tt = doc.add_table(rows=1, cols=3); tt.style = "Table Grid"; set_cell_margins(tt)
    for i, hh in enumerate(["Меъёр", "Балл", "Ҳисса"]):
        cellp(tt.rows[0].cells[i], hh, 10, True, WD_ALIGN_PARAGRAPH.CENTER)
        cell_shading(tt.rows[0].cells[i], "E8E8E8")
    for name, mx, got, *_ in D3.RUBRIC:
        row = tt.add_row().cells
        cellp(row[0], name, 10)
        cellp(row[1], f"{got} / {mx}", 10, True, WD_ALIGN_PARAGRAPH.CENTER)
        cellp(row[2], f"{got/mx*100:.0f} %", 10, align=WD_ALIGN_PARAGRAPH.CENTER)
    row = tt.add_row().cells
    cellp(row[0], "ҲАМАГӢ", 10.5, True)
    cellp(row[1], f"{total} / {maxt}", 10.5, True, WD_ALIGN_PARAGRAPH.CENTER)
    cellp(row[2], f"{total/maxt*100:.0f} %", 10.5, True, WD_ALIGN_PARAGRAPH.CENTER)
    for r_ in tt.rows:
        r_.cells[0].width = Cm(9.0); r_.cells[1].width = Cm(3.2); r_.cells[2].width = Cm(3.0)

    # ---- 2. scale ----
    doc.add_page_break()
    head(doc, "2. МИҚЁСИ БАҲОГУЗОРӢ", 15, before=0)
    t2 = doc.add_table(rows=1, cols=3); t2.style = "Table Grid"; set_cell_margins(t2)
    for i, hh in enumerate(["Балл", "Баҳо", "Тавсиф"]):
        cellp(t2.rows[0].cells[i], hh, 10, True, WD_ALIGN_PARAGRAPH.CENTER)
        cell_shading(t2.rows[0].cells[i], "E8E8E8")
    for b, g, d in D3.GRADE_SCALE:
        row = t2.add_row().cells
        cellp(row[0], b, 10, align=WD_ALIGN_PARAGRAPH.CENTER)
        cellp(row[1], g, 10, True)
        cellp(row[2], d, 10)
    for r_ in t2.rows:
        r_.cells[0].width = Cm(2.6); r_.cells[1].width = Cm(5.0); r_.cells[2].width = Cm(8.9)

    # ---- 3. recommendation ----
    doc.add_page_break()
    head(doc, "3. ХУЛОСА ВА ТАВСИЯИ РОҲБАРИ ИЛМӢ", 15, before=0)
    for txt in D3.RECOMMENDATION.split("\n\n"):
        para(doc, txt, 11.5, indent=1.0, space_after=8)

    head(doc, "ТАВСИЯИ НИҲОӢ", 13, before=10, after=6)
    para(doc, D3.RECOMMENDATION_2, 11.5, indent=1.0, space_after=8)

    verdict = doc.add_table(rows=1, cols=1); verdict.style = "Table Grid"; set_cell_margins(verdict)
    cell = verdict.rows[0].cells[0]
    cell.text = ""
    p = cell.paragraphs[0]; p.paragraph_format.first_line_indent = Cm(0); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("ҚАРОР: КОР БАРОИ ИСЛОҲ БАРГАРДОНИДА ШАВАД")
    r.bold = True; r.font.name = "Times New Roman"; r.font.size = Pt(13)
    cell_shading(cell, "FFC7CE")
    p2 = cell.add_paragraph(); p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.first_line_indent = Cm(0)
    r2 = p2.add_run("Баҳои ҷорӣ: {{TOTAL}}/100. Баъди ислоҳи камбудиҳои дар ҳуҷҷати дуюм нишондодашуда кор метавонад ба 85–90/100 умедвор бошад.")
    r2.font.name = "Times New Roman"; r2.font.size = Pt(10.5)

    # ---- 4. signing ----
    head(doc, "4. ИМЗОҲО", 15, before=18)
    para(doc, "Роҳбари илмии кор: _______________________________ / ______________________ /",
         11.5, space_before=16, space_after=14)
    para(doc, "Донишҷӯ: _______________________________ / ______________________ /",
         11.5, space_after=20)
    para(doc, "Санаи баҳогузорӣ: «______» ________________ 20____ с.", 11.5, space_after=18)
    para(doc, "ЭЗОҲ: ин ҳуҷҷат ҳамчун намунаи хулосаи роҳбари илмӣ таҳия шудааст. Имзоҳо танҳо баъди мувофиқа бо роҳбари воқеӣ гузошта мешаванд. "
              "Баҳо ва қарори ниҳоӣ ҳаққи роҳбари илмӣ мебошад; баҳои дар ин ҳуҷҷат овардашуда арзёбии мустақили аудит аст.",
         10, italic=True, space_before=14)

    # replace placeholders
    grade = "Қаноатбахш (3) — ҳудуди поёнӣ"
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    for r in p.runs:
                        if "{{TOTAL}}" in r.text: r.text = r.text.replace("{{TOTAL}}", str(total))
                        if "{{GRADE}}" in r.text: r.text = r.text.replace("{{GRADE}}", grade)
    for p in doc.paragraphs:
        for r in p.runs:
            if "{{TOTAL}}" in r.text: r.text = r.text.replace("{{TOTAL}}", str(total))
            if "{{GRADE}}" in r.text: r.text = r.text.replace("{{GRADE}}", grade)

    return doc, total, maxt

if __name__ == "__main__":
    doc, total, maxt = build()
    doc.save(OUT)
    print("saved", OUT, "total", total, "/", maxt, "paras", len(doc.paragraphs), "tables", len(doc.tables))
