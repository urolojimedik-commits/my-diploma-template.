"""DOCX: Pandoc + эталонный документ (reference.docx) по требованиям ГОСТ.

Схема:

1. ``python-docx`` собирает ``reference.docx`` с нужными стилями (Times New
   Roman 14 пт, полуторный интервал, поля 30/15/20/20 мм, отступ первой
   строки 1,25 см, стиль «Caption» для подписей, номер страницы в колонтитуле);
2. Pandoc конвертирует markdown в DOCX с этим эталоном и автоматическим
   содержанием (``--toc``);
3. постобработка ``python-docx``: удаляет дублирующий заголовок-название,
   переоформляет титульный лист и подписи рисунков/таблиц, вписывает номер
   страницы в нижний колонтитул.
"""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document as DocxDocument
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from .pandoc_utils import convert_file

# Параметры оформления (ГОСТ Р 7.0.32-2017 для студенческих работ)
BODY_FONT = "Times New Roman"
BODY_SIZE = Pt(14)
LINE_SPACING = 1.5


# --------------------------------------------------------------------------- #
# Вспомогательные функции OOXML
# --------------------------------------------------------------------------- #


def _ppr(obj):
    """Возвращает <w:pPr> для абзаца или для стиля абзаца."""
    if hasattr(obj, "_p"):  # Paragraph
        return obj._p.get_or_add_pPr()
    return obj.element.get_or_add_pPr()  # ParagraphStyle / ParagraphFormat


def _set_spacing(paragraph, line_spacing: float = LINE_SPACING, before: float = 0, after: float = 0):
    pPr = _ppr(paragraph)
    spacing = pPr.find(qn("w:spacing"))
    if spacing is None:
        spacing = OxmlElement("w:spacing")
        pPr.append(spacing)
    spacing.set(qn("w:line"), str(int(line_spacing * 240)))
    spacing.set(qn("w:lineRule"), "auto")
    spacing.set(qn("w:before"), str(int(before * 20)))
    spacing.set(qn("w:after"), str(int(after * 20)))


def _set_indent(paragraph, first_line_cm: float = 1.25, left_cm: float = 0.0):
    pPr = _ppr(paragraph)
    ind = pPr.find(qn("w:ind"))
    if ind is None:
        ind = OxmlElement("w:ind")
        pPr.append(ind)
    ind.set(qn("w:firstLine"), str(int(first_line_cm * 567)))
    ind.set(qn("w:left"), str(int(left_cm * 567)))


def _rpr(style_or_run, font: str, size: Pt, bold: bool = False, italic: bool = False,
         color: tuple | None = None):
    run = style_or_run if hasattr(style_or_run, "font") else None
    if run is None:  # передан style → работаем с его rPr
        rPr = style_or_run.element.get_or_add_rPr()
        _apply_rpr(rPr, font, size, bold, italic, color)
        return
    run.font.name = font
    run.font.size = size
    run.font.bold = bold
    run.font.italic = italic
    if color:
        run.font.color.rgb = RGBColor(*color)


def _apply_rpr(rPr, font: str, size: Pt, bold: bool = False, italic: bool = False,
               color: tuple | None = None):
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), font)
    rFonts.set(qn("w:hAnsi"), font)
    rFonts.set(qn("w:cs"), font)
    for tag, value in (("w:b", bold), ("w:i", italic)):
        el = rPr.find(qn(tag))
        if value and el is None:
            rPr.append(OxmlElement(tag))
        elif not value and el is not None:
            rPr.remove(el)
    sz = rPr.find(qn("w:sz"))
    if sz is None:
        sz = OxmlElement("w:sz")
        rPr.append(sz)
    sz.set(qn("w:val"), str(int(size.pt * 2)))
    if color:
        c = rPr.find(qn("w:color"))
        if c is None:
            c = OxmlElement("w:color")
            rPr.append(c)
        c.set(qn("w:val"), "%02X%02X%02X" % color)


def add_page_field(paragraph, instr: str = "PAGE"):
    """Вставляет поле Word (PAGE / NUMPAGES) в абзац."""
    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr_el = OxmlElement("w:instrText")
    instr_el.set(qn("xml:space"), "preserve")
    instr_el.text = f" {instr} "
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_begin)
    run._r.append(instr_el)
    run._r.append(fld_end)
    return run


def add_page_break(paragraph):
    run = paragraph.add_run()
    br = OxmlElement("w:br")
    br.set(qn("w:type"), "page")
    run._r.append(br)


# --------------------------------------------------------------------------- #
# Эталонный документ
# --------------------------------------------------------------------------- #


def make_reference_docx(path: Path, font_size: int = 14, line_spacing: float = 1.5) -> Path:
    """Создаёт reference.docx со стилями, которые Pandoc применит к выводу."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = DocxDocument()

    # --- поля страницы ---
    section = doc.sections[0]
    section.left_margin = Cm(3.0)
    section.right_margin = Cm(1.5)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)

    # --- стиль Normal ---
    normal = doc.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = Pt(font_size)
    _apply_rpr(normal.element.get_or_add_rPr(), BODY_FONT, Pt(font_size))
    pf = normal.paragraph_format
    pf.line_spacing = line_spacing
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)

    # --- заголовки ---
    heads = {
        "Heading 1": (font_size + 2, True, WD_ALIGN_PARAGRAPH.CENTER),
        "Heading 2": (font_size, True, WD_ALIGN_PARAGRAPH.LEFT),
        "Heading 3": (font_size, True, WD_ALIGN_PARAGRAPH.LEFT),
        "Title": (font_size + 4, True, WD_ALIGN_PARAGRAPH.CENTER),
    }
    for name, (size, bold, align) in heads.items():
        try:
            st = doc.styles[name]
        except KeyError:
            continue
        st.font.name = BODY_FONT
        st.font.size = Pt(size)
        st.font.bold = bold
        _apply_rpr(st.element.get_or_add_rPr(), BODY_FONT, Pt(size), bold=bold,
                   color=(0x10, 0x23, 0x3A))
        st.paragraph_format.alignment = align
        st.paragraph_format.space_before = Pt(12)
        st.paragraph_format.space_after = Pt(6)
        st.paragraph_format.first_line_indent = Cm(0)
        st.paragraph_format.line_spacing = line_spacing

    # --- подписи (Caption) ---
    try:
        caption = doc.styles.add_style("Caption", 1)  # 1 == WD_STYLE_TYPE.PARAGRAPH
    except Exception:
        caption = doc.styles["Caption"]
    caption.font.name = BODY_FONT
    caption.font.size = Pt(font_size - 2)
    caption.font.italic = False
    _apply_rpr(caption.element.get_or_add_rPr(), BODY_FONT, Pt(font_size - 2))
    caption.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption.paragraph_format.space_after = Pt(10)
    caption.paragraph_format.first_line_indent = Cm(0)
    caption.paragraph_format.line_spacing = 1.0

    # --- номер страницы в нижнем колонтитуле ---
    footer = section.footer
    fp = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if not fp.runs:
        _rpr(fp.add_run(""), BODY_FONT, Pt(11))
    add_page_field(fp, "PAGE")

    # --- хотя бы один абзац, чтобы стили записались ---
    p = doc.add_paragraph("Эталонный документ")
    p.style = doc.styles["Normal"]
    doc.save(str(path))
    return path


# --------------------------------------------------------------------------- #
# Постобработка
# --------------------------------------------------------------------------- #

CAPTION_RE = re.compile(r"^(Рисунок|Таблица|Figure|Table)\b")


def postprocess_docx(path: Path, title_block: list[tuple[str, str]] | None = None) -> Path:
    """Приводит DOCX к требованиям: подписи, титул, интервалы, разрыв страниц."""
    doc = DocxDocument(str(path))

    # 1. Удаляем дублирующий заголовок, вставленный Pandoc из метаданных
    if doc.paragraphs:
        first = doc.paragraphs[0]
        if first.style and first.style.name in {"Title", "Заголовок"} and not CAPTION_RE.match(first.text):
            el = first._p
            el.getparent().remove(el)

    # 2. Титульный лист: центрируем блок до первого Heading 1
    in_title = True
    for p in doc.paragraphs:
        style_name = p.style.name if p.style else ""
        if style_name.startswith("Heading"):
            in_title = False
        if in_title and p.text.strip():
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.line_spacing = 1.0
            for run in p.runs:
                run.font.size = Pt(14)
                run.font.name = BODY_FONT
        elif not in_title:
            break

    # 3. Подписи рисунков и таблиц
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue
        if CAPTION_RE.match(text):
            try:
                p.style = doc.styles["Caption"]
            except KeyError:
                pass
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.space_after = Pt(10)
            p.paragraph_format.line_spacing = 1.0
            for run in p.runs:
                run.font.size = Pt(12)
                run.font.name = BODY_FONT

    # 4. Основной текст: шрифт, интервал, отступ
    for p in doc.paragraphs:
        style_name = p.style.name if p.style else ""
        if style_name in {"Normal", "Body Text", "First Paragraph", "Compact"} or style_name == "Normal":
            p.paragraph_format.line_spacing = LINE_SPACING
            if p.text.strip() and not CAPTION_RE.match(p.text.strip()):
                _set_indent(p.paragraph_format, first_line_cm=1.25)
            for run in p.runs:
                run.font.name = BODY_FONT
                if run.font.size is None:
                    run.font.size = BODY_SIZE

    # 5. Таблицы: шрифт и границы уже заданы Pandoc — выравниваем ширину
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.line_spacing = 1.0
                    p.paragraph_format.first_line_indent = Cm(0)
                    for run in p.runs:
                        run.font.size = Pt(11)
                        run.font.name = BODY_FONT

    # 6. Новая страница перед каждой главой и перед списком литературы
    for i, p in enumerate(doc.paragraphs):
        text = p.text.strip()
        style_name = p.style.name if p.style else ""
        is_chapter = style_name.startswith("Heading 1") and (
            text.lower().startswith("глава") or text.lower().startswith("список")
            or text.lower().startswith("приложение") or text.lower() == "введение"
            or text.lower() == "заключение"
        )
        if is_chapter and i > 0:
            add_page_break(p.insert_paragraph_before(""))

    doc.save(str(path))
    return path


# --------------------------------------------------------------------------- #
# Сборка
# --------------------------------------------------------------------------- #


def render_docx(
    markdown: str,
    output: Path,
    base_dir: Path,
    reference_docx: Path | None = None,
    toc: bool = True,
    font_size: int = 14,
    line_spacing: float = 1.5,
) -> Path:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if reference_docx is None or not Path(reference_docx).exists():
        reference_docx = output.parent / "_reference.docx"
        make_reference_docx(reference_docx, font_size=font_size, line_spacing=line_spacing)
    args = [
        "--reference-doc",
        str(reference_docx),
        "--resource-path",
        str(base_dir),
        *(["--toc", "--toc-depth=2"] if toc else []),
        "--standalone",
    ]
    tmp_md = Path(output).with_suffix(".docx.md")
    tmp_md.write_text(markdown, encoding="utf-8")
    convert_file(tmp_md, "docx", output, args, cwd=base_dir)
    tmp_md.unlink(missing_ok=True)
    postprocess_docx(output)
    return output


def _write_temp(markdown: str, output: Path) -> Path:
    tmp = Path(output).with_suffix(".md")
    tmp.write_text(markdown, encoding="utf-8")
    return tmp
