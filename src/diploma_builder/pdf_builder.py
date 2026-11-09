"""
pdf_builder.py — сборка PDF по ГОСТ (reportlab, с фолбэком weasyprint).

Для кириллицы используем встроенные шрифты DejaVu (если доступны) или Helvetica.
"""

from __future__ import annotations

import pathlib
import re
from typing import List, Dict

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
    Image as RLImage,
    ListFlowable,
    ListItem,
)
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import reportlab.lib.fonts

from .config import ProjectConfig


# Цвета
COLORS = {
    "primary": HexColor("#1f4e79"),
    "secondary": HexColor("#548235"),
    "light_blue": HexColor("#D9E2F3"),
    "gray": HexColor("#595959"),
}


def _register_fonts():
    """Регистрируем DejaVu если есть, иначе fallback."""
    import pathlib as pl

    # Попробуем найти DejaVu
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    ]
    found = None
    for p in candidates:
        if pl.Path(p).exists():
            found = p
            break
    if found:
        try:
            # Регистрируем обычный и жирный
            pdfmetrics.registerFont(TTFont("GOST", found))
            # bold — пробуем найти
            bold_candidates = [
                str(pl.Path(found).parent / pl.Path(found).name.replace("Regular", "Bold").replace(".ttf", "-Bold.ttf")),
                "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                found,
            ]
            for b in bold_candidates:
                if pl.Path(b).exists():
                    pdfmetrics.registerFont(TTFont("GOST-Bold", b))
                    break
            else:
                pdfmetrics.registerFont(TTFont("GOST-Bold", found))
            print(f"[pdf] Шрифт зарегистрирован: {found}")
            return "GOST", "GOST-Bold"
        except Exception as e:
            print(f"[pdf] Ошибка регистрации шрифта {found}: {e}")

    # fallback — Helvetica (не поддерживает кириллицу полностью, но работает латиницей)
    # Используем встроенный
    print("[pdf] Используется Helvetica (fallback, кириллица может отображаться некорректно)")
    return "Helvetica", "Helvetica-Bold"


FONT_NORMAL, FONT_BOLD = _register_fonts()


def _footer(canvas, doc):
    """Нумерация страниц внизу по центру."""
    canvas.saveState()
    canvas.setFont(FONT_NORMAL, 9)
    canvas.setFillColor(COLORS["gray"])
    page_num = canvas.getPageNumber()
    text = f"{page_num}"
    canvas.drawCentredString(A4[0] / 2, 15 * mm, text)
    canvas.restoreState()


class PdfBuilder:
    def __init__(self, config: ProjectConfig, output_dir: pathlib.Path, images_dir: pathlib.Path = None):
        self.config = config
        self.output_dir = pathlib.Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir = pathlib.Path(images_dir) if images_dir else self.output_dir / "images"
        self.figure_counter = 0
        self.table_counter = 0

        # стили
        self.styles = getSampleStyleSheet()
        self._init_styles()

    def _init_styles(self):
        # Базовый 14pt
        self.styles.add(
            ParagraphStyle(
                name="GOST_Normal",
                parent=self.styles["Normal"],
                fontName=FONT_NORMAL,
                fontSize=11,  # в PDF 11pt ~ 14pt в Word из-за разницы dpi
                leading=16,
                alignment=TA_JUSTIFY,
                firstLineIndent=1.25 * cm,
                spaceAfter=6,
                textColor=black,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="GOST_Heading1",
                parent=self.styles["Normal"],
                fontName=FONT_BOLD,
                fontSize=15,
                leading=18,
                alignment=TA_CENTER,
                spaceBefore=12,
                spaceAfter=10,
                textColor=black,
                keepWithNext=True,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="GOST_Heading2",
                parent=self.styles["Normal"],
                fontName=FONT_BOLD,
                fontSize=12,
                leading=15,
                alignment=TA_LEFT,
                spaceBefore=10,
                spaceAfter=6,
                textColor=COLORS["primary"],
                keepWithNext=True,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="GOST_Heading3",
                parent=self.styles["Normal"],
                fontName=FONT_BOLD,
                fontSize=11,
                leading=14,
                alignment=TA_LEFT,
                spaceBefore=8,
                spaceAfter=4,
                textColor=black,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="GOST_Caption",
                parent=self.styles["Normal"],
                fontName=FONT_NORMAL,
                fontSize=9,
                leading=11,
                alignment=TA_CENTER,
                spaceBefore=4,
                spaceAfter=2,
                textColor=black,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="GOST_SourceNote",
                parent=self.styles["Normal"],
                fontName=FONT_NORMAL,
                fontSize=7,
                leading=9,
                alignment=TA_CENTER,
                textColor=COLORS["gray"],
                fontName2=FONT_NORMAL,
                spaceBefore=0,
                spaceAfter=8,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="GOST_TableCell",
                parent=self.styles["Normal"],
                fontName=FONT_NORMAL,
                fontSize=8,
                leading=10,
                alignment=TA_CENTER,
                spaceAfter=2,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="GOST_TitlePage",
                parent=self.styles["Normal"],
                fontName=FONT_NORMAL,
                fontSize=10,
                leading=12,
                alignment=TA_CENTER,
                spaceAfter=4,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="GOST_TitleTopic",
                parent=self.styles["Normal"],
                fontName=FONT_BOLD,
                fontSize=14,
                leading=16,
                alignment=TA_CENTER,
                textColor=COLORS["primary"],
                spaceBefore=12,
                spaceAfter=12,
            )
        )

    def _story_title_page(self) -> List:
        story = []
        # министерство
        story.append(Paragraph(self.config.organization.ministry, self.styles["GOST_TitlePage"]))
        story.append(Paragraph(f"<b>{self.config.organization.university}</b>", self.styles["GOST_TitlePage"]))
        if self.config.organization.institute:
            story.append(Paragraph(self.config.organization.institute, self.styles["GOST_TitlePage"]))
        story.append(Paragraph(self.config.author.department, self.styles["GOST_TitlePage"]))
        story.append(Spacer(1, 1.5 * cm))

        work_type_label = {
            "курсовая": "КУРСОВАЯ РАБОТА",
            "диплом": "ВЫПУСКНАЯ КВАЛИФИКАЦИОННАЯ РАБОТА",
            "вкр_бакалавр": "ВЫПУСКНАЯ КВАЛИФИКАЦИОННАЯ РАБОТА",
            "магистерская": "МАГИСТЕРСКАЯ ДИССЕРТАЦИЯ",
            "статья": "НАУЧНАЯ СТАТЬЯ",
        }.get(self.config.work_type.value, "ВЫПУСКНАЯ КВАЛИФИКАЦИОННАЯ РАБОТА")

        p = Paragraph(f"<b>{work_type_label}</b><br/>по дисциплине «{self.config.discipline}»", self.styles["GOST_TitlePage"])
        story.append(p)
        story.append(Spacer(1, 1 * cm))

        story.append(Paragraph(f"«{self.config.topic}»", self.styles["GOST_TitleTopic"]))
        story.append(Spacer(1, 2 * cm))

        info = [
            f"Выполнил: {self.config.author.fio} — {self.config.author.group}",
            f"Факультет: {self.config.author.faculty}",
            "",
            f"Научный руководитель: {self.config.author.supervisor}",
        ]
        for line in info:
            if not line:
                story.append(Spacer(1, 0.3 * cm))
                continue
            s = Paragraph(line, ParagraphStyle("tmp", parent=self.styles["GOST_TitlePage"], alignment=TA_RIGHT, fontSize=9))
            story.append(s)
        story.append(Spacer(1, 3 * cm))
        story.append(Paragraph(f"{self.config.organization.city} — {self.config.organization.year}", self.styles["GOST_TitlePage"]))
        story.append(PageBreak())
        return story

    def _story_toc(self) -> List:
        story = []
        story.append(Paragraph("Содержание", self.styles["GOST_Heading1"]))
        story.append(Spacer(1, 0.5 * cm))
        for ch in self.config.plan:
            if ch.number.isdigit():
                story.append(Paragraph(f"<b>Глава {ch.number}. {ch.title}</b>", self.styles["GOST_Heading2"]))
                for sub in ch.subsections:
                    story.append(Paragraph(f"{sub.number} {sub.title}", self.styles["GOST_Normal"]))
            elif ch.title in ("Введение", "Заключение", "Список использованных источников", "Приложения"):
                story.append(Paragraph(f"<b>{ch.title}</b>", self.styles["GOST_Heading2"]))
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph("<i>Оглавление в PDF автоматически не генерируется нумерацией страниц. Для навигации используйте закладки.</i>", self.styles["GOST_SourceNote"]))
        story.append(PageBreak())
        return story

    def _parse_markdown_to_story(self, markdown_text: str) -> List:
        story = []
        lines = markdown_text.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            if not line.strip():
                i += 1
                continue
            if line.startswith("# "):
                story.append(Paragraph(line[2:].strip(), self.styles["GOST_Heading1"]))
                i += 1
                continue
            if line.startswith("## "):
                story.append(Paragraph(line[3:].strip(), self.styles["GOST_Heading2"]))
                i += 1
                continue
            if line.startswith("### "):
                story.append(Paragraph(line[4:].strip(), self.styles["GOST_Heading3"]))
                i += 1
                continue

            # изображение
            img_match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line)
            if img_match:
                caption = img_match.group(1).strip()
                img_rel = img_match.group(2).strip()
                # путь
                if img_rel.startswith("images/"):
                    img_path = self.images_dir / pathlib.Path(img_rel).name
                else:
                    img_path = self.images_dir / pathlib.Path(img_rel).name
                if not img_path.exists():
                    # пробуем output_dir
                    alt = self.output_dir / img_rel
                    if alt.exists():
                        img_path = alt
                self.figure_counter += 1
                if img_path.exists():
                    try:
                        # ширина 14 см
                        img = RLImage(str(img_path), width=14 * cm, height=8 * cm)
                        img.hAlign = "CENTER"
                        story.append(Spacer(1, 0.2 * cm))
                        story.append(img)
                        story.append(Paragraph(f"Рисунок {self.figure_counter} — {caption or 'Иллюстрация'}", self.styles["GOST_Caption"]))
                        # источник
                        note = "Источник: составлено автором"
                        story.append(Paragraph(note, self.styles["GOST_SourceNote"]))
                    except Exception as e:
                        story.append(Paragraph(f"[Ошибка рисунка: {e}]", self.styles["GOST_Normal"]))
                else:
                    story.append(Paragraph(f"[Рисунок {self.figure_counter} отсутствует: {img_path.name}]", self.styles["GOST_Normal"]))
                i += 1
                continue

            # таблица markdown
            if line.strip().startswith("|") and i + 1 < len(lines) and "---" in lines[i + 1]:
                headers = [c.strip() for c in line.strip().strip("|").split("|")]
                i += 2
                rows = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                    rows.append(row)
                    i += 1
                caption = ""
                if i < len(lines) and lines[i].strip().startswith(":"):
                    caption = lines[i].strip().lstrip(":").split("{")[0].strip()
                    i += 1
                self.table_counter += 1
                cap_text = f"Таблица {self.table_counter} — {caption or 'Данные'}"
                story.append(Spacer(1, 0.2 * cm))
                story.append(Paragraph(cap_text, ParagraphStyle("tblcap", parent=self.styles["GOST_Caption"], alignment=TA_LEFT, fontName=FONT_NORMAL)))
                # таблица
                data = [[Paragraph(f"<b>{h}</b>", self.styles["GOST_TableCell"]) for h in headers]]
                for r in rows:
                    data.append([Paragraph(c, self.styles["GOST_TableCell"]) for c in r])
                # ширины
                col_width = (17 * cm) / len(headers)
                t = Table(data, colWidths=[col_width] * len(headers))
                t.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), COLORS["light_blue"]),
                            ("TEXTCOLOR", (0, 0), (-1, 0), black),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                            ("FONTSIZE", (0, 0), (-1, -1), 8),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                            ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ]
                    )
                )
                story.append(t)
                story.append(Spacer(1, 0.2 * cm))
                continue

            # цитата >
            if line.strip().startswith(">"):
                text = line.strip().lstrip(">").strip()
                text_clean = re.sub(r"\[@[^\]]+\]", "", text).strip()
                style_q = ParagraphStyle("quote", parent=self.styles["GOST_Normal"], leftIndent=1 * cm, rightIndent=1 * cm, fontName=FONT_NORMAL, textColor=COLORS["gray"], borderPadding=(6, 6, 6), backColor=HexColor("#f2f2f2"))
                story.append(Paragraph(f"<i>«{text_clean}»</i>", style_q))
                cite_match = re.search(r"\[@([^\]]+)\]", line)
                if cite_match:
                    story.append(Paragraph(f"[{cite_match.group(1)}]", ParagraphStyle("cite", parent=self.styles["GOST_SourceNote"], alignment=TA_RIGHT)))
                i += 1
                continue

            # список
            if re.match(r"^\s*[-*]\s+", line) or re.match(r"^\s*\d+\.\s+", line):
                items = []
                while i < len(lines) and (re.match(r"^\s*[-*]\s+", lines[i]) or re.match(r"^\s*\d+\.\s+", lines[i])):
                    item_text = re.sub(r"^\s*([-*]|\d+\.)\s+", "", lines[i]).strip()
                    item_text = re.sub(r"\[@[^\]]+\]", "", item_text)
                    item_text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", item_text)
                    items.append(Paragraph(item_text, self.styles["GOST_Normal"]))
                    i += 1
                # reportlab list
                lf = ListFlowable([ListItem(It) for It in items], bulletType="bullet", start="circle", leftIndent=1 * cm)
                story.append(lf)
                story.append(Spacer(1, 0.2 * cm))
                continue

            # обычный абзац
            text = line
            text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
            text = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", text)

            def cite_replace(m):
                key = m.group(1).strip().split()[0]
                for idx, src in enumerate(self.config.sources, 1):
                    if src.key == key:
                        return f"[{idx}]"
                return f"[{key}]"

            text = re.sub(r"\[@([^\]]+)\]", cite_replace, text)
            text = re.sub(r"@tbl-[\w-]+", "", text)
            text = re.sub(r"@fig-[\w-]+", "", text)
            text = text.strip()
            if text:
                # экранируем html
                text = text.replace("&", "&amp;")
                story.append(Paragraph(text, self.styles["GOST_Normal"]))
            i += 1
        return story

    def build(self, markdown_chapters: Dict[str, str], bibliography_lines: List[str] = None) -> pathlib.Path:
        output_path = self.output_dir / "thesis.pdf"
        # Поля ГОСТ: 30-15-20-20 мм
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=30 * mm,
            rightMargin=15 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
            title=self.config.topic,
            author=self.config.author.fio,
        )

        story = []
        # титул
        story.extend(self._story_title_page())
        # содержание
        story.extend(self._story_toc())

        # главы
        sorted_keys = sorted(markdown_chapters.keys())
        for idx, key in enumerate(sorted_keys):
            md = markdown_chapters[key]
            story.extend(self._parse_markdown_to_story(md))
            if idx < len(sorted_keys) - 1:
                story.append(PageBreak())

        # список литературы
        story.append(Paragraph("Список использованных источников", self.styles["GOST_Heading1"]))
        story.append(Spacer(1, 0.3 * cm))
        if bibliography_lines:
            for line in bibliography_lines:
                # line: "1. Автор ... — DOI..."
                style = ParagraphStyle(f"bib_{hash(line)%10000}", parent=self.styles["GOST_Normal"], fontSize=9, leading=11, firstLineIndent=0, leftIndent=0.5 * cm, spaceAfter=4, alignment=TA_LEFT)
                # если учебный пример — красный
                if "[УЧЕБНЫЙ" in line or "учебный пример" in line.lower():
                    style.textColor = HexColor("#bf0000")
                story.append(Paragraph(line.replace("&", "&amp;"), style))
        else:
            story.append(Paragraph("Список литературы формируется автоматически.", self.styles["GOST_Normal"]))

        story.append(PageBreak())
        story.append(Paragraph("Приложения", self.styles["GOST_Heading1"]))
        story.append(Paragraph("Приложение А. Исходные данные и расчёты (при наличии).", ParagraphStyle("app", parent=self.styles["GOST_Normal"], alignment=TA_CENTER, fontSize=10)))

        doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
        print(f"[pdf] PDF сохранён → {output_path} ({output_path.stat().st_size/1024:.1f} КБ)")
        return output_path

