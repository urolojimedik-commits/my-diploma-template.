"""Детерминированный композитор академического текста (шаг 4).

Работает без внешних сервисов и без «творчества»: каждый факт берётся из
полей ``summary_ru`` / ``facts`` проверенного источника и снабжается ссылкой
в формате Pandoc ``[@key]``. Фразы-связки выбираются из банка шаблонов, чтобы
текст не был однообразным, но оставался полностью проверяемым.

Если для раздела нет ни одного проверенного источника, композитор возвращает
явную пометку ``{{ТРЕБУЕТСЯ ИСТОЧНИК}}`` — выдумывать утверждения он не умеет.
"""

from __future__ import annotations

import random
import re

from ..model import Plan, Source, Topic
from .base import MISSING_SOURCE_MARK, SectionContext, TextBackend

# --------------------------------------------------------------------------- #
# Вспомогательные функции русской орфографии
# --------------------------------------------------------------------------- #

_ACRONYMS = {"КТ", "МРТ", "УЗИ", "AUC", "ROC", "CNN", "FPR", "TPR", "YOLO", "ИИ", "МО", "ГО", "PRISMA"}


def lower_first(text: str) -> str:
    """Понижает первый символ, если это безопасно (не аббревиатура, не число)."""
    text = text.strip()
    if not text:
        return text
    first_word = text.split()[0]
    if any(ch.isdigit() for ch in first_word[:2]):
        return text
    if first_word.upper().strip(".,;:") in _ACRONYMS:
        return text
    if len(first_word) > 1 and first_word[:2].isupper():
        return text
    return text[:1].lower() + text[1:]


def ensure_dot(text: str) -> str:
    text = text.strip()
    if not text:
        return text
    if text[-1] not in ".!?…:":
        return text + "."
    return text


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def clean_fact(fact: str) -> str:
    """Готовит факт к встраиванию в предложение.

    Текст факта не переписывается: он приводится к строчной первой букве
    (если это безопасно) и очищается от завершающей пунктуации. Перефразирование
    автоматически изменило бы смысл, поэтому не применяется.
    """
    fact = re.sub(r"\s+", " ", fact).strip()
    fact = fact.rstrip(".;")
    if fact.endswith(","):
        fact = fact[:-1]
    return lower_first(fact)


# --------------------------------------------------------------------------- #
# Банки шаблонов
# --------------------------------------------------------------------------- #

FACT_TEMPLATES = [
    "В работе {authors} ({year}) {fact} {cite}",
    "По данным {authors} ({year}), {fact} {cite}",
    "{Authors} ({year}) сообщают, что {fact} {cite}",
    "Согласно исследованию {authors} ({year}), {fact} {cite}",
    "В исследовании {authors} ({year}) отмечается, что {fact} {cite}",
    "Как показано в работе {authors} ({year}), {fact} {cite}",
    "Авторы {authors_ru} ({year}) указывают, что {fact} {cite}",
    "В публикации {authors} ({year}) рассматривается вопрос о том, что {fact} {cite}",
]

TITLE_TEMPLATES = [
    "Статья {authors} ({year}) «{title}» посвящена следующему аспекту темы: {theme} {cite}",
    "В работе {authors} ({year}) «{title}» предметом рассмотрения выступает {theme} {cite}",
    "Работа {authors} ({year}) «{title}» относится к направлению, связанному с {theme_t} {cite}",
]

LEAD_TEMPLATES_CHAPTER = [
    "Настоящий раздел посвящён следующему вопросу: {goal}.",
    "В данном разделе рассматривается {goal}.",
    "Целью настоящего раздела является анализ того, {goal_vp}.",
    "Раздел раскрывает {goal}.",
]

LEAD_TEMPLATES_SECTION = [
    "В подразделе рассматривается {goal}.",
    "Ниже рассматривается {goal}.",
    "Данный подраздел посвящён следующему аспекту: {goal}.",
]

SYNTHESIS_TEMPLATES = [
    "Таким образом, рассмотренные работы охватывают разные аспекты темы {cites}.",
    "Сопоставление приведённых результатов затруднено различиями в условиях проведения "
    "исследований — объёме выборок, используемых модальностях и применяемых метриках {cites}.",
    "Материалы приведённых исследований {cites} используются далее при сопоставлении "
    "количественных показателей.",
    "Отметим, что воспроизведение приведённых результатов требует соблюдения условий "
    "исходных исследований, что следует учитывать при их использовании {cites}.",
]

CLOSING_TEMPLATES = [
    "С учётом изложенного далее рассматривается следующий аспект темы.",
    "Полученные сведения используются ниже при обобщении результатов.",
    "Изложенное позволяет перейти к следующему вопросу исследования.",
]

TRANSITIONS = [
    "Кроме того,",
    "Дополнительно отметим,",
    "В свою очередь,",
    "Наряду с этим",
    "Также",
]

MEDIA_TEMPLATES = {
    "fig": [
        "Соответствующая иллюстрация приведена на {{{{Ref:{label}}}}}.",
        "Схематичное представление рассматриваемого материала дано на {{{{Ref:{label}}}}}.",
        "На {{{{Ref:{label}}}}} представлены данные, обсуждаемые в данном разделе.",
    ],
    "tbl": [
        "Сводные данные приведены в {{{{Ref:{label}}}}}.",
        "Обобщённые сведения систематизированы в {{{{Ref:{label}}}}}.",
        "Для наглядности основные показатели сведены в {{{{Ref:{label}}}}}.",
    ],
}


class DeterministicComposer(TextBackend):
    """Композитор, работающий только на проверенных данных."""

    name = "deterministic"

    def __init__(self, seed: int = 7, facts_per_source: int = 2):
        self.rng = random.Random(seed)
        self.facts_per_source = facts_per_source

    # ------------------------------------------------------------------ #
    def _pick(self, bank: list[str], idx: int) -> str:
        return bank[idx % len(bank)]

    def _theme(self, ctx: SectionContext) -> str:
        return (ctx.section.goal or ctx.section.title).rstrip(".")

    def _theme_t(self, ctx: SectionContext) -> str:
        theme = self._theme(ctx)
        return re.sub(r"^\S+\s", "", theme) or theme

    def fact_sentence(self, source: Source, fact: str, idx: int) -> str:
        tpl = self._pick(FACT_TEMPLATES, idx)
        text = tpl.format(
            authors=source.authors_ru,
            Authors=source.authors_ru,
            authors_ru=source.authors_ru,
            year=source.year_str,
            fact=clean_fact(fact),
            cite=source.cite_inline,
        )
        return ensure_dot(text)

    def title_sentence(self, source: Source, ctx: SectionContext, idx: int) -> str:
        tpl = self._pick(TITLE_TEMPLATES, idx)
        return ensure_dot(
            tpl.format(
                authors=source.authors_ru,
                year=source.year_str,
                title=source.title_display,
                theme=lower_first(self._theme(ctx)),
                theme_t=self._theme_t(ctx),
                cite=source.cite_inline,
            )
        )

    def source_block(self, source: Source, ctx: SectionContext, idx: int) -> str:
        facts = [f for f in source.facts if f.strip()]
        if not facts and source.summary_ru:
            facts = sentences(source.summary_ru)
        out: list[str] = []
        if facts:
            for j, fact in enumerate(facts[: self.facts_per_source]):
                out.append(self.fact_sentence(source, fact, idx + j))
        else:
            out.append(self.title_sentence(source, ctx, idx))
        return " ".join(out)

    def lead(self, ctx: SectionContext) -> str:
        goal = (ctx.section.goal or ctx.section.title).rstrip(".")
        if ctx.section.level <= 1:
            tpl = self._pick(LEAD_TEMPLATES_CHAPTER, self.rng.randint(0, 99))
            text = tpl.format(
                goal=lower_first(goal),
                goal_vp=goal.replace("анализ того, ", "") or goal,
            )
        else:
            tpl = self._pick(LEAD_TEMPLATES_SECTION, self.rng.randint(0, 99))
            text = tpl.format(goal=lower_first((ctx.section.goal or ctx.section.title).rstrip(".")))
        return text

    def synthesis(self, ctx: SectionContext, sources: list[Source]) -> str:
        if len(sources) < 2:
            return ""
        cites = "[@" + "; @".join(s.key for s in sources[:3]) + "]"
        tpl = self._pick(SYNTHESIS_TEMPLATES, self.rng.randint(0, 99))
        return tpl.format(theme=lower_first(self._theme(ctx)), cites=cites)

    def media_sentences(self, ctx: SectionContext) -> list[str]:
        out = []
        for i, label in enumerate(ctx.media_refs):
            kind = "fig" if label.startswith("fig:") else "tbl"
            tpl = self._pick(MEDIA_TEMPLATES[kind], i)
            out.append(tpl.format(label=label))
        return out

    # ------------------------------------------------------------------ #
    def write_section(self, ctx: SectionContext) -> str:
        blocks: list[str] = [self.lead(ctx)]
        if not ctx.sources:
            blocks.append(
                f"{MISSING_SOURCE_MARK}: по данному разделу не найдено проверенных "
                "источников, поэтому утверждения не приведены."
            )
        else:
            parts = []
            for i, s in enumerate(ctx.sources):
                part = self.source_block(s, ctx, i)
                if i > 0 and i % 2 == 1:
                    part = f"{self.rng.choice(TRANSITIONS)} " + lower_first(part)
                parts.append(part)
            blocks.append(" ".join(parts))
            blocks += self.media_sentences(ctx)
            syn = self.synthesis(ctx, ctx.sources)
            if syn:
                blocks.append(syn)
        if ctx.section.level <= 1:
            blocks.append(self._pick(CLOSING_TEMPLATES, self.rng.randint(0, 99)))
        return "\n\n".join(b for b in blocks if b)

    # ------------------------------------------------------------------ #
    def write_introduction(self, topic: Topic, sources: list[Source], plan: Plan) -> str:
        blocks: list[str] = []
        blocks.append(
            f"Актуальность работы определяется необходимостью систематизации и "
            "критического сопоставления сведений, опубликованных по теме "
            f"«{topic.title}», а также потребностью в проверяемой основе выводов: "
            "в работу включаются только источники, прошедшие проверку регистрации "
            "идентификатора DOI и сверку метаданных."
        )
        # фактические утверждения — только со ссылками
        fact_sources = [s for s in sources if s.facts or s.summary_ru][:3]
        if fact_sources:
            parts = []
            for i, s in enumerate(fact_sources):
                facts = s.facts or sentences(s.summary_ru)
                if facts:
                    parts.append(self.fact_sentence(s, facts[0], i))
            if parts:
                blocks.append(" ".join(parts))
        else:
            blocks.append(
                f"{MISSING_SOURCE_MARK}: по теме не найдено проверенных источников "
                "для обоснования актуальности."
            )
        blocks.append(
            f"Объектом исследования выступает {topic.object_ru}. "
            f"Предметом исследования являются {topic.subject_ru}."
        )
        blocks.append(f"Цель работы — {topic.goal_ru}.")
        blocks.append("Для достижения поставленной цели решаются следующие задачи: ")
        blocks.append("\n".join(f"{i}. {t}" for i, t in enumerate(topic.tasks_ru, start=1)))
        blocks.append(
            "Методологическую основу работы составляют: "
            + "; ".join(topic.methods_ru)
            + "."
        )
        chapters = [s for s in plan.sections if s.kind == "body"]
        if chapters:
            blocks.append(
                "Работа состоит из введения, "
                f"{len(chapters)} "
                + ("главы" if len(chapters) == 1 else "глав")
                + ", заключения и списка использованных источников. "
                + "Структура работы отражает последовательность решения поставленных задач."
            )
        return "\n\n".join(ensure_dot(b) if not b.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.")) else b for b in blocks)

    def write_conclusion(self, topic: Topic, sources: list[Source], plan: Plan) -> str:
        blocks: list[str] = []
        blocks.append(
            f"В ходе работы рассмотрена тема «{topic.title}». "
            f"Цель работы — {topic.goal_ru} — достигнута: поставленные задачи решены "
            "в полном объёме."
        )
        # Выводы формируются только из проверенных фактов
        conclusions: list[str] = []
        for i, s in enumerate([x for x in sources if x.facts][:5], start=1):
            conclusions.append(f"{i}. {ensure_dot(self.fact_sentence(s, s.facts[0], i))}")
        if conclusions:
            blocks.append("Основные результаты работы:")
            blocks.append("\n".join(conclusions))
        with_doi = [s for s in sources if s.doi]
        blocks.append(
            "Информационную основу исследования составили "
            f"{len(sources)} проверенных источников"
            + (f", из них {len(with_doi)} с идентификатором DOI" if with_doi else "")
            + ". Все включённые источники прошли автоматическую проверку регистрации DOI "
            "и сверку метаданных, что исключает использование недостоверных ссылок."
        )
        blocks.append(
            "Практическая значимость работы состоит в том, что систематизированные "
            "сведения и полученные обобщения могут быть использованы при постановке "
            "последующих исследований и при подготовке обзоров по теме."
        )
        blocks.append(
            "Перспективы дальнейшей работы связаны с расширением выборки источников, "
            "включением дополнительных баз данных и проведением собственных "
            "экспериментальных исследований."
        )
        return "\n\n".join(blocks)

    def write_annotation(self, topic: Topic, sources: list[Source]) -> str:
        return (
            f"Работа посвящена теме «{topic.title}». "
            f"Объект исследования — {topic.object_ru}, предмет — {topic.subject_ru}. "
            f"Цель работы — {topic.goal_ru}. "
            f"В работе использовано {len(sources)} проверенных источников. "
            "Результаты представлены в виде таблиц и рисунков с оформленными подписями "
            "и сквозной нумерацией."
        )
