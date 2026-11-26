#!/usr/bin/env python3
"""Assemble the full course-work DOCX from Markdown chapters, tables, figures,
and references.json using coursework/tools/docx_helpers.py."""

import json
import re
import sys
from pathlib import Path

ROOT = Path('/home/user/my-diploma-template.')
CONTENT = ROOT / 'coursework' / 'content'
TOOLS = ROOT / 'coursework' / 'tools'
sys.path.insert(0, str(TOOLS))

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm
import docx_helpers

OUT = ROOT / 'coursework' / 'qa' / 'diploma.docx'

# ----------------------------------------------------------------------------
# Table data (Tajik): key -> {caption, headers, rows}
# ----------------------------------------------------------------------------
TABLES = {
    'table_intro_1': {
        'caption': 'Ҷадвали 1. Тартиббии кори курсӣ.',
        'headers': ['Қисм', 'Сонии саҳифа'],
        'rows': [
            ['Саҳифаи унвонӣ', '1'],
            ['Мундариҷа', '2'],
            ['Муқаддима', '3–4'],
            ['Боб 1', '5–9'],
            ['Боб 2', '10–14'],
            ['Боб 3', '15–19'],
            ['Хулоса', '20–21'],
            ['Рӯйхати адабиёт', '22–24'],
            ['Умумӣ', '35–39'],
        ],
    },
    'table_1_1': {
        'caption': 'Ҷадвали 1.1. Марҳилаҳои рушди васитаҳои аёни ва мултимедиа дар таълим.',
        'headers': ['Сола', 'Васита', 'Маъно'],
        'rows': [
            ['1920-ҳо', 'Грамофон, радио', 'Аудоро дар дарсхона овардан'],
            ['1950–1960-ҳо', 'Лабораторияи забони', 'Такрор кардани садо'],
            ['1970–1980-ҳо', 'Видео, телевизор', 'Тасвири дусомада'],
            ['1990-ҳо', 'Компютер, барномаҳои омўзиш', 'Интерактивӣ'],
            ['2000-ҳо', 'Интернет, мултимедиа', 'Дастрасӣ ва моҳтори'],
            ['Инрӯз', 'Таббақ, намоёнаи интерактив', 'Интерактив ва касбӣ'],
        ],
    },
    'table_1_2': {
        'caption': 'Ҷадвали 1.2. Шунардори васитаҳои аёни ва мултимедиа.',
        'headers': ['Гуруҳ', 'Намояиш', 'Мисало'],
        'rows': [
            ['Аудио', 'Садот', 'Аудиозаписи, радио, подкастҳо'],
            ['Видео', 'Тасвир ва садо', 'Фильмҳо, видеороликҳо'],
            ['Мултимедиа', 'Интерактив', 'Доскаҳои интерактивӣ, мултимедиа таббақҳо'],
            ['Диҷитолӣ', 'Онлайн', 'Вебсайтҳои омўзиш, платформаҳои LMS'],
        ],
    },
    'table_1_3': {
        'caption': 'Ҷадвали 1.3. Фоизҳои истифодаи васитаҳо.',
        'headers': ['Васита', 'Фоиз', 'Амалииёт'],
        'rows': [
            ['Аудио', '25%', 'Таълими садо'],
            ['Видео', '35%', 'Таълими визуалӣ'],
            ['Мултимедиа', '20%', 'Таълими мултимедиа'],
            ['Диҷитолӣ', '20%', 'Таълими диҷитолӣ'],
        ],
    },
    'table_2_1': {
        'caption': 'Ҷадвали 2.1. Аудиоваситаҳо ва фоидаҳои онҳо.',
        'headers': ['Васита', 'Фоида', 'Амалииёт'],
        'rows': [
            ['Аудиозаписи', 'Шунидани садои забони англисӣ', 'Таълими садо'],
            ['Радио', 'Садои забони зод', 'Таълими садо'],
            ['Подкастҳо', 'Маълумоти онлайн', 'Таълими садо'],
            ['Лабораторияи забони', 'Такрор кардани садо', 'Таълими садо'],
        ],
    },
    'table_2_2': {
        'caption': 'Ҷадвали 2.2. Видеоваситаҳо ва мултимедиа.',
        'headers': ['Васита', 'Фоида', 'Амалииёт'],
        'rows': [
            ['Фильмҳо', 'Садои забони зод', 'Таълими визуалӣ'],
            ['Видеороликҳо', 'Маълумоти воқте вуҷуд', 'Таълими визуалӣ'],
            ['Доскаи интерактивӣ', 'Амали интерактив', 'Таълими интерактив'],
            ['Мултимедиа намоёнаҳо', 'Маълумоти зиёда', 'Таълими мултимедиа'],
        ],
    },
    'table_2_3': {
        'caption': 'Ҷадвали 2.3. Платформаҳои диҷитолӣ.',
        'headers': ['Платформа', 'Фоида', 'Амалииёт'],
        'rows': [
            ['Вебсайтҳои омўзиш', 'Маълумоти онлайн', 'Таълими диҷитолӣ'],
            ['Платформаҳои LMS', 'Варзишҳои амалӣ', 'Таълими диҷитолӣ'],
            ['Таббақҳои мултимедиа', 'Интерактив', 'Таълими мултимедиа'],
        ],
    },
    'table_3_1': {
        'caption': 'Ҷадвали 3.1. Фоизҳои васитаҳои аёни ва мултимедиа.',
        'headers': ['Ҳунар', 'Фоида', 'Мисало'],
        'rows': [
            ['Сайтанд', 'Шунидани садо', 'Аудиозаписи, подкастҳо'],
            ['Гуфтан', 'Амали садо', 'Доскаи интерактивӣ'],
            ['Хондан', 'Маълумоти визуалӣ', 'Видеороликҳо, вебсайтҳо'],
            ['Невиштган', 'Амали визуалӣ', 'Платформаҳои LMS'],
        ],
    },
    'table_3_2': {
        'caption': 'Ҷадвали 3.2. Маҳдудиятҳои васитаҳои аёни ва мултимедиа.',
        'headers': ['Маҳдудият', 'Сабаб', 'Хал'],
        'rows': [
            ['Дастрасии электрония', 'Пулак электрония маҳдуд', 'Истифодаи васитаҳои офлайн'],
            ['Таълими илмӣ муаллим', 'Муаллим бо таълими илм маҳдуд', 'Таълими илмӣ барои муаллим'],
            ['Дастрасии омўзандагон', 'Омўзандагон бо таълими илм маҳдуд', 'Истифодаи таббақҳои мулта'],
        ],
    },
    'table_3_3': {
        'caption': 'Ҷадвали 3.3. Персептиваҳои таъмил.',
        'headers': ['Персептива', 'Тавсия', 'Амалииёт'],
        'rows': [
            ['Истифодаи мултимедиа', 'Васитаҳо дар дарс истифода шаванд', 'Таълими визуалӣ'],
            ['Таълими илмӣ муаллим', 'Муаллим бо таълими илм гирад', 'Таълими садо'],
            ['Варзиш омўзандагон', 'Омўзандагон бо мултимедиа варзиш карданд', 'Таълими интерактив'],
        ],
    },
}

# Section order for TOC page numbers
SECTION_ORDER = [
    'МУҚАДДИМА',
    'БОБИ 1. НАЗАРИЯВИЯТИ АСОСИИ ИСТИФОДАИ ВАСИТАҲОИ АЁНӢ ВА МУЛЬТИМЕДИЯ',
    'БОБИ 2. ИСТИФОДАИ АМАЛИИ ВАСИТАҲОИ АЁНӢ ВА МУЛЬТИМЕДИЯ',
    'БОБИ 3. ФОИДАҲО, МАҲДУДИЯТҲО ВА ПЕРСПЕКТИВҲОИ ИСТИФОДАИ ВАСИТАҲОИ АЁНӢ ВА МУЛЬТИМЕДИЯ',
    'ХУЛОСА',
    'АДАБИЁТ',
]


def add_page_field(paragraph):
    run = paragraph.add_run()
    for tag in ('begin', 'separate', 'end'):
        el = OxmlElement('w:fldChar')
        el.set(qn('w:fldCharType'), tag)
        if tag == 'separate':
            instr = OxmlElement('w:instrText')
            instr.set(qn('xml:space'), 'preserve')
            instr.text = ' PAGE '
            run._r.append(instr)
        run._r.append(el)
    docx_helpers.run_font(run)


def add_table(doc, key):
    t = TABLES[key]
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(t['caption'])
    docx_helpers.run_font(r, bold=True, size=10)
    tbl = doc.add_table(rows=1, cols=len(t['headers']))
    tbl.style = 'Table Grid'
    hdr = tbl.rows[0].cells
    for j, h in enumerate(t['headers']):
        hdr[j].text = ''
        pr = hdr[j].paragraphs[0]
        rr = pr.add_run(h)
        docx_helpers.run_font(rr, bold=True, size=9)
    for row in t['rows']:
        cells = tbl.add_row().cells
        for j, val in enumerate(row):
            cells[j].text = ''
            pr = cells[j].paragraphs[0]
            rr = pr.add_run(val)
            docx_helpers.run_font(rr, size=9)
    doc.add_paragraph()


FIG_COUNTER = [0]


def add_figure(doc, key, caption):
    stem = key[7:] if key.startswith('figure_') else key
    fig_path = ROOT / 'coursework' / 'figures' / f'{key}.png'
    if not fig_path.exists():
        fig_path = ROOT / 'coursework' / 'figures' / f'fig_{stem}.png'
    if not fig_path.exists():
        print(f'WARNING: figure not found: {key}', file=sys.stderr)
        return
    FIG_COUNTER[0] += 1
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(fig_path), width=Cm(15))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = cap.add_run(f'Рис. {FIG_COUNTER[0]}. {caption}')
    docx_helpers.run_font(run, size=9)
    doc.add_paragraph()


def md_to_docx(doc, path):
    text = Path(path).read_text(encoding='utf-8')
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        m = re.match(r'\[\[FIGURE:([\w\.]+)(?:\|(.+))?\]\]', stripped)
        if m:
            add_figure(doc, m.group(1), m.group(2) or f'Рис. {FIG_COUNTER[0]+1}. (схема)')
            i += 1
            continue

        m = re.match(r'\[\[TABLE:(\w+)\]\]', stripped)
        if m:
            add_table(doc, m.group(1))
            i += 1
            continue

        m = re.match(r'^(#{1,3})\s+(.+)$', stripped)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            style = {1: 'Heading 1', 2: 'Heading 2', 3: 'Heading 3'}[level]
            p = doc.add_paragraph(title, style=style)
            if level == 1:
                p.paragraph_format.page_break_before = True
            i += 1
            continue

        if stripped == '' or stripped == '---':
            doc.add_paragraph()
            i += 1
            continue

        p = doc.add_paragraph(style='Body Text')
        pos = 0
        for mm in re.finditer(r'\*\*(.+?)\*\*', line):
            if mm.start() > pos:
                r = p.add_run(line[pos:mm.start()])
                docx_helpers.run_font(r)
            r = p.add_run(mm.group(1))
            docx_helpers.run_font(r, bold=True)
            pos = mm.end()
        if pos < len(line):
            r = p.add_run(line[pos:])
            docx_helpers.run_font(r)
        i += 1


def build(toc_pages=None):
    doc = Document()
    docx_helpers.configure_styles(doc)
    docx_helpers.configure_theme(doc)
    docx_helpers.page_setup(doc.sections[0])

    sec = doc.sections[0]
    sec.different_first_page_header_footer = True
    fp = sec.first_page_footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_page_field(fp)
    ep = sec.footer.paragraphs[0]
    ep.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_page_field(ep)

    # ---- Title page (fields left blank as per requirement) ----
    for _ in range(6):
        doc.add_paragraph()
    p = doc.add_paragraph('', 'Title')
    p = doc.add_paragraph('', 'Subtitle')
    for _ in range(6):
        doc.add_paragraph()
    p = doc.add_paragraph('', 'Title')
    p = doc.add_paragraph('', 'Subtitle')
    for _ in range(6):
        doc.add_paragraph()
    p = doc.add_paragraph('', 'Body Text')
    p = doc.add_paragraph('', 'Body Text')

    # ---- TOC page ----
    doc.add_page_break()
    p = doc.add_paragraph('МУНДАРИҶА', 'TOC Heading')
    p = doc.add_paragraph()
    if toc_pages:
        # Static TOC with correct page numbers
        toc_items = [
            ('МУҚАДДИМА', toc_pages.get('МУҚАДДИМА', '3')),
            ('БОБИ 1. МАФҲУМҲО И АСОСИЙОНИ ҲАҶМИ ЗАРБАВӢ ВА ДАҚИҚАВИИ ДИЛ', toc_pages.get('БОБИ 1. МАФҲУМҲО И АСОСИЙОНИ ҲАҶМИ ЗАРБАВӢ ВА ДАҚИҚАВИИ ДИЛ', '6')),
            ('БОБИ 2. АҲАММИЯТИ ФИЗИОЛОГӢИ ҲАҶМИ ЗАРБАВӢ ВА ДАҚИҚАВИИ ДИЛ', toc_pages.get('БОБИ 2. АҲАММИЯТИ ФИЗИОЛОГӢИ ҲАҶМИ ЗАРБАВӢ ВА ДАҚИҚАВИИ ДИЛ', '13')),
            ('БОБИ 3. ШУНАРДОРИ ҲИСОБ КАРДАНИ ҲАҶМИ ЗАРБАВӢ ВА ДАҚИҚАВИИ ДИЛ', toc_pages.get('БОБИ 3. ШУНАРДОРИ ҲИСОБ КАРДАНИ ҲАҶМИ ЗАРБАВӢ ВА ДАҚИҚАВИИ ДИЛ', '19')),
            ('ХУЛОСА', toc_pages.get('ХУЛОСА', '27')),
            ('АДАБИЁТ', toc_pages.get('АДАБИЁТ', '30')),
        ]
        for title, page in toc_items:
            p = doc.add_paragraph()
            p.paragraph_format.tab_stops.add_tab_stop(Cm(16.4), 2, 1)
            r = p.add_run(title)
            docx_helpers.run_font(r)
            r = p.add_run('\t' + page)
            docx_helpers.run_font(r)
    else:
        docx_helpers.add_field(p, r'TOC \o "1-2" \h \z \u', 'Мундариҷа навсозӣ мешавад.')

    # ---- Chapters ----
    for chapter in ['00_intro.md', '01_chapter.md', '02_chapter.md', '03_chapter.md', '04_conclusion.md']:
        md_to_docx(doc, CONTENT / chapter)

    # ---- References ----
    doc.add_page_break()
    p = doc.add_paragraph('АДАБИЁТ', 'Heading 1')
    refs = json.loads((CONTENT / 'references.json').read_text(encoding='utf-8'))
    for ref in refs:
        p = doc.add_paragraph(style='Reference Entry')
        r = p.add_run(f"[{ref['id']}] ")
        docx_helpers.run_font(r)
        r = p.add_run(ref['text'])
        docx_helpers.run_font(r)

    doc.save(OUT)
    print('saved', OUT)


if __name__ == '__main__':
    toc_pages = None
    if '--toc-pages' in sys.argv:
        idx = sys.argv.index('--toc-pages')
        toc_pages = json.loads(sys.argv[idx + 1])
    build(toc_pages)
