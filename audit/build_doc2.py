# -*- coding: utf-8 -*-
"""DOCX #2 — «ТАХЛИЛИ КАМБУДИҲОИ КОРИ КУРСӢ.docx»"""
import os, sys, collections
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION_START

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import doc2_data as DD
import doc2_notes as DN
import doc1_stats as S
import build_marked as BM
from docxlib import *

OUT = "ТАХЛИЛИ КАМБУДИҲОИ КОРИ КУРСӢ.docx"
SEV_FILL = {"Ҷиддӣ": "FFC7CE", "Миёна": "FFEB9C", "Кам": "E2EFDA"}

def para(doc, text, size=12, bold=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=0.0,
         italic=False, space_after=4, space_before=0, left=0.0, hanging=0.0):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.first_line_indent = Cm(indent); pf.left_indent = Cm(left)
    if hanging: pf.first_line_indent = Cm(-hanging)
    pf.space_after = Pt(space_after); pf.space_before = Pt(space_before)
    pf.line_spacing = 1.12
    p.alignment = align
    r = p.add_run(text)
    r.font.name = "Times New Roman"; r.font.size = Pt(size); r.bold = bold; r.italic = italic
    return p

def head(doc, text, size=14, before=14, after=6, align=WD_ALIGN_PARAGRAPH.LEFT):
    return para(doc, text, size=size, bold=True, align=align, space_before=before, space_after=after)

def cellp(cell, text, size=9.5, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.05
    p.alignment = align
    r = p.add_run(text); r.font.name = "Times New Roman"; r.font.size = Pt(size); r.bold = bold
    return r

def build():
    doc = BM.new_doc()
    BM.page_number_footer(doc)

    # ---------- title ----------
    para(doc, "ТАХЛИЛИ КАМБУДИҲОИ КОРИ КУРСӢ", 18, True, WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    para(doc, "Мавзӯъ: «Ултрасадои гурдаҳо: анатомияи ултрасадоӣ ва нишондиҳандаҳои меъёрӣ»",
         12.5, True, WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    para(doc, "Ҳуҷҷати дуюм аз се ҳуҷҷати аудит. Ин ҳуҷҷат рӯйхати пурраи камбудиҳоро бо рақамгузорӣ, тавсиф ва роҳи ислоҳ дар бар мегирад.",
         11, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=14)

    # ---------- 1. Хулосаи иҷмолӣ ----------
    head(doc, "1. ХУЛОСАИ ИҶМОЛӢ", 15, before=0)
    para(doc, "Кори курсӣ мавзӯи воқеан муҳимро дар бар мегирад ва аз ҷиҳати мазмун пурра аст: анатомия, физиология, физикаи ултрасадо, "
              "техникаи муоина, нишондиҳандаҳои меъёрӣ ва аҳамияти клиникӣ. Муаллиф маводи зиёдеро ҷамъ овардааст ва бахшҳои калидӣ "
              "(физиологияи нефрон, андозаҳои гурда, маҳдудиятҳои УЗИ, Допплерография) аз ҷиҳати илмӣ дурустанд.", 11.5)
    para(doc, "Дар баробари ин, кор ба талаботи расмӣ пурра ҷавоб намедиҳад. Камбудиҳо ба панҷ гурӯҳ ҷудо мешаванд:", 11.5)

    # severity summary table
    cnt = collections.Counter(d[3] for c in DD.CATEGORIES for d in c[1])
    t = doc.add_table(rows=1, cols=4); t.style = "Table Grid"; set_cell_margins(t)
    for i, hh in enumerate(["Гурӯҳи камбудиҳо", "Ҷиддӣ", "Миёна", "Кам"]):
        cellp(t.rows[0].cells[i], hh, 10, True, WD_ALIGN_PARAGRAPH.CENTER)
        cell_shading(t.rows[0].cells[i], "E8E8E8")
    for title, items in DD.CATEGORIES:
        c = collections.Counter(x[3] for x in items)
        row = t.add_row().cells
        cellp(row[0], title, 9.5)
        for i, k in enumerate(["Ҷиддӣ", "Миёна", "Кам"], start=1):
            cellp(row[i], str(c.get(k, 0)), 9.5, align=WD_ALIGN_PARAGRAPH.CENTER)
    row = t.add_row().cells
    cellp(row[0], "ҲАМАГӢ", 9.5, True)
    for i, k in enumerate(["Ҷиддӣ", "Миёна", "Кам"], start=1):
        cellp(row[i], str(cnt.get(k, 0)), 9.5, True, WD_ALIGN_PARAGRAPH.CENTER)
    for r_ in t.rows:
        r_.cells[0].width = Cm(9.5); r_.cells[1].width = Cm(2.2)
        r_.cells[2].width = Cm(2.2); r_.cells[3].width = Cm(2.2)

    para(doc, "Ҳаҷми умумӣ: 54 камбудии мушаххас (16 ҷиддӣ, 23 миёна, 15 кам) + 221 қайди инфиродӣ дар нусхаи қайдшуда "
              "(163 зард, 9 сурх, 49 сабз).", 10.5, italic=True, space_before=6, space_after=10)

    para(doc, "БАҲОИ УМУМИИ КОР (пеш аз ислоҳ): 59 аз 100 имтиёзӣ — «қаноатбахш, ҳудуди поёнӣ».", 12.5, bold=True, space_before=8, space_after=3)
    para(doc, "Асос (ниг. баҳои муфассал дар ҳуҷҷати сеюм — «ХУЛОСАИ РОҲБАРИ ИЛМӢ»): сохтори расмӣ 6/15; мазмуни илмӣ 21/25; "
              "таҳлил ва хулосабарорӣ 8/15; забон ва услуб 10/15; сарчашмаҳо ва истинодҳо 5/15; формат 9/15. "
              "Хулосаи асосӣ: мазмун хуб, аммо расмият ва сарчашмаҳо нопурра — кор барои ислоҳ баргардонида шавад.", 10.5, italic=True, space_after=10)

    # ---------- 2. Харитаи сохтор ----------
    doc.add_page_break()
    head(doc, "2. ХАРИТАИ САРЛАВҲАҲО ВА САҲИФАБАНДИИ КОР", 15, before=0)
    para(doc, "Ҷадвали зерин нишон медиҳад, ки кор дар асл чӣ сохтор дорад ва ҳар қисм чӣ камбудиро дорост.", 11)
    t2 = doc.add_table(rows=1, cols=6); t2.style = "Table Grid"; set_cell_margins(t2)
    hdrs = ["№", "Қисми кор", "Саҳифа", "Ҳолат / эзоҳ", "Баҳо", "Тавсия"]
    for i, hh in enumerate(hdrs):
        cellp(t2.rows[0].cells[i], hh, 9, True, WD_ALIGN_PARAGRAPH.CENTER)
        cell_shading(t2.rows[0].cells[i], "E8E8E8")
        repeat_header(t2.rows[0])
    for no, name, pages, note, sev, rec in DD.STRUCT:
        row = t2.add_row().cells
        cellp(row[0], no, 9, align=WD_ALIGN_PARAGRAPH.CENTER)
        cellp(row[1], name, 9, True)
        cellp(row[2], pages, 9, align=WD_ALIGN_PARAGRAPH.CENTER)
        cellp(row[3], note, 9)
        r = cellp(row[4], sev, 9, True, WD_ALIGN_PARAGRAPH.CENTER)
        set_run_shading(r, SEV_FILL.get(sev, "FFFFFF"))
        cellp(row[5], rec, 9)
    widths = [0.9, 3.6, 1.7, 5.9, 1.6, 4.6]
    for i, w in enumerate(widths):
        for row in t2.rows: row.cells[i].width = Cm(w)

    # ---------- 3. Рӯйхати пурраи камбудиҳо ----------
    doc.add_page_break()
    head(doc, "3. РӮЙХАТИ ПУРРАИ КАМБУДИҲО БО РАҚАМГУЗОРӢ", 15, before=0)
    para(doc, "Ҳар камбудӣ рақами алоҳида дорад (А1, Б2, В3 …) ва дар нусхаи қайдшуда бо ҳамин рақам қайд шудааст. "
              "Баҳо: «Ҷиддӣ» — бояд ҳатман ислоҳ шавад; «Миёна» — тавсияи қатъӣ; «Кам» — беҳтар аст ислоҳ шавад.", 10.5, italic=True)

    for cat_title, items in DD.CATEGORIES:
        head(doc, cat_title, 12.5, before=12, after=5)
        tt = doc.add_table(rows=1, cols=5); tt.style = "Table Grid"; set_cell_margins(tt)
        for i, hh in enumerate(["№", "Камбудӣ", "Ҷой / далел", "Баҳо", "Роҳи ислоҳ"]):
            cellp(tt.rows[0].cells[i], hh, 9, True, WD_ALIGN_PARAGRAPH.CENTER)
            cell_shading(tt.rows[0].cells[i], "E8E8E8")
        repeat_header(tt.rows[0])
        for code, short, where, sev, fix in items:
            row = tt.add_row().cells
            cellp(row[0], code, 9, True, WD_ALIGN_PARAGRAPH.CENTER)
            cellp(row[1], short, 9, True)
            cellp(row[2], where, 9)
            r = cellp(row[3], sev, 9, True, WD_ALIGN_PARAGRAPH.CENTER)
            set_run_shading(r, SEV_FILL.get(sev, "FFFFFF"))
            cellp(row[4], fix, 9)
        for i, w in enumerate([0.9, 4.4, 3.6, 1.5, 6.0]):
            for row in tt.rows: row.cells[i].width = Cm(w)

    # ---------- 4. Таҳлил аз рӯйи бобҳо ----------
    doc.add_page_break()
    head(doc, "4. ТАҲЛИЛИ МУФАССАЛ АЗ РӮЙИ БОБҲО", 15, before=0)
    para(doc, "Ҳар боб аз се ҷиҳат арзёбӣ шудааст: чӣ дуруст аст (сабз), чӣ нодуруст аст (зард/сурх) ва хулосаи умумӣ.", 10.5, italic=True)
    for title, items in DN.CHAPTERS:
        head(doc, title, 13, before=14, after=5)
        for kind, text in items:
            p = doc.add_paragraph()
            pf = p.paragraph_format
            pf.left_indent = Cm(0.9); pf.first_line_indent = Cm(-0.9)
            pf.space_after = Pt(4); pf.line_spacing = 1.12
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            label = {"Хуб": "✓ ДУРУСТ:", "Бад": "✗ КАМБУДӢ:", "Хулоса": "► ХУЛОСА:"}[kind]
            fill = {"Хуб": "C6EFCE", "Бад": "FFF2CC", "Хулоса": "DDEBF7"}[kind]
            r = p.add_run(label + " ")
            r.font.name = "Times New Roman"; r.font.size = Pt(10.5); r.bold = True
            set_run_shading(r, fill)
            r2 = p.add_run(text)
            r2.font.name = "Times New Roman"; r2.font.size = Pt(10.5)

    # ---------- 5. Санҷиши сарчашмаҳо ----------
    doc.add_page_break()
    head(doc, "5. САНҶИШИ САРЧАШМАҲО (SOURCE VERIFICATION)", 15, before=0)
    para(doc, "Ҳар як сарчашма бо феҳристҳои китобӣ ва интернет муқоиса карда шуд. Натиҷа:", 10.5, italic=True)
    SRC = [
     ("1", "Rumack C.M., Levine D. Diagnostic Ultrasound, 5th ed., Elsevier, 2018", "Тасдиқ шуд", "ОК", "Саҳифа ва шаҳри нашр илова шавад."),
     ("2", "Callen P.W. Ultrasonography in Obstetrics and Gynecology, 6th ed., 2016", "Тасдиқ шуд", "ОК", "Саҳифа илова шавад."),
     ("3", "Kremkau F.W. Sonography Principles and Instruments, 10th ed., 2020", "Тасдиқ шуд", "ОК", "Саҳифа илова шавад."),
     ("4", "Grainger & Allison's Diagnostic Radiology, Elsevier", "Нопурра", "Миёна", "Сол, нашриёт, саҳифа нест."),
     ("5", "Standring S. Gray's Anatomy, 42nd ed., 2020", "Тасдиқ шуд", "ОК", "Саҳифа илова шавад."),
     ("6", "Moore K.L. Clinically Oriented Anatomy, 8th ed., 2018", "Тасдиқ шуд", "ОК", "Саҳифа илова шавад."),
     ("7", "Guyton and Hall Textbook of Medical Physiology, 14th ed., 2021", "Тасдиқ шуд", "ОК", "—"),
     ("8", "Hall J.E., Hall M.E. Guyton and Hall, Elsevier, 2021", "Такрорӣ бо №7", "Ҷиддӣ", "Нест карда шавад."),
     ("9", "Rumack C.M., Wilson S.R., Charboneau J.W. Diagnostic Ultrasound, Mosby, 2005", "Такрорӣ/кӯҳна (бо №1)", "Миёна", "Иваз карда шавад бо сарчашмаи нав."),
     ("10", "Hricak H., Choyke P.L., Eberhardt S.C. Imaging of the Kidney and Urinary Tract", "ТАСДИҚ НАШУД", "Ҷиддӣ",
      "Китоби мазкур вуҷуд надорад. Иловатан матни тоҷикӣ дар сарчашмаи англисӣ — «Китобҳо ва дастурҳои радиологияи ташхисӣ» — аломати нусхабардорӣ аз манбаи дигар."),
     ("11", "EAU Guidelines on Urolithiasis", "Тасдиқ шуд (ҳуҷҷати расмӣ)", "Миёна", "Сол, версия, URL, санаи муроҷиат лозим."),
     ("12", "EAU Guidelines on Renal Cell Carcinoma", "Тасдиқ шуд (ҳуҷҷати расмӣ)", "Миёна", "Сол, версия, URL, санаи муроҷиат лозим."),
     ("13", "KDIGO 2024 Clinical Practice Guideline for CKD", "Тасдиқ шуд", "ОК", "URL ва санаи муроҷиат илова шавад."),
     ("14", "AIUM Practice Parameters … Abdomen and Retroperitoneum", "Тасдиқ шуд (ҳуҷҷати расмӣ)", "Миёна", "Сол ва URL лозим."),
     ("15", "WHO. Kidney Disease: Information and Health Recommendations", "ТАСДИҚ НАШУД", "Ҷиддӣ",
      "Нашрияи СҲТ бо ин ном ёфт нашуд. Ҳуҷҷатҳои воқеии СҲТ (EB156) номи дигар доранд."),
     ("16", "Radiopaedia", "Сайт мавҷуд", "Миёна", "URL, муаллиф, санаи муроҷиат лозим."),
     ("17", "NIDDK", "Сайт мавҷуд", "Миёна", "URL, санаи муроҷиат лозим."),
     ("18", "National Kidney Foundation (NKF)", "Сайт мавҷуд", "Миёна", "URL, санаи муроҷиат лозим."),
     ("19", "European Society of Radiology (ESR)", "Сайт мавҷуд", "Миёна", "URL, санаи муроҷиат лозим."),
     ("20", "American College of Radiology (ACR)", "Сайт мавҷуд", "Миёна", "URL, санаи муроҷиат лозим."),
    ]
    t3 = doc.add_table(rows=1, cols=5); t3.style = "Table Grid"; set_cell_margins(t3)
    for i, hh in enumerate(["№", "Сарчашма (тавре ки дар кор)", "Натиҷаи санҷиш", "Ҳолат", "Эзоҳ"]):
        cellp(t3.rows[0].cells[i], hh, 8.5, True, WD_ALIGN_PARAGRAPH.CENTER)
        cell_shading(t3.rows[0].cells[i], "E8E8E8")
    repeat_header(t3.rows[0])
    for no, src, res, st, note in SRC:
        row = t3.add_row().cells
        cellp(row[0], no, 8.5, align=WD_ALIGN_PARAGRAPH.CENTER)
        cellp(row[1], src, 8.5)
        cellp(row[2], res, 8.5, True)
        r = cellp(row[3], st, 8.5, True, WD_ALIGN_PARAGRAPH.CENTER)
        fill = {"ОК": "C6EFCE", "Миёна": "FFEB9C", "Ҷиддӣ": "FFC7CE"}[st]
        set_run_shading(r, fill)
        cellp(row[4], note, 8.5)
    for i, w in enumerate([0.8, 5.6, 2.9, 1.5, 5.6]):
        for row in t3.rows: row.cells[i].width = Cm(w)

    para(doc, "ХУЛОСАИ САНҶИШ: аз 20 сарчашма — 7 сарчашмаи пурра тасдиқшуда, 9 сарчашма боэътимод вале нопурра, "
              "2 сарчашмаи тасдиқнашуда (№10, №15), 2 сарчашмаи такрорӣ (№8, №9).", 10.5, bold=True, space_before=8)

    # ---------- 6. Таҳлили такрор ва номутавозинӣ ----------
    doc.add_page_break()
    head(doc, "6. ТАКРОР ВА НОМУТАВОЗИНӢ ДАР КОР", 15, before=0)
    head(doc, "6.1. Такрорҳои мазмунӣ", 12.5, before=10)
    for t_ in [
      "Оғози БОБИ 1 ва МУҚАДДИМА — як фикр дар бораи муҳимияти гурдаҳо (саҳ. 2 ва 3).",
      "Ҷумлаи «ташхиси ултрасадоӣ яке аз усулҳои муҳим…» дар саҳ. 2, 13, 18, 26 ва 39 такрор мешавад.",
      "Ҷадвали «Усул | Имконият | Афзалият | Маҳдудият» дар саҳ. 42 ва 49–50 якхела аст.",
      "Рӯйхати сабабҳои баландшавии эхогения дар саҳ. 34 ва 36 такрор шудааст (Гломерулонефрит, Пиелонефрити музмин, Склероз ва ғ.).",
      "Рӯйхати афзалиятҳои УЗИ дар саҳ. 21, 39–41 ва 47 такрор мешавад.",
    ]:
        para(doc, "— " + t_, 10.5, space_after=3, left=0.6, hanging=0.6)
    head(doc, "6.2. Номутавозинӣ дар ҳаҷм", 12.5, before=10)
    HV = [("МУҚАДДИМА", "1 саҳ.", "Хеле кӯтоҳ — бояд 2–3 саҳифа бошад."),
          ("БОБИ 1", "11 саҳ.", "Мутавозин."),
          ("БОБИ 2", "13 саҳ.", "Мутавозин, аммо сохтор хурд-хурд шудааст."),
          ("БОБИ 3", "14 саҳ.", "Мутавозин."),
          ("БОБИ 4", "17 саҳ.", "Калон; зербоби 4.2 танҳо 7 саҳифа."),
          ("ХУЛОСА", "1,5 саҳ.", "Мутавозин.")]
    t4 = doc.add_table(rows=1, cols=3); t4.style = "Table Grid"; set_cell_margins(t4)
    for i, hh in enumerate(["Қисм", "Ҳаҷм", "Эзоҳ"]):
        cellp(t4.rows[0].cells[i], hh, 9.5, True, WD_ALIGN_PARAGRAPH.CENTER)
        cell_shading(t4.rows[0].cells[i], "E8E8E8")
    for a, b, c_ in HV:
        row = t4.add_row().cells
        cellp(row[0], a, 9.5, True); cellp(row[1], b, 9.5, align=WD_ALIGN_PARAGRAPH.CENTER); cellp(row[2], c_, 9.5)
    for i, w in enumerate([4.5, 3.0, 8.9]):
        for row in t4.rows: row.cells[i].width = Cm(w)

    # ---------- 7. Нақшаи ислоҳот ----------
    doc.add_page_break()
    head(doc, "7. НАҚШАИ ИСЛОҲОТ БА ТАРТИБИ АВЛАВИЯТ", 15, before=0)
    PLAN = [
     ("1", "САРЛАВҲА ВА МУҚАДДИМА", "2–3 соат",
      "Сохтани саҳифаи сарлавҳа; навиштани мубрамият (бо 2–3 рақам ва сарчашма), дараҷаи омӯзиш (3–5 муаллиф), мақсад (1 ҷумла), "
      "вазифаҳо (4–5), объект, предмет, усулҳо, сохтор. Ин бузургтарин афзоиши баҳо аст.", "Ҷиддӣ"),
     ("2", "САРЧАШМАҲО ВА ИСТИНОДҲО", "3–4 соат",
      "Илова кардани истинодҳо дар матн ([1], [2] … ё сноскаҳо); ислоҳи №10 ва №15; нест кардани такрорҳо (№8, №9); "
      "тоза кардани URL-ҳо аз utm_source; илова кардани санаи муроҷиат; илова кардани 3–5 сарчашмаи тоҷикӣ/русӣ; "
      "аз нав тартиб додан тибқи ГОСТ 7.1–2003.", "Ҷиддӣ"),
     ("3", "ИСЛОҲИ ХАТОҲОИ ИЛМӢ", "1–2 соат",
      "«Ҳалқумчаи пешоб» → «Пешоббарор»; ислоҳи фазои капсулавӣ; «15–25 мм» → «15–20 мм» дар се ҷой; "
      "ислоҳи тартиби шохаҳои артерия; «эхогеннокӣ» → «эхогения»; ислоҳи ҷумлаи саҳ. 39 («УЗИ … муайян карда мешавад»).", "Ҷиддӣ"),
     ("4", "СОХТОР ВА РАҚАМГУЗОРӢ", "2 соат",
      "Рақамгузории сарлавҳаҳои дохилӣ; баровардани ХУЛОСА аз саҳифаи нав; нест кардани ҷадвали такрорӣ; "
      "мутобиқ кардани номгузории ҷадвалҳо (Ҷадвали 1, 2 …); мутобиқ кардани зербобҳо бо муқаддима.", "Ҷиддӣ"),
     ("5", "ТАҲРИРИ ЗАБОН", "2–3 соат",
      "Ислоҳи 123 ҳолати фосилаи набуда баъди нуқта; ислоҳи аломатҳои рӯйхат; якхела кардани низоми рӯйхат; "
      "ислоҳи «пешгирӣ», «ҳавзаҳо», «ғайриинвазивӣ»; тақсим кардани ҷумлаҳои дароз.", "Миёна"),
     ("6", "ФОРМАТИРОВКА", "1–2 соат",
      "Ҳошияҳо (3 / 1,5 / 2 / 2 см); рақами саҳифа; фосилаи 1,5; ҷадвалҳоро ҳамчун ҷадвали воқеӣ сохтан; "
      "нест кардани чорчӯбаи ороишӣ; якхела кардани ҷойгиршавии сарлавҳаҳо.", "Ҷиддӣ"),
    ]
    t5 = doc.add_table(rows=1, cols=5); t5.style = "Table Grid"; set_cell_margins(t5)
    for i, hh in enumerate(["#", "Қадам", "Вақт", "Амалҳо", "Баҳо"]):
        cellp(t5.rows[0].cells[i], hh, 9, True, WD_ALIGN_PARAGRAPH.CENTER)
        cell_shading(t5.rows[0].cells[i], "E8E8E8")
    repeat_header(t5.rows[0])
    for no, name, dur, acts, sev in PLAN:
        row = t5.add_row().cells
        cellp(row[0], no, 9, True, WD_ALIGN_PARAGRAPH.CENTER)
        cellp(row[1], name, 9, True)
        cellp(row[2], dur, 9, align=WD_ALIGN_PARAGRAPH.CENTER)
        cellp(row[3], acts, 9)
        r = cellp(row[4], sev, 9, True, WD_ALIGN_PARAGRAPH.CENTER)
        set_run_shading(r, SEV_FILL[sev])
    for i, w in enumerate([0.8, 3.4, 1.7, 8.6, 1.6]):
        for row in t5.rows: row.cells[i].width = Cm(w)

    para(doc, "Ҳаҷми умумии вақти тахминӣ: 11–16 соат. Тавсия: тартиби 1 → 2 → 3 → 4 → 5 → 6 риоя шавад — "
              "аввал сохтор ва манбаъҳо, баъд матн ва формат.", 11, bold=True, space_before=8)

    # ---------- 8. Маҳдудиятҳои аудит ----------
    doc.add_page_break()
    head(doc, "8. МАҲДУДИЯТҲОИ АУДИТ ВА ҲУДУДИ ТАҲЛИЛ", 15, before=0)
    for t_ in [
      "Тасвирҳо ва расмҳо дар кор мавҷуд нестанд — сифати онҳо арзёбӣ нашудааст (баҳогузории графика мавзӯи алоҳида аст).",
      "Ҷадвалҳои аслӣ бо фосила сохта шудаанд; мазмуни катакҳо аз рӯйи мавқеи матн дар PDF барқарор карда шуданд. "
      "Эҳтимоли хурди нодуруст ҷойгиршавии як катак вуҷуд дорад — ҳангоми истифода бо файли аслӣ муқоиса кунед.",
      "Сарчашмаҳои №10 ва №15 дар интернет ёфт нашуданд. Ин маънои онро надорад, ки онҳо ҳатман сохтаанд — "
      "имкон аст, ки номгӯи онҳо нодуруст навишта шуда бошад. Ҳарду бояд аз ҷониби донишҷӯ тафтиш шаванд.",
      "Талаботи расмии муассиса (ГОСТ ё дастур) ба мо пешниҳод нашудааст. Ҳамаи меъёрҳои форматӣ дар ин ҳуҷҷат "
      "ҳамчун меъёрҳои УМУМИИ ГОСТ 7.1–2003, ГОСТ 2.105 ва амалияи маъмули корҳои курсӣ нишон дода шудаанд. "
      "Агар муассиса талаботи худро дошта бошад, онҳо афзалият доранд.",
      "Баҳои 59/100 тахминӣ аст ва ба меъёрҳои умумӣ асос ёфтааст; баҳои ниҳоӣ аз ҷониби роҳбари илмӣ дода мешавад.",
    ]:
        para(doc, "— " + t_, 10.5, space_after=4, left=0.6, hanging=0.6)

    return doc

if __name__ == "__main__":
    doc = build()
    doc.save(OUT)
    print("saved", OUT, "paras", len(doc.paragraphs), "tables", len(doc.tables))
