"""Шаг 2. Построение плана и структуры глав.

План строится по типовой для российских вузов схеме (введение — главы с
параграфами — заключение — список источников). Названия глав и параграфов
формируются из частей названия темы (процесс / метод / предметная область),
поэтому заголовки остаются грамматически правильными русскими фразами.
"""

from __future__ import annotations

import re

from .model import Plan, SectionPlan, Source, Topic

STOP = {
    "и", "в", "во", "на", "за", "по", "для", "при", "с", "со", "к", "от", "до", "из",
    "у", "о", "об", "а", "но", "как", "что", "это", "не", "или", "же", "бы", "ли",
    "теме", "тема", "работы", "работа", "работе", "основе", "данных", "данные", "том",
}


def _short(phrase: str, words: int = 6) -> str:
    """Убирает служебный «хвост» названия, не обрывая фразу на полуслове."""
    text = str(phrase).strip().rstrip(".,;:")
    return text


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"\W+", (text or "").lower()) if len(t) > 2} - STOP


def build_plan(topic: Topic, work_type: str = "diploma") -> Plan:
    """Формирует структуру работы."""
    n_chapters = 2 if work_type == "course" else 3
    domain = topic.title_domain or topic.title
    method = topic.title_method
    process = (topic.title_process or "Исследование").lower()
    domain_short = _short(domain, 6)
    method_phrase = f"{process} {method}".strip() if method else topic.title

    sections: list[SectionPlan] = []

    sections.append(
        SectionPlan(
            id="intro",
            title="Введение",
            level=1,
            kind="front",
            goal="обоснование актуальности темы, формулировка объекта, предмета, цели и задач исследования",
            target_words=700,
        )
    )

    # Глава 1 — теоретическая часть
    ch1_kids = [
        SectionPlan(
            id="ch1-1",
            title=f"Современное состояние проблемы в области {domain}",
            level=2,
            goal=f"современное состояние исследований в области {domain}",
            target_words=900,
        ),
        SectionPlan(
            id="ch1-2",
            title=f"{method_phrase[0].upper() + method_phrase[1:] if method_phrase else 'Методы'}: обзор и классификация",
            level=2,
            goal=f"методы и подходы, применяемые в рамках темы: {method_phrase or topic.title}",
            target_words=900,
        ),
        SectionPlan(
            id="ch1-3",
            title="Критерии и показатели оценки результатов",
            level=2,
            goal="показатели и критерии, по которым оцениваются результаты исследований",
            target_words=700,
        ),
    ]
    sections.append(
        SectionPlan(
            id="ch1",
            title=f"Теоретические и методологические основы {domain_short}",
            level=1,
            kind="body",
            goal=f"теоретические и методологические основы {domain}",
            children=ch1_kids,
            target_words=2500,
        )
    )

    # Глава 2 — аналитическая часть (здесь живут таблицы и графики)
    ch2_kids = [
        SectionPlan(
            id="ch2-1",
            title="Характеристика отобранных источников и данных",
            level=2,
            goal="состав и характеристики отобранных источников, данные которых используются далее",
            target_words=700,
        ),
        SectionPlan(
            id="ch2-2",
            title="Сравнительный анализ количественных показателей",
            level=2,
            goal=f"количественные показатели, приведённые в отобранных исследованиях по направлению {domain}",
            target_words=1000,
        ),
        SectionPlan(
            id="ch2-3",
            title="Обсуждение результатов и ограничения",
            level=2,
            goal="обсуждение полученных результатов и их ограничения",
            target_words=800,
        ),
    ]
    sections.append(
        SectionPlan(
            id="ch2",
            title="Аналитическое исследование и сопоставление результатов",
            level=1,
            kind="body",
            goal="анализ и сопоставление количественных результатов отобранных исследований",
            children=ch2_kids,
            target_words=2500,
        )
    )

    # Глава 3 — практическая часть (только для диплома)
    if n_chapters >= 3:
        ch3_kids = [
            SectionPlan(
                id="ch3-1",
                title="Практические рекомендации по результатам исследования",
                level=2,
                goal="практические рекомендации, следующие из результатов анализа",
                target_words=700,
            ),
            SectionPlan(
                id="ch3-2",
                title="Ограничения исследования и направления дальнейшей работы",
                level=2,
                goal="ограничения проведённого анализа и возможные направления дальнейшей работы",
                target_words=600,
            ),
        ]
        sections.append(
            SectionPlan(
                id="ch3",
                title="Практическая значимость и направления развития",
                level=1,
                kind="body",
                goal="практическая значимость результатов и направления их развития",
                children=ch3_kids,
                target_words=1300,
            )
        )

    sections.append(
        SectionPlan(
            id="concl",
            title="Заключение",
            level=1,
            kind="back",
            goal="основные выводы по результатам работы",
            target_words=600,
        )
    )
    sections.append(
        SectionPlan(
            id="refs",
            title="Список использованных источников",
            level=1,
            kind="back",
            goal="перечень проверенных источников",
            target_words=0,
        )
    )
    return Plan(topic=topic, sections=sections)


def _section_weight(section: SectionPlan, source: Source) -> float:
    """Насколько источник подходит разделу (пересечение терминов)."""
    sec_tokens = _tokens(section.title) | _tokens(section.goal)
    if not sec_tokens:
        return 0.0
    src_tokens = _tokens(source.title) | _tokens(source.title_ru) | _tokens(
        source.summary_ru
    ) | _tokens(" ".join(source.facts)) | _tokens(" ".join(source.tags))
    if not src_tokens:
        return 0.0
    return len(sec_tokens & src_tokens) / len(sec_tokens)


def allocate_sources(plan: Plan, sources: list[Source]) -> dict[str, list[Source]]:
    """Распределяет источники по разделам плана.

    Сначала каждый источник получает раздел с максимальным пересечением
    терминов; затем выравниваем загрузку, чтобы ни один раздел не остался
    без материала, а перегруженные разделы отдали «хвост» соседним.
    """
    leaves = [
        s
        for s in plan.walk()
        if s.kind in {"front", "body", "back"} and not s.children and s.id != "refs"
    ]
    allocation: dict[str, list[Source]] = {s.id: [] for s in leaves}
    for src in sources:
        best = max(leaves, key=lambda s: _section_weight(s, src))
        allocation[best.id].append(src)

    per_section_max = max(1, -(-len(sources) // max(len(leaves), 1)) + 1)
    donors = sorted(allocation, key=lambda k: len(allocation[k]), reverse=True)
    for sec in leaves:
        if allocation[sec.id]:
            continue
        for donor in donors:
            if donor != sec.id and len(allocation[donor]) > 1:
                allocation[sec.id].append(allocation[donor].pop())
                break
    for donor in donors:
        while len(allocation[donor]) > per_section_max:
            receivers = sorted(
                (s.id for s in leaves if s.id != donor), key=lambda k: len(allocation[k])
            )
            if not receivers or len(allocation[receivers[0]]) >= per_section_max:
                break
            allocation[receivers[0]].append(allocation[donor].pop())

    for sec_id in allocation:
        allocation[sec_id].sort(key=lambda s: (-(s.year or 0), s.authors_ru))
    return allocation


def plan_to_markdown(plan: Plan) -> str:
    """Человекочитаемый план (используется и в веб-интерфейсе)."""
    lines = [f"# План работы: {plan.topic.title}", ""]
    chapter_no = 0
    for sec in plan.sections:
        if sec.kind == "body":
            chapter_no += 1
            lines.append(f"**Глава {chapter_no}. {sec.title}**")
            for j, child in enumerate(sec.children, start=1):
                lines.append(f"    {chapter_no}.{j} {child.title}")
        else:
            lines.append(f"**{sec.title}**")
    return "\n".join(lines) + "\n"
