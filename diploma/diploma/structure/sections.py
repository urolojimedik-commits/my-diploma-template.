"""Разделы медицинской работы и правила нумерации.

Разделы перечислены в том порядке, который требуют ГОСТ 7.32-2017 (отчёт о НИР)
и ГОСТ Р 7.0.11-2011 (диссертация) с поправкой на медицинскую схему IMRAD:

    Introduction, Methods, Results, and Discussion.

Названия разделов хранятся и на таджикском (основа) и на русском — для
двуязычной аннотации и для отчётов системы.

Нумерация
---------
* главы — «Боби 1», «Боби 2» … (каждая с новой страницы);
* параграфы — 1.1, 1.2, 1.3 … (внутри главы);
* рисунки и таблицы — по главам: «Расм 2.1», «Ҷадвал 2.2»
  (или сквозная, если в ``config/university.yml`` стоит ``numbering: continuous``).

Правило системы: номера в тексте не «зашиваются» вручную, а подставляются
из этой модели; в Word они оформляются полями ``SEQ`` (см. render/docx.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from ..model import Plan, SectionPlan, Topic
from ..lang import get_language


# --------------------------------------------------------------------------- #
# Описание раздела
# --------------------------------------------------------------------------- #


@dataclass
class SectionSpec:
    id: str
    kind: str  # front | body | back
    level: int  # 1 — глава (Боб), 2 — параграф, 0 — ненумеруемый раздел
    title_tg: str
    title_ru: str
    number: str = ""  # «1», «2.1», «» для ненумеруемых
    numbered: bool = True  # участвует ли в автонумерации Word
    required: bool = True
    target_words: int = 400
    goal: str = ""  # что должно быть в разделе (для генератора и для проверки)
    children: list["SectionSpec"] = field(default_factory=list)

    # ------------------------------------------------------------------ вывод
    @property
    def heading(self) -> str:
        """Заголовок для документа на таджикском, уже с номером."""
        if not self.numbered or not self.number:
            return self.title_tg
        if self.level == 1:
            return f"{_t('chapter_gen')} {self.number}. {self.title_tg}"
        return f"{self.number}. {self.title_tg}"

    @property
    def heading_ru(self) -> str:
        if not self.numbered or not self.number:
            return self.title_ru
        if self.level == 1:
            return f"Глава {self.number}. {self.title_ru}"
        return f"{self.number}. {self.title_ru}"

    def title(self, lang: str = "tg") -> str:
        return self.title_tg if lang == "tg" else self.title_ru

    def walk(self) -> Iterable["SectionSpec"]:
        yield self
        for c in self.children:
            yield from c.walk()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "level": self.level,
            "title_tg": self.title_tg,
            "title_ru": self.title_ru,
            "number": self.number,
            "numbered": self.numbered,
            "required": self.required,
            "target_words": self.target_words,
            "goal": self.goal,
            "children": [c.to_dict() for c in self.children],
        }


def _t(key: str) -> str:
    return get_language("tg").t(key)


# --------------------------------------------------------------------------- #
# Порядок разделов
# --------------------------------------------------------------------------- #

# Передняя часть (ненумеруемые разделы, страницы нумеруются как ii, iii…)
FRONT: list[tuple[str, str, str]] = [
    ("title", "Варақи унвонӣ", "Титульный лист"),
    ("contents", "Мундариҷа", "Содержание"),
    ("annotation", "Аннотатсия", "Аннотация"),
    ("abbreviations", "Рӯйхати ихтисораҳо", "Список сокращений"),
    ("introduction", "Муқаддима", "Введение"),
]

# Задняя часть
BACK: list[tuple[str, str, str]] = [
    ("conclusion", "Хулоса", "Заключение"),
    ("recommendations", "Тавсияҳои амалӣ", "Практические рекомендации"),
    ("references", "Рӯйхати адабиёт", "Список использованных источников"),
    ("appendices", "Замимаҳо", "Приложения"),
]

# Главы IMRAD: номер главы → (название tg, название ru, параграфы)
# Параграфы: (id, tg, ru, цель)
CHAPTERS: dict[int, tuple[str, str, list[tuple[str, str, str, str]]]] = {
    1: (
        "Баррасии адабиёт",
        "Обзор литературы",
        [
            (
                "ch1-1",
                "Вазъи муосири масъала",
                "Современное состояние проблемы",
                "эпидемиология, факторҳои хавф ва аҳамияти клиникии мавзӯъ",
            ),
            (
                "ch1-2",
                "Усулҳои мавҷудаи ташхис ва муолиҷа",
                "Существующие методы диагностики и лечения",
                "усулҳои анъанавӣ, маҳдудиятҳо ва дақиқии онҳо",
            ),
            (
                "ch1-3",
                "Истифодаи технологияҳои иттилоотӣ дар тиб",
                "Применение информационных технологий в медицине",
                "шарҳи таҳқиқотҳои қаблӣ ва натиҷаҳои онҳо",
            ),
        ],
    ),
    2: (
        "Мавод ва усулҳои таҳқиқот",
        "Материалы и методы исследования",
        [
            (
                "ch2-1",
                "Тарҳи таҳқиқот ва хусусияти беморон",
                "Дизайн исследования и характеристика пациентов",
                "тарҳ, меъёрҳои дохилшавӣ/хориҷшавӣ, ҳаҷми интихоб",
            ),
            (
                "ch2-2",
                "Усулҳои таҳқиқот",
                "Методы исследования",
                "усулҳои клиникӣ, лабораторӣ ва инструменталӣ",
            ),
            (
                "ch2-3",
                "Усулҳои коркарди оморӣ",
                "Методы статистической обработки",
                "меъёрҳои оморӣ, озмоишҳо, сатҳи аҳамиятнокӣ",
            ),
        ],
    ),
    3: (
        "Натиҷаҳои таҳқиқот",
        "Результаты исследования",
        [
            (
                "ch3-1",
                "Хусусияти умумии беморон",
                "Общая характеристика пациентов",
                "сину сол, ҷинс, гурӯҳҳои муқоисавӣ",
            ),
            (
                "ch3-2",
                "Натиҷаҳои асосӣ",
                "Основные результаты",
                "натиҷаҳои асосии таҳқиқот бо нишондиҳандаҳои оморӣ",
            ),
            (
                "ch3-3",
                "Таҳлили зергурӯҳҳо",
                "Анализ подгрупп",
                "муқоисаи зергурӯҳҳо ва омилҳои вобаста",
            ),
        ],
    ),
    4: (
        "Муҳокимаи натиҷаҳо",
        "Обсуждение результатов",
        [
            (
                "ch4-1",
                "Муқоиса бо маълумотҳои адабиёт",
                "Сопоставление с данными литературы",
                "муқоиса бо натиҷаҳои муаллифони дигар (танҳо сарчашмаҳои санҷидашуда)",
            ),
            (
                "ch4-2",
                "Маҳдудиятҳои таҳқиқот",
                "Ограничения исследования",
                "маҳдудиятҳо ва хатари хатоҳо",
            ),
        ],
    ),
}

# Вариант для курсовой работы: 2 главы, обсуждение — параграфом в главе 2.
COURSE_CHAPTERS: dict[int, tuple[str, str, list[tuple[str, str, str, str]]]] = {
    1: CHAPTERS[1],
    2: (
        "Мавод, усулҳо ва натиҷаҳои таҳқиқот",
        "Материалы, методы и результаты исследования",
        [
            CHAPTERS[2][2][0],  # дизайн и характеристика
            CHAPTERS[2][2][1],  # методы
            CHAPTERS[3][2][1],  # основные результаты
            (
                "ch2-4",
                "Муҳокимаи натиҷаҳо",
                "Обсуждение результатов",
                "муқоиса бо адабиёт ва маҳдудиятҳо",
            ),
        ],
    ),
}

# Объём разделов в словах (ориентир; берётся из volumes в university.yml)
TARGET_WORDS = {
    "annotation": 200,
    "introduction": 800,
    "ch1-1": 900,
    "ch1-2": 900,
    "ch1-3": 700,
    "ch2-1": 500,
    "ch2-2": 600,
    "ch2-3": 400,
    "ch3-1": 400,
    "ch3-2": 700,
    "ch3-3": 500,
    "ch4-1": 700,
    "ch4-2": 300,
    "conclusion": 500,
    "recommendations": 300,
}

# Цели передней и задней части
FRONT_GOALS = {
    "annotation": "мухтасари мақсад, усулҳо ва натиҷаҳои асосӣ (150–250 калима)",
    "abbreviations": "рӯйхати ихтисораҳо бо тавзеҳи пурра",
    "introduction": (
        "аҳамияти мавзӯъ, мақсад, вазифаҳо, объект, мавзӯъ, усулҳо, "
        "навоварии илмӣ, аҳамияти амалӣ, сохтори кор"
    ),
}
BACK_GOALS = {
    "conclusion": "хулосаҳои рақамгузорӣшуда, танҳо аз натиҷаҳои тасдиқшуда",
    "recommendations": "тавсияҳои амалӣ, ки бевосита аз хулосаҳо бармеоянд",
    "references": "рӯйхати адабиёт ба тартиби ГОСТ Р 7.0.5-2008",
    "appendices": "замимаҳо: протоколи санҷиш, пайдоиши маълумотҳо, луғати истилоҳот",
}


def chapter_map(work_type: str, n_chapters: int | None = None) -> dict:
    """Возвращает набор глав для данного типа работы."""
    if work_type == "course" or n_chapters == 2:
        return {k: v for k, v in COURSE_CHAPTERS.items() if k <= (n_chapters or 2)}
    n = n_chapters or 4
    return {k: v for k, v in CHAPTERS.items() if k <= n}


def build_outline(
    work_type: str = "diploma",
    n_chapters: int | None = None,
    with_appendices: bool = True,
) -> list[SectionSpec]:
    """Полный список разделов работы в правильном порядке с номерами."""
    outline: list[SectionSpec] = []

    # ---------------------------------------------------------------- фронт
    for sid, tg, ru in FRONT:
        is_intro = sid == "introduction"
        outline.append(
            SectionSpec(
                id=sid,
                kind="front",
                level=0,
                title_tg=tg,
                title_ru=ru,
                number="",
                numbered=False,
                required=True,
                target_words=TARGET_WORDS.get(sid, 200),
                goal=FRONT_GOALS.get(sid, ""),
            )
        )
        _ = is_intro

    # ---------------------------------------------------------------- главы
    for num, (tg, ru, paras) in sorted(chapter_map(work_type, n_chapters).items()):
        children: list[SectionSpec] = []
        for idx, (pid, ptg, pru, pgoal) in enumerate(paras, start=1):
            children.append(
                SectionSpec(
                    id=pid,
                    kind="body",
                    level=2,
                    title_tg=ptg,
                    title_ru=pru,
                    number=f"{num}.{idx}",
                    numbered=True,
                    required=True,
                    target_words=TARGET_WORDS.get(pid, 500),
                    goal=pgoal,
                )
            )
        outline.append(
            SectionSpec(
                id=f"ch{num}",
                kind="body",
                level=1,
                title_tg=tg,
                title_ru=ru,
                number=str(num),
                numbered=True,
                required=True,
                target_words=sum(c.target_words for c in children),
                goal=f"боби {num}: {ru.lower()}",
                children=children,
            )
        )

    # ------------------------------------------------------------------ зад
    for sid, tg, ru in BACK:
        if sid == "appendices" and not with_appendices:
            continue
        outline.append(
            SectionSpec(
                id=sid,
                kind="back",
                level=0,
                title_tg=tg,
                title_ru=ru,
                number="",
                numbered=False,
                required=True,
                target_words=TARGET_WORDS.get(sid, 300),
                goal=BACK_GOALS.get(sid, ""),
            )
        )
    return outline


def flatten(outline: list[SectionSpec]) -> list[SectionSpec]:
    out: list[SectionSpec] = []
    for s in outline:
        out.append(s)
        out.extend(s.children)
    return out


def outline_to_plan(outline: list[SectionSpec], topic: Topic) -> Plan:
    """Преобразует структуру в ``Plan`` конвейера (шаг 2)."""
    sections: list[SectionPlan] = []
    for s in outline:
        sections.append(
            SectionPlan(
                id=s.id,
                title=s.heading,
                level=s.level,
                kind=s.kind,
                goal=s.goal,
                target_words=s.target_words,
                children=[
                    SectionPlan(
                        id=c.id,
                        title=c.heading,
                        level=c.level,
                        kind=c.kind,
                        goal=c.goal,
                        target_words=c.target_words,
                    )
                    for c in s.children
                ],
            )
        )
    return Plan(topic=topic, sections=sections)


# --------------------------------------------------------------------------- #
# Нумерация рисунков и таблиц
# --------------------------------------------------------------------------- #


def next_figure_number(
    counters: dict[str, int],
    chapter: str | int,
    numbering: str = "per_chapter",
) -> str:
    """Возвращает следующий номер рисунка/таблицы: «2.3» или «7»."""
    if numbering == "continuous":
        counters["total"] = counters.get("total", 0) + 1
        return str(counters["total"])
    key = str(chapter) or "0"
    counters[key] = counters.get(key, 0) + 1
    return f"{key}.{counters[key]}"
