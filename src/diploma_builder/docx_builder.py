"""
docx_builder.py — сборка DOCX по ГОСТ.

Требования:
- Times New Roman 14pt, интервал 1.5
- Поля: 30-15-20-20 мм
- Красная строка 1.25 см
- Подписи: "Рисунок N — Название" (центр), "Таблица N — Название" (слева)
- Нумерация сквозная
- Содержание, список литературы
"""

from __future__ import annotations

import pathlib
import re
from typing import List, Optional

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.section import WD_SECTION
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Cm, RGBColor, Emu

from .config import ProjectConfig, ChapterPlan, SourceRecord
from .bibliography import BibliographyManager


# Утилиты для docx

def set_margins(section, left_mm=30, right_mm=15, top_mm=20, bottom_mm=20):
    section.left_margin = Cm(left_mm / 10)
    section.right_margin = Cm(right_mm / 10)
    section.top_margin = Cm(top_mm / 10)
    section.bottom_margin = Cm(bottom_mm / 10)


def set_paragraph_format(paragraph, font_name="Times New Roman", font_size=14, bold=False, italic=False, alignment=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=6, line_spacing=1.5, first_line_indent_cm=1.25):
    # интервал
    paragraph.paragraph_format.line_spacing = line_spacing
    paragraph.paragraph_format.space_after = Pt(space_after)
    paragraph.paragraph_format.space_before = Pt(0)
    if first_line_indent_cm:
        paragraph.paragraph_format.first_line_indent = Cm(first_line_indent_cm)
    # выравнивание
    paragraph.alignment = alignment
    # шрифт для всех ранов
    for run in paragraph.runs:
        run.font.name = font_name
        run.font.size = Pt(font_size)
        run.font.bold = bold
        run.font.italic = italic
        # для корректного отображения Times New Roman в LibreOffice
        r = run._element
        rPr = r.get_or_add_rPr()
        rFonts = OxmlElement("w:rFonts")
        rFonts.set(qn("w:ascii"), font_name)
        rFonts.set(qn("w:hAnsi"), font_name)
        rFonts.set(qn("w:cs"), font_name)
        rPr.append(rFonts)


def add_heading_styled(doc: Document, text: str, level: int = 1, centered: bool = True, font_size: int = 16):
    """Заголовок главы."""
    p = doc.add_heading(level=level)
    run = p.add_run(text)
    run.bold = True
    run.font.name = "Times New Roman"
    run.font.size = Pt(font_size)
    run.font.color.rgb = RGBColor(0x00, 0x00, 0x00)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if centered else WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.first_line_indent = Cm(0)
    # rFonts
    r = run._element
    rPr = r.get_or_add_rPr()
    rFonts = OxmlElement("w:rFonts")
    rFonts.set(qn("w:ascii"), "Times New Roman")
    rFonts.set(qn("w:hAnsi"), "Times New Roman")
    rPr.append(rFonts)
    return p


def add_paragraph_styled(doc: Document, text: str, bold=False, italic=False, alignment=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent_cm=1.25, font_size=14, space_after=6) -> any:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(font_size)
    run.bold = bold
    run.italic = italic
    # цитаты курсивом
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.first_line_indent = Cm(first_line_indent_cm) if first_line_indent_cm else None
    p.alignment = alignment
    # rFonts
    r = run._element
    rPr = r.get_or_add_rPr()
    rFonts = OxmlElement("w:rFonts")
    rFonts.set(qn("w:ascii"), "Times New Roman")
    rFonts.set(qn("w:hAnsi"), "Times New Roman")
    rFonts.set(qn("w:cs"), "Times New Roman")
    rPr.append(rFonts)
    return p


def add_table_gost(doc: Document, headers: List[str], rows: List[List[str]], caption: str, table_number: int, source_note: str = ""):
    # подпись таблицы (сверху, слева)
    cap_text = f"Таблица {table_number} — {caption}"
    p_cap = doc.add_paragraph()
    run = p_cap.add_run(cap_text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    run.italic = True
    p_cap.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_cap.paragraph_format.space_after = Pt(4)
    p_cap.paragraph_format.first_line_indent = Cm(0)
    p_cap.paragraph_format.line_spacing = 1.0

    # таблица
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Light Grid Accent 1"  # ГОСТ-подобный
    table.autofit = True
    # заголовки
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h
        for paragraph in hdr_cells[i].paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                run.font.name = "Times New Roman"
                run.font.size = Pt(10)
                run.bold = True
        # заливка заголовка
        shading = OxmlElement("w:shd")
        shading.set(qn("w:val"), "clear")
        shading.set(qn("w:color"), "auto")
        shading.set(qn("w:fill"), "D9E2F3")
        hdr_cells[i]._tc.get_or_add_tcPr().append(shading)

    for row_data in rows:
        cells = table.add_row().cells
        for i, val in enumerate(row_data):
            cells[i].text = str(val)
            for paragraph in cells[i].paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if i > 0 else WD_ALIGN_PARAGRAPH.LEFT
                for run in paragraph.runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(10)

    # источник под таблицей
    if source_note:
        p_src = doc.add_paragraph()
        run = p_src.add_run(source_note)
        run.font.name = "Times New Roman"
        run.font.size = Pt(9)
        run.italic = True
        run.font.color.rgb = RGBColor(0x59, 0x59, 0x59)
        p_src.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_src.paragraph_format.space_before = Pt(2)
        p_src.paragraph_format.first_line_indent = Cm(0)
        p_src.paragraph_format.line_spacing = 1.0

    # отступ после
    doc.add_paragraph().paragraph_format.space_after = Pt(6)


def add_figure_gost(doc: Document, image_path: pathlib.Path, caption: str, figure_number: int, source_note: str = ""):
    # изображение по центру
    if not image_path.exists():
        p = doc.add_paragraph()
        p.add_run(f"[Рисунок {figure_number} отсутствует: {image_path.name}]").italic = True
        return

    p_img = doc.add_paragraph()
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_img.paragraph_format.first_line_indent = Cm(0)
    p_img.paragraph_format.space_after = Pt(4)
    # ширина ~ 14 см (чтобы влезала в поля)
    try:
        p_img.add_run().add_picture(str(image_path), width=Cm(14))
    except Exception as e:
        p_img.add_run(f"[Ошибка вставки рисунка: {e}]")

    # подпись (снизу, по центру)
    cap_text = f"Рисунок {figure_number} — {caption}"
    p_cap = doc.add_paragraph()
    run = p_cap.add_run(cap_text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    run.italic = False
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_after = Pt(2)
    p_cap.paragraph_format.first_line_indent = Cm(0)
    p_cap.paragraph_format.line_spacing = 1.0

    if source_note:
        p_src = doc.add_paragraph()
        run = p_src.add_run(source_note)
        run.font.name = "Times New Roman"
        run.font.size = Pt(9)
        run.italic = True
        run.font.color.rgb = RGBColor(0x59, 0x59, 0x59)
        p_src.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_src.paragraph_format.space_before = Pt(0)
        p_src.paragraph_format.first_line_indent = Cm(0)
        p_src.paragraph_format.line_spacing = 1.0
        p_src.paragraph_format.space_after = Pt(8)


class DocxBuilder:
    """Собирает DOCX по ГОСТ."""

    def __init__(self, config: ProjectConfig, output_dir: pathlib.Path, images_dir: pathlib.Path = None):
        self.config = config
        self.output_dir = pathlib.Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir = pathlib.Path(images_dir) if images_dir else self.output_dir / "images"
        self.figure_counter = 0
        self.table_counter = 0

    def _create_title_page(self, doc: Document):
        # министерство
        p = doc.add_paragraph()
        run = p.add_run(self.config.organization.ministry)
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.first_line_indent = Cm(0)

        p = doc.add_paragraph()
        run = p.add_run(self.config.organization.university)
        run.bold = True
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)

        if self.config.organization.institute:
            p = doc.add_paragraph()
            run = p.add_run(self.config.organization.institute)
            run.font.name = "Times New Roman"
            run.font.size = Pt(12)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.first_line_indent = Cm(0)

        p = doc.add_paragraph()
        run = p.add_run(self.config.author.department)
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)

        # отступ
        for _ in range(2):
            doc.add_paragraph()

        # тип работы
        work_type_label = {
            "курсовая": "КУРСОВАЯ РАБОТА",
            "диплом": "ВЫПУСКНАЯ КВАЛИФИКАЦИОННАЯ РАБОТА",
            "вкр_бакалавр": "ВЫПУСКНАЯ КВАЛИФИКАЦИОННАЯ РАБОТА",
            "магистерская": "МАГИСТЕРСКАЯ ДИССЕРТАЦИЯ",
            "статья": "НАУЧНАЯ СТАТЬЯ",
        }.get(self.config.work_type.value, "ВЫПУСКНАЯ КВАЛИФИКАЦИОННАЯ РАБОТА")

        p = doc.add_paragraph()
        run = p.add_run(work_type_label)
        run.bold = True
        run.font.name = "Times New Roman"
        run.font.size = Pt(14)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)

        p = doc.add_paragraph()
        run = p.add_run(f"по дисциплине «{self.config.discipline}»")
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)

        for _ in range(1):
            doc.add_paragraph()

        # тема
        p = doc.add_paragraph()
        run = p.add_run(f"«{self.config.topic}»")
        run.bold = True
        run.font.name = "Times New Roman"
        run.font.size = Pt(16)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)

        for _ in range(3):
            doc.add_paragraph()

        # автор/руководитель (справа)
        info_lines = [
            f"Выполнил: {self.config.author.fio}",
            f"Группа: {self.config.author.group}",
            f"Факультет: {self.config.author.faculty}",
            "",
            f"Научный руководитель:",
            f"{self.config.author.supervisor}",
        ]
        for line in info_lines:
            p = doc.add_paragraph()
            run = p.add_run(line)
            run.font.name = "Times New Roman"
            run.font.size = Pt(12)
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.space_after = Pt(2)

        for _ in range(4):
            doc.add_paragraph()

        p = doc.add_paragraph()
        run = p.add_run(f"{self.config.organization.city} — {self.config.organization.year}")
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)

        # разрыв страницы
        doc.add_page_break()

    def _create_toc_placeholder(self, doc: Document):
        add_heading_styled(doc, "Содержание", level=1, centered=True)
        p = doc.add_paragraph()
        run = p.add_run("Оглавление формируется автоматически в Word: Ссылки → Оглавление → Автособираемое оглавление. Ниже — структура для ручной проверки.")
        run.font.name = "Times New Roman"
        run.font.size = Pt(11)
        run.italic = True
        p.paragraph_format.first_line_indent = Cm(0)

        # список разделов
        for ch in self.config.plan:
            if ch.number.isdigit():
                p = doc.add_paragraph(style="List Bullet")
                run = p.add_run(f"Глава {ch.number}. {ch.title}")
                run.font.name = "Times New Roman"
                run.font.size = Pt(12)
                p.paragraph_format.first_line_indent = Cm(0)
                p.paragraph_format.space_after = Pt(2)
                for sub in ch.subsections:
                    p2 = doc.add_paragraph(style="List Bullet 2")
                    run = p2.add_run(f"{sub.number} {sub.title}")
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(11)
                    p2.paragraph_format.first_line_indent = Cm(0)
                    p2.paragraph_format.space_after = Pt(1)
            elif ch.title in ("Введение", "Заключение", "Список использованных источников", "Приложения"):
                p = doc.add_paragraph(style="List Bullet")
                run = p.add_run(ch.title)
                run.bold = True
                run.font.name = "Times New Roman"
                run.font.size = Pt(12)
                p.paragraph_format.first_line_indent = Cm(0)

        doc.add_page_break()

    def _add_text_with_citations(self, doc: Document, markdown_text: str):
        """Конвертирует markdown-подобный текст в абзацы docx."""
        # Упрощённый парсер: заголовки #, списки, цитаты, таблицы markdown, изображения
        lines = markdown_text.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            if not line.strip():
                i += 1
                continue

            # заголовки markdown
            if line.startswith("# "):
                text = line[2:].strip()
                add_heading_styled(doc, text, level=1, centered=True, font_size=16)
                i += 1
                continue
            if line.startswith("## "):
                text = line[3:].strip()
                add_heading_styled(doc, text, level=2, centered=False, font_size=14)
                i += 1
                continue
            if line.startswith("### "):
                text = line[4:].strip()
                add_heading_styled(doc, text, level=3, centered=False, font_size=13)
                i += 1
                continue

            # изображение ![alt](path){#fig-...}
            img_match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)(?:\{#fig-([^\}]+)\})?", line)
            if img_match:
                caption = img_match.group(1).strip()
                img_rel = img_match.group(2).strip()
                # путь
                if img_rel.startswith("images/"):
                    img_path = self.images_dir / pathlib.Path(img_rel).name
                else:
                    img_path = self.images_dir / pathlib.Path(img_rel).name
                    # пробуем также output_dir
                    if not img_path.exists():
                        alt = self.output_dir / img_rel
                        if alt.exists():
                            img_path = alt
                self.figure_counter += 1
                # источник
                source_note = "Источник: составлено автором"
                # если synthetic в caption?
                synthetic = "учебный пример" in caption.lower()
                add_figure_gost(doc, img_path, caption or f"Иллюстрация {self.figure_counter}", self.figure_counter, source_note)
                i += 1
                continue

            # таблица markdown (определяем по |)
            if line.strip().startswith("|") and i + 1 < len(lines) and "---" in lines[i + 1]:
                # собираем таблицу
                headers = [c.strip() for c in line.strip().strip("|").split("|")]
                i += 2  # пропуск разделителя
                rows = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                    rows.append(row)
                    i += 1
                # подпись таблицы (следующая строка : ... {#tbl-...})
                caption = ""
                source_note = ""
                if i < len(lines) and lines[i].strip().startswith(":"):
                    caption = lines[i].strip().lstrip(":").split("{")[0].strip()
                    i += 1
                # синтетик?
                if not caption:
                    caption = f"Данные по теме «{self.config.topic}»"
                self.table_counter += 1
                add_table_gost(doc, headers, rows, caption, self.table_counter, source_note)
                continue

            # цитата markdown >
            if line.strip().startswith(">"):
                text = line.strip().lstrip(">").strip()
                # убираем [@...]
                text_clean = re.sub(r"\[@[^\]]+\]", "", text).strip()
                p = doc.add_paragraph()
                run = p.add_run(text_clean)
                run.font.name = "Times New Roman"
                run.font.size = Pt(12)
                run.italic = True
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p.paragraph_format.left_indent = Cm(1)
                p.paragraph_format.right_indent = Cm(1)
                p.paragraph_format.space_before = Pt(6)
                p.paragraph_format.space_after = Pt(6)
                p.paragraph_format.first_line_indent = Cm(0)
                # если есть цитата, добавим ссылку
                cite_match = re.search(r"\[@([^\]]+)\]", line)
                if cite_match:
                    p2 = doc.add_paragraph()
                    run = p2.add_run(f"[{cite_match.group(1)}]")
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(10)
                    run.italic = True
                    p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    p2.paragraph_format.first_line_indent = Cm(0)
                    p2.paragraph_format.space_after = Pt(2)
                i += 1
                continue

            # список нумерованный / маркированный
            if re.match(r"^\s*[-*]\s+", line) or re.match(r"^\s*\d+\.\s+", line):
                # собираем список до пустой строки
                list_items = []
                while i < len(lines) and (re.match(r"^\s*[-*]\s+", lines[i]) or re.match(r"^\s*\d+\.\s+", lines[i])):
                    item_text = re.sub(r"^\s*([-*]|\d+\.)\s+", "", lines[i]).strip()
                    # чистим цитаты
                    item_text = re.sub(r"\[@[^\]]+\]", "", item_text)
                    list_items.append(item_text)
                    i += 1
                for item in list_items:
                    p = doc.add_paragraph(style="List Bullet")
                    run = p.add_run(item)
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(14)
                    p.paragraph_format.first_line_indent = Cm(0)
                    p.paragraph_format.space_after = Pt(2)
                    p.paragraph_format.line_spacing = 1.5
                continue

            # обычный абзац (чистим markdown форматирование)
            text = line
            # **bold**, *italic*, [@cite]
            text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
            text = re.sub(r"\*([^*]+)\*", r"\1", text)
            # цитаты — убираем или заменяем на [n]
            def cite_replace(m):
                key = m.group(1).strip()
                # найдём номер источника
                for idx, src in enumerate(self.config.sources, 1):
                    if src.key == key.split()[0]:
                        return f"[{idx}]"
                return f"[{key}]"
            text = re.sub(r"\[@([^\]]+)\]", cite_replace, text)
            text = re.sub(r"@tbl-[\w-]+", "", text)
            text = re.sub(r"@fig-[\w-]+", "", text)
            text = text.strip()
            if text:
                add_paragraph_styled(doc, text)
            i += 1

    def build(self, markdown_chapters: Dict[str, str], bibliography_lines: List[str] = None) -> pathlib.Path:
        """Собирает DOCX из markdown глав."""
        doc = Document()

        # поля
        for section in doc.sections:
            set_margins(section, left_mm=30, right_mm=15, top_mm=20, bottom_mm=20)
            # нумерация страниц (нижний колонтитул)
            footer = section.footer
            footer.is_linked_to_previous = False
            p = footer.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            # поле PAGE
            run = p.add_run()
            fldChar1 = OxmlElement("w:fldChar")
            fldChar1.set(qn("w:fldCharType"), "begin")
            run._r.append(fldChar1)
            run2 = p.add_run()
            instr = OxmlElement("w:instrText")
            instr.set(qn("xml:space"), "preserve")
            instr.text = "PAGE"
            run2._r.append(instr)
            run3 = p.add_run()
            fldChar2 = OxmlElement("w:fldChar")
            fldChar2.set(qn("w:fldCharType"), "end")
            run3._r.append(fldChar2)

        # титул
        self._create_title_page(doc)
        # содержание
        self._create_toc_placeholder(doc)

        # введение и главы
        # сортировка ключей: 00_, 01_, 02_ ...
        sorted_keys = sorted(markdown_chapters.keys())
        for key in sorted_keys:
            md = markdown_chapters[key]
            self._add_text_with_citations(doc, md)
            # разрыв после каждой главы кроме последней
            if key != sorted_keys[-1]:
                doc.add_page_break()

        # список литературы
        add_heading_styled(doc, "Список использованных источников", level=1, centered=True)
        if bibliography_lines:
            for line in bibliography_lines:
                # line вида "1. Автор ... — DOI: ..."
                p = doc.add_paragraph()
                run = p.add_run(line)
                run.font.name = "Times New Roman"
                run.font.size = Pt(12)
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p.paragraph_format.first_line_indent = Cm(0)
                p.paragraph_format.left_indent = Cm(0)
                p.paragraph_format.space_after = Pt(3)
                p.paragraph_format.line_spacing = 1.0
                # узкий интервал для списка
                if line.strip().startswith("[УЧЕБНЫЙ"):
                    run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
                    run.italic = True
        else:
            p = doc.add_paragraph()
            p.add_run("Список литературы формируется автоматически.")

        # приложения (заглушка)
        doc.add_page_break()
        add_heading_styled(doc, "Приложения", level=1, centered=True)
        p = doc.add_paragraph()
        run = p.add_run("Приложение А. Исходные данные и расчёты (при наличии).")
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        run.italic = True
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # сохранение
        output_path = self.output_dir / "thesis.docx"
        doc.save(str(output_path))
        print(f"[docx] DOCX сохранён → {output_path} ({output_path.stat().st_size/1024:.1f} КБ)")
        return output_path

