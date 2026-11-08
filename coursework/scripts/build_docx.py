#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_docx.py — Табдили файли Markdown ба кори курсӣ дар шакли .docx
бо риояи талаботи стандарти донишгоҳ:

  * A4 (210×297 мм)
  * Times New Roman 14 пт, байни сатрҳо 1,5
  * маржа: чап 3 см, рост 1,5 см, боло 2 см, поён 2 см
  * саршавии параграф 1,25 см, матн аз ду тарафа ҳамвор
  * унвони бандҳо: ғафс, дар марказ; зербандҳо: ғафс, аз чап
  * ҷадвалҳо: 12 пт, байни сатрҳо 1,0, стили «Table Grid», унвон дар боло
  * рақами саҳифа дар поён, марказ; вараки унвон рақам надорад
  * вараки унвон ва мундариҷаи худкор (field TOC)

Истифода:
    python coursework/scripts/build_docx.py coursework/01_Elastografiya.md
    python coursework/scripts/build_docx.py coursework/01_Elastografiya.md -o out/…
    python coursework/scripts/build_docx.py coursework/01_Elastografiya.md --no-title

Синтаксиси Markdown, ки дастгирӣ мешавад:
    # Унвони банд          -> сарлавҳаи 1 (ғафс, марказ, ҳарфҳои калон)
    ## Зербанд            -> сарлавҳаи 2
    ### Зербанди хурд      -> сарлавҳаи 3
    ¶ матн                 -> абзаци оддӣ
    - / * / 1.  …          -> рӯйхат
    | a | b |              -> ҷадвал (сатри аввал — сарлавҳа)
    Ҷадвали 1.1 — Ном     -> унвони ҷадвал (сатри ҷудогона пеш аз ҷадвал)
    > иқтибос              -> абзаци фосиладор
    **ғафс**, *моил*       -> таъкид
    ---                    -> хати ҷудокунанда (нест мешавад)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    from docx import Document
    from docx.enum.section import WD_SECTION
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor
except ImportError:  # pragma: no cover
    sys.exit(
        "Хато: python-docx насб нашудааст.\n"
        "Иҷро кунед:  python3 -m venv .venv && .venv/bin/pip install python-docx"
    )


# --------------------------------------------------------------------------
# МАЪЛУМОТИ МУАССИСА  —  ин ҷоро як бор тағйир диҳед, ҳамаи корҳо якхел мешаванд
# --------------------------------------------------------------------------
INSTITUTION = {
    "ministry": "ВАЗОРАТИ МАОРИФ ВА ИЛМИ ҶУМҲУРИИ ТОҶИКИСТОН",
    "name": "ДОНИШКАДАИ ИЛМҲОИ ДАҚИҚ ВА ТЕХНОЛОГИЯИ ТОҶИКИСТОН ДАР ШАҲРИ ХУҶАНД",
    "faculty": "Факултети фанҳои дақиқ ва технологияи инноватсионӣ",
    "chair": "Кафедраи фанҳои дақиқ ва тиббӣ",
    "work_type": "КОРИ КУРСӢ",
    "speciality": "______",
    "course": "______",
    "group": "______",
    "student": "______",
    "teacher": "______",
    "city": "Хуҷанд",
    "year": "______",
    "placeholders": "______",
}

# Барои ҳисоби тахминӣ: калимаи тоҷикӣ ба ҳисоби миёна ~5,3 аломат,
# саҳифаи A4 (TNR 14, 1,5) ~1900 аломат мегирад.
CHARS_PER_WORD = 5.3
CHARS_PER_PAGE = 1900

FONT = "Times New Roman"
BODY_SIZE = Pt(14)
TABLE_SIZE = Pt(12)
INDENT = Cm(1.25)


# --------------------------------------------------------------------------
# Ярддамонҳои XML
# --------------------------------------------------------------------------
def set_run_font(run, size: Pt | None = None, bold: bool | None = None, italic: bool | None = None):
    """Шрифти Times New Roman-ро барои ҳар се алифбо (лот., кирил., шарқӣ) мегузорад."""
    run.font.name = FONT
    if size is not None:
        run.font.size = size
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), FONT)
    # андозаи шрифт барои матни комплексӣ (cs)
    sz = rpr.find(qn("w:szCs"))
    if size is not None:
        if sz is None:
            sz = OxmlElement("w:szCs")
            rpr.append(sz)
        sz.set(qn("w:val"), str(int(size.pt * 2)))


def add_field(paragraph, instr: str, placeholder: str = ""):
    """Майдони Word (барои рақами саҳифа ва мундариҷа).

    Ҳар қисми майдон (begin / instrText / separate / натиҷа / end)
    дар run-и АЛОҲИДА гузошта мешавад — талаботи OOXML.
    """
    def _mkrun():
        r = paragraph.add_run()
        set_run_font(r, BODY_SIZE)
        return r

    r1 = _mkrun()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    fld_begin.set(qn("w:dirty"), "true")
    r1._r.append(fld_begin)

    r2 = _mkrun()
    instr_el = OxmlElement("w:instrText")
    instr_el.set(qn("xml:space"), "preserve")
    instr_el.text = instr
    r2._r.append(instr_el)

    r3 = _mkrun()
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    r3._r.append(fld_sep)

    if placeholder:
        r4 = _mkrun()
        text_el = OxmlElement("w:t")
        text_el.set(qn("xml:space"), "preserve")
        text_el.text = placeholder
        r4._r.append(text_el)

    r5 = _mkrun()
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    r5._r.append(fld_end)
    return r1


def force_update_fields(doc):
    """Word ҳангоми кушодан майдонҳоро (мундариҷа) нав мекунад.

    Муҳим: тибқи схемаи OOXML унсури <w:updateFields> бояд ПЕШ аз
    <w:compat>, <w:rsids>, <w:themeFontLang> ва <w:clrSchemeMapping>
    бошад. Агар онро дар охири settings.xml гузорем, Word файлро
    «вайрон» ҳисобида кушода наметавонад.
    """
    settings = doc.settings.element
    for old in settings.findall(qn("w:updateFields")):
        settings.remove(old)

    upd = OxmlElement("w:updateFields")
    upd.set(qn("w:val"), "true")

    # Ҷои дуруст: баъд аз w:proofState/w:defaultTabStop, пеш аз w:compat
    anchor = None
    for tag in ("w:compat", "w:rsids", "w:themeFontLang", "w:clrSchemeMapping",
                "w:mathPr", "w:zoom", "w:proofState"):
        el = settings.find(qn(tag))
        if el is not None:
            anchor = el
            break

    if anchor is not None:
        anchor.addprevious(upd)
    else:
        settings.insert(0, upd)
    return upd


# --------------------------------------------------------------------------
# Услубҳо
# --------------------------------------------------------------------------
def configure_styles(doc):
    styles = doc.styles

    normal = styles["Normal"]
    normal.font.name = FONT
    normal.font.size = BODY_SIZE
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    normal.element.rPr.rFonts.set(qn("w:cs"), FONT)
    pf = normal.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.first_line_indent = INDENT

    # Сарлавҳаҳо: сиёҳ, ғафс, Times New Roman (на ранги кабуд)
    h1 = styles["Heading 1"]
    h1.font.name = FONT
    h1.font.size = BODY_SIZE
    h1.font.bold = True
    h1.font.color.rgb = RGBColor(0, 0, 0)
    h1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    h1.paragraph_format.first_line_indent = Cm(0)
    h1.paragraph_format.space_before = Pt(12)
    h1.paragraph_format.space_after = Pt(6)
    h1.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    h1.paragraph_format.keep_with_next = True

    h2 = styles["Heading 2"]
    h2.font.name = FONT
    h2.font.size = BODY_SIZE
    h2.font.bold = True
    h2.font.color.rgb = RGBColor(0, 0, 0)
    h2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    h2.paragraph_format.first_line_indent = Cm(0)
    h2.paragraph_format.space_before = Pt(10)
    h2.paragraph_format.space_after = Pt(4)
    h2.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    h2.paragraph_format.keep_with_next = True

    h3 = styles["Heading 3"]
    h3.font.name = FONT
    h3.font.size = BODY_SIZE
    h3.font.bold = True
    h3.font.italic = False
    h3.font.color.rgb = RGBColor(0, 0, 0)
    h3.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    h3.paragraph_format.first_line_indent = Cm(0)
    h3.paragraph_format.space_before = Pt(8)
    h3.paragraph_format.space_after = Pt(4)
    h3.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    h3.paragraph_format.keep_with_next = True

    # Унвони ҷадвал
    if "Table Caption" not in [s.name for s in styles]:
        cap = styles.add_style("Table Caption", 1)  # 1 = PARAGRAPH
        cap.base_style = styles["Normal"]
    cap = styles["Table Caption"]
    cap.font.name = FONT
    cap.font.size = TABLE_SIZE
    cap.font.bold = False
    cap.font.italic = False
    cap.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    cap.paragraph_format.first_line_indent = Cm(0)
    cap.paragraph_format.space_before = Pt(10)
    cap.paragraph_format.space_after = Pt(2)
    cap.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    cap.paragraph_format.keep_with_next = True


def configure_section(doc):
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(3)
    section.right_margin = Cm(1.5)
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.header_distance = Cm(1.25)
    section.footer_distance = Cm(1.0)
    section.different_first_page_header_footer = True  # вараки унвон бе рақам

    # Рақами саҳифа дар поён, марказ
    footer = section.footer
    p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    add_field(p, "PAGE", "2")
    for run in p.runs:
        set_run_font(run, BODY_SIZE)

    # Саҳифаи якум (вараки унвон) — поёни холӣ
    first_footer = section.first_page_footer
    fp = first_footer.paragraphs[0] if first_footer.paragraphs else first_footer.add_paragraph()
    fp.text = ""


# --------------------------------------------------------------------------
# Вараки унвон
# --------------------------------------------------------------------------
def _line(doc, text="", size=BODY_SIZE, bold=False, before=0, after=0, align=WD_ALIGN_PARAGRAPH.CENTER):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    run = p.add_run(text)
    set_run_font(run, size, bold=bold)
    return p


def add_title_page(doc, topic: str):
    i = INSTITUTION
    _line(doc, i["ministry"], Pt(12), bold=True)
    _line(doc, i["name"], Pt(12), bold=True, before=6)
    _line(doc, i["faculty"], Pt(12), before=6)
    _line(doc, i["chair"], Pt(12), before=2)

    _line(doc, "", before=90)
    _line(doc, i["work_type"], Pt(20), bold=True, before=12, after=12)
    _line(doc, "аз фанни «______»", Pt(14), after=6)
    _line(doc, "Мавзӯъ:", Pt(14), after=6)
    _line(doc, topic.upper() if topic else i["placeholders"], Pt(16), bold=True, after=6)

    _line(doc, "", before=110)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    lines = [
        f"Иҷрокунанда: донишҷӯи курси {i['course']}",
        f"гурӯҳи {i['group']}",
        i["student"],
        "______________________ (имзо)",
        "",
        f"Роҳбар: {i['teacher']}",
        "______________________ (имзо)",
    ]
    for text in lines:
        run = p.add_run(text + "\n")
        set_run_font(run, BODY_SIZE)

    _line(doc, "", before=90)
    _line(doc, f"{i['city']} — {i['year']}", BODY_SIZE, bold=True)

    # гузариш ба саҳифаи нав
    br = doc.add_paragraph()
    br.paragraph_format.first_line_indent = Cm(0)
    br.add_run().add_break(WD_BREAK.PAGE)


def add_toc(doc):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_after = Pt(12)
    run = p.add_run("МУНДАРИҶА")
    set_run_font(run, BODY_SIZE, bold=True)

    toc_p = doc.add_paragraph()
    toc_p.paragraph_format.first_line_indent = Cm(0)
    toc_p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    add_field(toc_p, 'TOC \\o "1-3" \\h \\z \\u',
              "Барои сохтани мундариҷа: клик дар ин ҷо → F9 → Update entire table")


# --------------------------------------------------------------------------
# Парсер Markdown
# --------------------------------------------------------------------------
INLINE_RE = re.compile(r"(\*\*.+?\*\*|\*[^*\n]+?\*|__.+?__|`[^`]+?`)")


def add_inline(paragraph, text: str, size=BODY_SIZE):
    """**ғафс**, *моил*, `код`-ро коркард мекунад."""
    for chunk in INLINE_RE.split(text):
        if not chunk:
            continue
        if chunk.startswith("**") and chunk.endswith("**") and len(chunk) > 4:
            run = paragraph.add_run(chunk[2:-2])
            set_run_font(run, size, bold=True)
        elif chunk.startswith("__") and chunk.endswith("__") and len(chunk) > 4:
            run = paragraph.add_run(chunk[2:-2])
            set_run_font(run, size, bold=True)
        elif chunk.startswith("*") and chunk.endswith("*") and len(chunk) > 2:
            run = paragraph.add_run(chunk[1:-1])
            set_run_font(run, size, italic=True)
        elif chunk.startswith("`") and chunk.endswith("`") and len(chunk) > 2:
            run = paragraph.add_run(chunk[1:-1])
            set_run_font(run, size)
        else:
            run = paragraph.add_run(chunk)
            set_run_font(run, size)


def parse_table(lines, start):
    rows = []
    i = start
    while i < len(lines) and lines[i].strip().startswith("|"):
        raw = lines[i].strip().strip("|")
        cells = [c.strip() for c in raw.split("|")]
        if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            rows.append(cells)
        i += 1
    return rows, i


def add_table(doc, rows, caption: str | None = None):
    if not rows:
        return
    ncols = max(len(r) for r in rows)
    if caption:
        p = doc.add_paragraph(style="Table Caption")
        add_inline(p, caption, size=TABLE_SIZE)

    table = doc.add_table(rows=0, cols=ncols)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True

    for r_idx, row in enumerate(rows):
        cells = table.add_row().cells
        for c_idx in range(ncols):
            text = row[c_idx] if c_idx < len(row) else ""
            cell = cells[c_idx]
            cell.text = ""
            para = cell.paragraphs[0]
            para.paragraph_format.first_line_indent = Cm(0)
            para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            para.paragraph_format.space_before = Pt(2)
            para.paragraph_format.space_after = Pt(2)
            para.alignment = (
                WD_ALIGN_PARAGRAPH.CENTER if r_idx == 0 else WD_ALIGN_PARAGRAPH.LEFT
            )
            add_inline(para, text, size=TABLE_SIZE)
            if r_idx == 0:
                for run in para.runs:
                    run.bold = True

    # фосилаи баъд аз ҷадвал
    sp = doc.add_paragraph()
    sp.paragraph_format.first_line_indent = Cm(0)
    sp.paragraph_format.space_after = Pt(0)
    sp.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    r = sp.add_run("")
    set_run_font(r, Pt(6))


CAPTION_RE = re.compile(
    r"^(Ҷадвали|Шакли|Диаграмма)\s+([А-ЯЁA-Z]|\d+)\.\d+", re.IGNORECASE
)


def convert(md_path: Path, out_path: Path, topic: str | None, with_title: bool):
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    doc = Document()
    configure_styles(doc)
    configure_section(doc)
    force_update_fields(doc)

    if with_title:
        add_title_page(doc, topic or "")
        add_toc(doc)
        head = doc.add_paragraph()
        head.paragraph_format.first_line_indent = Cm(0)
        head.add_run().add_break(WD_BREAK.PAGE)

    i = 0
    pending_caption: str | None = None
    in_code = False
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # блоки код — ҳамчун матни оддӣ
        if stripped.startswith("```"):
            in_code = not in_code
            i += 1
            continue

        if in_code:
            p = doc.add_paragraph()
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            add_inline(p, stripped, size=Pt(12))
            i += 1
            continue

        if not stripped or stripped in {"---", "***", "___"}:
            i += 1
            continue

        # сарлавҳаҳо
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            level = min(len(m.group(1)), 3)
            title = m.group(2).strip()
            if level == 1:
                p = doc.add_paragraph(style="Heading 1")
                p.paragraph_format.page_break_before = False
                add_inline(p, title.upper(), size=BODY_SIZE)
            else:
                p = doc.add_paragraph(style=f"Heading {level}")
                add_inline(p, title, size=BODY_SIZE)
            i += 1
            continue

        # ҷадвал
        if stripped.startswith("|"):
            rows, i = parse_table(lines, i)
            add_table(doc, rows, caption=pending_caption)
            pending_caption = None
            continue

        # рӯйхат
        m = re.match(r"^([-*•]|\d+[.)])\s+(.*)$", stripped)
        if m:
            marker = m.group(1)
            style = "List Bullet" if marker in {"-", "*", "•"} else "List Number"
            while True:
                mm = re.match(r"^([-*•]|\d+[.)])\s+(.*)$", lines[i].strip()) if i < len(lines) else None
                if not mm:
                    break
                p = doc.add_paragraph(style=style)
                p.paragraph_format.first_line_indent = Cm(0)
                p.paragraph_format.left_indent = Cm(1.0)
                p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                add_inline(p, mm.group(2), size=BODY_SIZE)
                i += 1
            continue

        # иқтибос / эзоҳ
        if stripped.startswith(">"):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(1.0)
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            add_inline(p, stripped.lstrip("> ").strip(), size=Pt(12))
            i += 1
            continue

        # унвони ҷадвал (ба ҷадвали навбатӣ мечаспад)
        if CAPTION_RE.match(stripped):
            pending_caption = stripped
            i += 1
            continue

        # абзаци оддӣ
        para_lines = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if (not nxt or nxt.startswith(("#", "|", ">", "```"))
                    or re.match(r"^([-*•]|\d+[.)])\s+", nxt)
                    or CAPTION_RE.match(nxt)
                    or nxt in {"---", "***", "___"}):
                break
            para_lines.append(nxt)
            i += 1
        p = doc.add_paragraph()
        add_inline(p, " ".join(para_lines), size=BODY_SIZE)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)
    return out_path


def extract_topic(md_text: str, base: Path | None = None) -> str | None:
    """Мавзӯъро меҷӯяд: topic.txt → сатри «Мавзӯъ: ...» → аввалин сарлавҳаи #."""
    if base is not None:
        folder = base.parent if base.is_file() else base
        topic_file = folder / "topic.txt"
        if topic_file.exists():
            text = topic_file.read_text(encoding="utf-8").strip()
            if text:
                return text.splitlines()[0].strip()

    for line in md_text.splitlines():
        m = re.match(r"^\s*Мавзӯъ\s*:\s*(.+)$", line, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    for line in md_text.splitlines():
        m = re.match(r"^#\s+(.+)$", line.strip())
        if m:
            return m.group(1).strip()
    return None


def collect_sources(paths: list[Path]) -> tuple[list[Path], Path]:
    """Як файл, якчанд файл ё ҷузвдонро ба рӯйхати тартибдодашуда табдил медиҳад."""
    files: list[Path] = []
    base: Path | None = None
    for p in paths:
        if p.is_dir():
            base = p
            files.extend(sorted([f for f in p.iterdir() if f.suffix == ".md"]))
        elif p.is_file():
            if base is None:
                base = p
            files.append(p)
        else:
            sys.exit(f"Ёфт нашуд: {p}")
    if not files:
        sys.exit("Ягон файли .md ёфт нашуд.")
    return files, base


def main():
    ap = argparse.ArgumentParser(description="Markdown → .docx барои кори курсӣ")
    ap.add_argument(
        "source", type=Path, nargs="+",
        help="файли .md ё ҷузвдони дорои 00_*.md, 10_*.md, …",
    )
    ap.add_argument("-o", "--output", type=Path, default=None, help="файли .docx")
    ap.add_argument("--topic", default=None, help="мавзӯъ барои вараки унвон")
    ap.add_argument("--no-title", action="store_true", help="бе вараки унвон ва мундариҷа")
    args = ap.parse_args()

    files, base = collect_sources(args.source)

    # Ҳамаи файлҳоро ба як файли муваққатӣ ҷамъ мекунем
    merged = "\n\n".join(f.read_text(encoding="utf-8") for f in files)
    tmp = Path(".build_merged.md")
    tmp.write_text(merged, encoding="utf-8")

    if args.output:
        out = args.output
    elif base is not None and base.is_dir():
        out = base.parent / (base.name + ".docx")
    else:
        out = base.with_suffix(".docx") if base else Path("coursework.docx")

    topic = args.topic or extract_topic(merged, base)
    path = convert(tmp, out, topic, with_title=not args.no_title)
    tmp.unlink(missing_ok=True)

    words = len(merged.split())
    print(f"✅ Тайёр: {path}")
    print(f"   Қисмҳо: {len(files)} файл ({', '.join(f.name for f in files)})")
    print(f"   Мавзӯъ: {topic or '—'}")
    pages = words * CHARS_PER_WORD / CHARS_PER_PAGE
    print(f"   Калимаҳо: {words} (~{round(pages, 1)} саҳифа)")


if __name__ == "__main__":
    main()
