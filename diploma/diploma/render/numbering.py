"""Автоматическая нумерация в Word через поля (SEQ, TOC, PAGE, REF).

Зачем поля вместо обычного текста
--------------------------------
Если вписать номера («Расм 2.1», «Боби 3») прямо в текст, то при вставке
нового рисунка или главы вся нумерация «поедет» и её придётся править руками.
Word умеет считать сам: поле ``SEQ`` увеличивает счётчик, а ``\\s`` и ``\\c``
связывают его с заголовками. Поэтому здесь номера **не печатаются**, а
вставляются как поля:

* глава:      ``Боби { SEQ Chapter \\* ARABIC \\s 1 }``;
* параграф:   ``{ SEQ Chapter \\c }.{ SEQ Section \\* ARABIC \\s 1 }``;
* рисунок:    ``Расм { SEQ Chapter \\c }.{ SEQ Figure \\* ARABIC \\s 1 }``;
* таблица:    ``Ҷадвал { SEQ Chapter \\c }.{ SEQ Table \\* ARABIC \\s 1 }``;
* ссылка:     ``расми { SEQ Chapter \\c }.{ SEQ Figure \\c }``.

Переключатели SEQ (Microsoft Word):
``\\s n`` — сбрасывать счётчик у каждого заголовка уровня n;
``\\c``   — повторить ближайшее предыдущее значение;
``\\r n`` — установить счётчик в n (используется для сброса в приложениях);
``\\h``   — скрыть результат поля.

Каждое поле получает кэшированное значение (``w:fldChar separate`` + текст),
поэтому документ выглядит правильно и до обновления полей, а флаг
``w:dirty="true"`` заставляет Word пересчитать номера при открытии.
"""

from __future__ import annotations

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# Идентификаторы счётчиков. Одинаковые во всём документе — это важно:
# именно так Word понимает, что «Расм 2.3» относится к главе 2.
SEQ_CHAPTER = "Chapter"
SEQ_SECTION = "Section"
SEQ_FIGURE = "Figure"
SEQ_TABLE = "Table"
SEQ_APPENDIX = "Appendix"
SEQ_FIGURE_A = "FigureA"
SEQ_TABLE_A = "TableA"

# Порядок элементов внутри <w:sectPr> (схема OOXML)
SECTPR_ORDER = [
    "w:footnotePr", "w:endnotePr", "w:type", "w:pgSz", "w:pgMar", "w:paperSrc",
    "w:pgBorders", "w:lnNumType", "w:pgNumType", "w:cols", "w:formProt",
    "w:vAlign", "w:noEndnote", "w:titlePg", "w:textDirection",
    "w:bidi", "w:rtlGutter", "w:docGrid", "w:printerSettings",
]


# --------------------------------------------------------------------------- #
# Базовые поля
# --------------------------------------------------------------------------- #


def add_field(paragraph, instr: str, cached: str = "", dirty: bool = True):
    """Вставляет поле Word: begin → instrText → separate → результат → end.

    ``cached`` — значение, которое видно до обновления полей (Word пересчитает
    его при открытии/печати). Оно же спасает, если получатель открывает файл
    не в Word (например, в LibreOffice или просмотрщике).
    """
    run = paragraph.add_run()

    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    if dirty:
        fld_begin.set(qn("w:dirty"), "true")
    run._r.append(fld_begin)

    instr_el = OxmlElement("w:instrText")
    instr_el.set(qn("xml:space"), "preserve")
    instr_el.text = f" {instr} "
    run._r.append(instr_el)

    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    run._r.append(fld_sep)

    result = OxmlElement("w:t")
    result.text = cached
    run._r.append(result)

    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_end)
    return run


def seq(
    paragraph,
    name: str,
    cached: str = "",
    switches: str = "",
    arabic: bool = True,
    restart_at_heading: int | None = None,
    repeat_nearest: bool = False,
    hidden: bool = False,
):
    """Поле ``SEQ``.

    ``restart_at_heading`` — добавляет ``\\s n``: счётчик сбрасывается у
    каждого заголовка уровня n (главы → ``\\s 1``).
    ``repeat_nearest`` — добавляет ``\\c``: повторить ближайшее значение
    (используется в номере параграфа/рисунка и в перекрёстных ссылках).
    """
    parts = [f"SEQ {name}"]
    if arabic:
        parts.append(r"\* ARABIC")
    if repeat_nearest:
        parts.append(r"\c")
    if restart_at_heading:
        parts.append(rf"\s {restart_at_heading}")
    if switches:
        parts.append(switches)
    if hidden:
        parts.append(r"\h")
    return add_field(paragraph, " ".join(parts), cached=cached)


def add_toc(
    paragraph,
    levels: str = "1-2",
    switches: str = r'\h \z \u',
    cached: str = "Мундариҷаро нав кунед (Ctrl+A, F9).",
):
    """Поле содержания: TOC \\o "1-2" \\h \\z \\u."""
    return add_field(paragraph, f'TOC \\o "{levels}" {switches}', cached=cached)


def add_page_number(paragraph, cached: str = "1"):
    """Поле PAGE (номер страницы)."""
    return add_field(paragraph, "PAGE", cached=cached)


def add_numpages(paragraph, cached: str = "1"):
    return add_field(paragraph, "NUMPAGES", cached=cached)


def add_ref(paragraph, bookmark: str, cached: str = "", above_below: bool = True):
    """Ссылка на закладку: ``REF name \\h`` (или ``\\p`` — «выше/ниже»)."""
    instr = f"REF {bookmark} " + (r"\h" if above_below else "")
    return add_field(paragraph, instr, cached=cached)


def set_bookmark(paragraph, name: str, after_run=None):
    """Создаёт закладку вокруг абзаца (нужна для перекрёстных ссылок)."""
    p = paragraph._p
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), str(abs(hash(name)) % 10**8))
    start.set(qn("w:name"), name)
    end = OxmlElement("w:bookmarkEnd")
    end.set(qn("w:id"), start.get(qn("w:id")))
    if after_run is not None:
        after_run._r.addnext(start)
        start.addnext(end)
    else:
        p.insert(0, start)
        p.append(end)
    return start


# --------------------------------------------------------------------------- #
# Номера разделов, рисунков, таблиц
# --------------------------------------------------------------------------- #


def chapter_number(paragraph, cached: str = "1"):
    """Номер главы: ``{ SEQ Chapter \\* ARABIC }``.

    Здесь НЕЛЬЗЯ добавлять ``\\s 1``: счётчик сбрасывался бы у каждого
    заголовка 1-го уровня, то есть в самой главе, и все главы стали бы
    «Боби 1». Главы просто увеличиваются на единицу.
    """
    return seq(paragraph, SEQ_CHAPTER, cached=cached)


def section_number(paragraph, cached: str = "1.1"):
    """Номер параграфа: ``{ SEQ Chapter \\c }.{ SEQ Section \\* ARABIC \\s 1 }``."""
    ch, _, sec = cached.partition(".")
    seq(paragraph, SEQ_CHAPTER, cached=ch, repeat_nearest=True)
    run = paragraph.add_run(".")
    seq(paragraph, SEQ_SECTION, cached=sec, restart_at_heading=1)
    return run


def object_number(paragraph, kind: str, cached: str = "1.1"):
    """Номер рисунка/таблицы: ``{ SEQ Chapter \\c }.{ SEQ Figure \\s 1 }``."""
    name = SEQ_FIGURE if kind == "fig" else SEQ_TABLE
    ch, _, num = cached.partition(".")
    seq(paragraph, SEQ_CHAPTER, cached=ch, repeat_nearest=True)
    paragraph.add_run(".")
    return seq(paragraph, name, cached=num, restart_at_heading=1)


def object_ref(paragraph, kind: str, cached: str = "1.1"):
    """Перекрёстная ссылка: ``расми { SEQ Chapter \\c }.{ SEQ Figure \\c }``."""
    name = SEQ_FIGURE if kind == "fig" else SEQ_TABLE
    ch, _, num = cached.partition(".")
    seq(paragraph, SEQ_CHAPTER, cached=ch, repeat_nearest=True)
    paragraph.add_run(".")
    return seq(paragraph, name, cached=num, repeat_nearest=True)


def continuous_number(paragraph, kind: str, cached: str = "1"):
    """Сквозная нумерация (без привязки к главе): ``{ SEQ Figure }``."""
    name = SEQ_FIGURE if kind == "fig" else SEQ_TABLE
    return seq(paragraph, name, cached=cached)


def appendix_letter(paragraph, cached: str = "А"):
    """Обозначение приложения: ``{ SEQ Appendix \\* ALPHABETIC }``."""
    return add_field(paragraph, f"SEQ {SEQ_APPENDIX} \\* ALPHABETIC", cached=cached)


def appendix_object_number(paragraph, kind: str, cached: str = "А.1"):
    """Номер объекта в приложении: буква приложения + ``SEQ TableA \\s 1``.

    Для приложений используются отдельные счётчики (``FigureA``, ``TableA``):
    они не мешают нумерации рисунков и таблиц основной части.
    """
    name = SEQ_FIGURE_A if kind == "fig" else SEQ_TABLE_A
    letter, _, number = cached.partition(".")
    paragraph.add_run(f"{letter}.")
    return seq(paragraph, name, cached=number, restart_at_heading=1)


def appendix_object_ref(paragraph, kind: str, cached: str = "А.1"):
    """Ссылка на объект приложения: буква + ``SEQ TableA \\c``."""
    name = SEQ_FIGURE_A if kind == "fig" else SEQ_TABLE_A
    letter, _, number = cached.partition(".")
    paragraph.add_run(f"{letter}.")
    return seq(paragraph, name, cached=number, repeat_nearest=True)


# --------------------------------------------------------------------------- #
# Колонтитулы и номера страниц
# --------------------------------------------------------------------------- #


def page_number_footer(
    section,
    align: str = "center",
    start: int | None = None,
    page_word: str = "",
    cached: str = "1",
):
    """Номер страницы внизу по центру (требование ГОСТ 7.32-2017).

    ``start`` — с какого номера начинать нумерацию в этой секции
    (ставится ``w:pgNumType``).
    """
    footer = section.footer
    footer.is_linked_to_previous = False
    p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    p.alignment = {
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "right": WD_ALIGN_PARAGRAPH.RIGHT,
        "left": WD_ALIGN_PARAGRAPH.LEFT,
    }.get(align, WD_ALIGN_PARAGRAPH.CENTER)
    if page_word:
        p.add_run(f"{page_word} ")
    add_page_number(p, cached=cached)
    if start is not None:
        set_page_number_start(section, start)
    return p


def set_page_number_start(section, start: int) -> None:
    """Устанавливает начальный номер страницы секции."""
    sectPr = section._sectPr
    el = sectPr.find(qn("w:pgNumType"))
    if el is None:
        el = OxmlElement("w:pgNumType")
        _insert_in_order(sectPr, el)
    el.set(qn("w:start"), str(start))


def set_page_borders(
    section,
    left_mm: float = 20,
    right_mm: float = 5,
    top_mm: float = 5,
    bottom_mm: float = 5,
    from_edge_mm: float = 0,
) -> None:
    """Рамка страницы (по ГОСТ 7.32-2017 на титульном листе отчёта о НИР)."""
    sectPr = section._sectPr
    for old in sectPr.findall(qn("w:pgBorders")):
        sectPr.remove(old)
    borders = OxmlElement("w:pgBorders")
    borders.set(qn("w:offsetFrom"), "page")
    sides = {"top": top_mm, "left": left_mm, "bottom": bottom_mm, "right": right_mm}
    for side, mm in sides.items():
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "8")  # 0,5 pt
        el.set(qn("w:space"), str(int(mm * 56.7)))  # мм → твипы
        el.set(qn("w:color"), "000000")
        borders.append(el)
    _insert_in_order(sectPr, borders)


def _insert_in_order(sectPr, element) -> None:
    """Вставляет элемент в <w:sectPr> с соблюдением порядка схемы OOXML."""
    tag = element.tag.split("}")[-1]
    name = f"w:{tag}"
    idx = SECTPR_ORDER.index(name) if name in SECTPR_ORDER else len(SECTPR_ORDER)
    for candidate in SECTPR_ORDER[idx + 1 :]:
        found = sectPr.find(qn(candidate))
        if found is not None:
            found.addprevious(element)
            return
    sectPr.append(element)


def field_instructions(paragraph) -> list[str]:
    """Все инструкции полей абзаца (для тестов и отладки)."""
    return [
        node.text or ""
        for node in paragraph._p.iter(qn("w:instrText"))
    ]


def field_instructions_document(document) -> list[str]:
    out: list[str] = []
    for part in (document, *(getattr(document, "sections", []) and [])):
        _ = part
    for p in document.paragraphs:
        out.extend(field_instructions(p))
    for section in document.sections:
        for p in list(section.footer.paragraphs) + list(section.header.paragraphs):
            out.extend(field_instructions(p))
    return out
