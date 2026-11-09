"""
planner.py — генерация подробного плана и структуры глав из темы.

Логика: эвристика по ключевым словам темы + ГОСТ-структура российских ВУЗов.
Не использует LLM — детерминированный, воспроизводимый.
"""

from __future__ import annotations

import re
from typing import List, Dict

from .config import ProjectConfig, ChapterPlan, WorkType, FigureSpec, TableSpec


# Базовые ГОСТ-структуры по типу работы
WORK_STRUCTURES: Dict[str, Dict] = {
    "курсовая": {
        "pages_total": 30,
        "chapters": 2,
        "sections_per_chapter": 3,
        "sources_min": 20,
    },
    "диплом": {
        "pages_total": 70,
        "chapters": 3,
        "sections_per_chapter": 3,
        "sources_min": 40,
    },
    "вкр_бакалавр": {
        "pages_total": 60,
        "chapters": 3,
        "sections_per_chapter": 3,
        "sources_min": 35,
    },
    "магистерская": {
        "pages_total": 90,
        "chapters": 3,
        "sections_per_chapter": 4,
        "sources_min": 60,
    },
    "статья": {
        "pages_total": 12,
        "chapters": 4,  # введение, методы, результаты, обсуждение
        "sections_per_chapter": 2,
        "sources_min": 15,
    },
}

# Шаблоны глав в зависимости от дисциплинарных кластеров
DISCIPLINE_TEMPLATES = {
    "it": {
        "keywords": ["цифровизац", "информацион", "программ", "алгоритм", "машинное обучение", "ии", "база данных", "веб", "мобильн", "кибербезопас"],
        "ch1_title": "Теоретические основы и анализ предметной области",
        "ch1_subs": [
            "Понятие и сущность исследуемого явления в контексте дисциплины",
            "Обзор существующих подходов, моделей и технологий",
            "Нормативно-правовая база и стандарты",
            "Зарубежный и отечественный опыт",
        ],
        "ch2_title": "Анализ объекта исследования и постановка задачи",
        "ch2_subs": [
            "Характеристика объекта исследования (предприятие/система/процесс)",
            "Анализ текущего состояния и выявление проблем",
            "Сравнительный анализ аналогов и обоснование выбора решения",
            "Постановка требований и техническое задание",
        ],
        "ch3_title": "Проектирование и реализация решения",
        "ch3_subs": [
            "Архитектура и моделирование системы",
            "Разработка алгоритмов и программная реализация",
            "Тестирование, внедрение и оценка эффективности",
            "Рекомендации и перспективы развития",
        ],
    },
    "economy": {
        "keywords": ["эконом", "финанс", "менеджмент", "маркетинг", "бизнес", "рынок", "инвестиц", "банк", "аудит", "бухгалтер"],
        "ch1_title": "Теоретико-методологические основы исследования",
        "ch1_subs": [
            "Экономическая сущность и классификация исследуемого явления",
            "Методы и показатели оценки эффективности",
            "Факторы, влияющие на исследуемый процесс",
        ],
        "ch2_title": "Анализ финансово-хозяйственной деятельности объекта исследования",
        "ch2_subs": [
            "Организационно-экономическая характеристика организации",
            "Анализ финансового состояния и ключевых показателей",
            "Диагностика проблем и оценка рисков",
        ],
        "ch3_title": "Разработка мероприятий по совершенствованию",
        "ch3_subs": [
            "Обоснование предлагаемых мероприятий",
            "Экономическое обоснование и расчёт эффективности",
            "План внедрения и оценка рисков реализации",
        ],
    },
    "law": {
        "keywords": ["прав", "юридич", "законодательств", "регулировани", "договор", "ответственност", "конституц"],
        "ch1_title": "Теоретико-правовые основы исследования",
        "ch1_subs": [
            "Понятие, признаки и классификация",
            "Историко-правовой анализ",
            "Нормативно-правовое регулирование",
        ],
        "ch2_title": "Проблемы правового регулирования и правоприменительная практика",
        "ch2_subs": [
            "Анализ действующего законодательства",
            "Судебная и административная практика",
            "Сравнительно-правовой анализ",
        ],
        "ch3_title": "Пути совершенствования законодательства и практики",
        "ch3_subs": [
            "Выявленные пробелы и коллизии",
            "Предложения по изменению нормативных актов",
            "Модель внедрения и ожидаемый эффект",
        ],
    },
    "pedagogy": {
        "keywords": ["педагог", "образован", "обучен", "воспитан", "методика", "учебн", "школьн", "студент"],
        "ch1_title": "Теоретические основы исследования",
        "ch1_subs": [
            "Психолого-педагогические аспекты проблемы",
            "Анализ ФГОС и образовательных программ",
            "Обзор методических подходов",
        ],
        "ch2_title": "Опытно-экспериментальная работа",
        "ch2_subs": [
            "Констатирующий этап: диагностика уровня",
            "Формирующий этап: реализация методики",
            "Контрольный этап: оценка результатов",
        ],
        "ch3_title": "Методические рекомендации",
        "ch3_subs": [
            "Разработка методического обеспечения",
            "Апробация и оценка эффективности",
            "Рекомендации педагогам и перспективы",
        ],
    },
    "default": {
        "ch1_title": "Теоретические аспекты темы исследования",
        "ch1_subs": [
            "Сущность, понятие и классификация",
            "Факторы и условия развития",
            "Нормативно-правовые и методологические основы",
            "Зарубежный и отечественный опыт",
        ],
        "ch2_title": "Анализ современного состояния объекта исследования",
        "ch2_subs": [
            "Характеристика объекта исследования",
            "Анализ текущего состояния и динамики показателей",
            "Выявление проблем и причинно-следственный анализ",
        ],
        "ch3_title": "Разработка рекомендаций и оценка их эффективности",
        "ch3_subs": [
            "Обоснование направлений совершенствования",
            "Разработка практических мероприятий",
            "Оценка социально-экономической эффективности",
            "План внедрения и управление рисками",
        ],
    },
}


def detect_discipline_cluster(topic: str, discipline: str) -> str:
    text = (topic + " " + discipline).lower()
    for cluster, data in DISCIPLINE_TEMPLATES.items():
        if cluster == "default":
            continue
        for kw in data.get("keywords", []):
            if kw in text:
                return cluster
    return "default"


def slugify(text: str) -> str:
    # транслит для id
    import re

    t = text.lower()
    t = re.sub(r"[^a-zа-я0-9]+", "_", t)
    return t.strip("_")[:30]


class Planner:
    """Генератор плана работы."""

    def __init__(self, config: ProjectConfig):
        self.config = config
        self.cluster = detect_discipline_cluster(config.topic, config.discipline)
        self.template = DISCIPLINE_TEMPLATES.get(self.cluster, DISCIPLINE_TEMPLATES["default"])
        self.work_profile = WORK_STRUCTURES.get(config.work_type.value, WORK_STRUCTURES["диплом"])

    def generate(self) -> ProjectConfig:
        """Заполняет config.plan и возвращает его."""
        topic = self.config.topic.strip()
        # Автозаполнение цели/задач если пустые
        if not self.config.goal:
            self.config.goal = self._make_goal(topic)
        if not self.config.tasks:
            self.config.tasks = self._make_tasks(topic)
        if not self.config.object_research:
            self.config.object_research = self._make_object(topic)
        if not self.config.subject_research:
            self.config.subject_research = self._make_subject(topic)
        if not self.config.methods:
            self.config.methods = [
                "анализ научной литературы и нормативно-правовых актов",
                "сравнительный анализ",
                "системный анализ",
                "статистический анализ",
                "моделирование",
                "эмпирическое исследование (наблюдение, опрос, тестирование)",
            ]
        if not self.config.keywords:
            self.config.keywords = self._extract_keywords(topic)

        self.config.plan = self._build_plan()
        return self.config

    def _make_goal(self, topic: str) -> str:
        return (
            f"Цель работы — комплексное исследование темы «{topic}», "
            f"выявление ключевых проблем и разработка практических рекомендаций "
            f"по совершенствованию исследуемого объекта."
        )

    def _make_tasks(self, topic: str) -> list[str]:
        return [
            f"Раскрыть теоретические основы по теме «{topic}»",
            "Проанализировать нормативно-правовую базу и научные подходы",
            "Исследовать современное состояние объекта на примере конкретной организации/процесса",
            "Выявить проблемы и факторы, влияющие на эффективность",
            "Разработать комплекс мероприятий по совершенствованию",
            "Обосновать социально-экономическую эффективность предложенных решений",
        ]

    def _make_object(self, topic: str) -> str:
        # эвристика: если в теме есть "на примере", берём его
        m = re.search(r"на примере (.+)", topic, re.IGNORECASE)
        if m:
            return m.group(1).strip(" .«»\"")
        return "общественные отношения / процессы, связанные с предметом исследования"

    def _make_subject(self, topic: str) -> str:
        return f"теоретические и практические аспекты темы «{topic}»"

    def _extract_keywords(self, topic: str) -> list[str]:
        stop = {"и", "в", "на", "по", "для", "с", "к", "о", "об", "из", "за", "от", "как", "при", "их", "его", "ее"}
        words = re.findall(r"[а-яА-Яa-zA-Z]{3,}", topic.lower())
        kw = [w for w in words if w not in stop]
        # уникальные, до 5
        seen = []
        for w in kw:
            if w not in seen:
                seen.append(w)
        return seen[:5]

    def _build_plan(self) -> List[ChapterPlan]:
        plan: List[ChapterPlan] = []

        # Титульный, содержание, введение — служебные
        plan.append(
            ChapterPlan(
                number="",
                title="Титульный лист",
                description="ГОСТ оформление, реквизиты вуза, ФИО, руководитель",
                pages_target=1,
            )
        )
        plan.append(
            ChapterPlan(
                number="",
                title="Содержание",
                description="Автоматически генерируется",
                pages_target=1,
            )
        )
        # Введение
        plan.append(
            ChapterPlan(
                number="Введение",
                title="Введение",
                description=(
                    f"Актуальность темы «{self.config.topic}», степень научной разработанности, "
                    "цель, задачи, объект, предмет, методы, практическая значимость, структура работы. "
                    "Объём 3–4 стр."
                ),
                pages_target=3,
                keywords=self.config.keywords,
            )
        )

        # Главы 1-3 (по профилю)
        n_chapters = self.work_profile["chapters"]
        titles = [
            self.template["ch1_title"],
            self.template["ch2_title"],
            self.template["ch3_title"],
        ]
        subs_list = [
            self.template["ch1_subs"],
            self.template["ch2_subs"],
            self.template["ch3_subs"],
        ]
        # если магистерская — 4я глава не нужна, но можно расширить
        for i in range(n_chapters):
            ch_title = titles[i] if i < len(titles) else f"Глава {i+1}"
            subs_raw = subs_list[i] if i < len(subs_list) else subs_list[-1]
            # ограничим по sections_per_chapter
            max_subs = self.work_profile["sections_per_chapter"]
            subs_raw = subs_raw[:max_subs]

            subsections = []
            for j, sub_title in enumerate(subs_raw, 1):
                # Для каждой подглавы предложим фигуры/таблицы
                figs = []
                tbls = []
                # Эвристика: глава 2 — больше графиков
                if i == 1 and j == 2:
                    figs.append(
                        FigureSpec(
                            id=f"fig_{i+1}_{j}",
                            caption="Динамика ключевых показателей объекта исследования",
                            filename=f"fig_{i+1}_{j}_dynamics.png",
                            source_note="Источник: составлено автором по данным Росстата / отчётности организации",
                            synthetic=False,
                        )
                    )
                    tbls.append(
                        TableSpec(
                            id=f"tbl_{i+1}_{j}",
                            caption="Сравнительная характеристика подходов / показателей",
                            headers=["Показатель", "2022 г.", "2023 г.", "2024 г.", "Темп роста, %"],
                            rows=[
                                ["Показатель 1", "120", "135", "142", "118,3"],
                                ["Показатель 2", "85", "90", "97", "114,1"],
                                ["Показатель 3", "45", "48", "52", "115,6"],
                            ],
                            source_note="Источник: расчёты автора",
                            synthetic=True,
                        )
                    )
                if i == 2 and j == 2:
                    figs.append(
                        FigureSpec(
                            id=f"fig_{i+1}_{j}_eff",
                            caption="Прогноз эффективности предлагаемых мероприятий",
                            filename=f"fig_{i+1}_{j}_forecast.png",
                            source_note="Источник: учебный пример, данные условные",
                            synthetic=True,
                        )
                    )

                subsections.append(
                    ChapterPlan(
                        number=f"{i+1}.{j}",
                        title=sub_title,
                        description=f"Раскрытие вопроса: {sub_title.lower()}. Требуется ссылки на 3–5 источников.",
                        pages_target=5,
                        sources_needed=4,
                        figures=figs,
                        tables=tbls,
                        keywords=self.config.keywords,
                    )
                )

            plan.append(
                ChapterPlan(
                    number=str(i + 1),
                    title=ch_title,
                    description=f"Цель главы — {ch_title.lower()}. Объём 15–20 стр.",
                    pages_target=18,
                    subsections=subsections,
                    sources_needed=12,
                    keywords=self.config.keywords,
                )
            )

        # Заключение
        plan.append(
            ChapterPlan(
                number="Заключение",
                title="Заключение",
                description="Краткие выводы по каждой главе (по 3–4 тезиса), достижение цели, подтверждение гипотезы, перспективы. 3–4 стр.",
                pages_target=3,
            )
        )
        # Список литературы
        plan.append(
            ChapterPlan(
                number="",
                title="Список использованных источников",
                description=f"Не менее {self.work_profile['sources_min']} источников, ГОСТ Р 7.0.5-2018, сортировка по алфавиту.",
                pages_target=4,
                sources_needed=self.work_profile["sources_min"],
            )
        )
        # Приложения
        plan.append(
            ChapterPlan(
                number="",
                title="Приложения",
                description="Анкеты, расчёты, акты внедрения, листинги кода (при наличии).",
                pages_target=5,
            )
        )

        return plan

    def to_markdown(self) -> str:
        """Человекочитаемый план Markdown."""
        lines = [f"# План работы: «{self.config.topic}»", ""]
        lines.append(f"**Тип:** {self.config.work_type.value} | **Дисциплина:** {self.config.discipline}")
        lines.append(f"**Кластер:** {self.cluster} | **Объём:** ~{self.work_profile['pages_total']} стр.")
        lines.append("")
        lines.append(f"**Цель:** {self.config.goal}")
        lines.append("")
        lines.append("**Задачи:**")
        for i, t in enumerate(self.config.tasks, 1):
            lines.append(f"{i}. {t}")
        lines.append("")
        lines.append(f"**Объект:** {self.config.object_research}")
        lines.append(f"**Предмет:** {self.config.subject_research}")
        lines.append("")
        lines.append("## Содержание (оглавление)")
        lines.append("")
        for ch in self.config.plan:
            if ch.number in ("", "Введение", "Заключение"):
                lines.append(f"- **{ch.title}** — {ch.description}")
            elif ch.number.isdigit():
                lines.append(f"- **Глава {ch.number}. {ch.title}** ({ch.pages_target} стр.)")
                for sub in ch.subsections:
                    lines.append(f"  - {sub.number} {sub.title}")
                    if sub.figures:
                        for f in sub.figures:
                            lines.append(f"    - 📊 Рисунок: {f.caption} `({f.filename})`")
                    if sub.tables:
                        for t in sub.tables:
                            lines.append(f"    - 📋 Таблица: {t.caption}")
            else:
                lines.append(f"- **{ch.title}** — {ch.description}")
        lines.append("")
        lines.append(f"**Методы:** {', '.join(self.config.methods)}")
        lines.append(f"**Ключевые слова:** {', '.join(self.config.keywords)}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "topic": self.config.topic,
            "work_type": self.config.work_type.value,
            "discipline": self.config.discipline,
            "cluster": self.cluster,
            "goal": self.config.goal,
            "tasks": self.config.tasks,
            "object": self.config.object_research,
            "subject": self.config.subject_research,
            "methods": self.config.methods,
            "keywords": self.config.keywords,
            "plan": [
                {
                    "number": ch.number,
                    "title": ch.title,
                    "description": ch.description,
                    "pages": ch.pages_target,
                    "subsections": [
                        {"number": s.number, "title": s.title, "description": s.description} for s in ch.subsections
                    ],
                }
                for ch in self.config.plan
            ],
        }

