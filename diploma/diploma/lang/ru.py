"""Русский язык оформления (для двуязычной аннотации и русскоязычных работ)."""

from __future__ import annotations

from .base import Language

TERMS_RU: dict[str, str] = {
    "title_page": "Титульный лист",
    "contents": "Содержание",
    "annotation": "Аннотация",
    "keywords": "Ключевые слова",
    "abbreviations": "Список сокращений",
    "introduction": "Введение",
    "chapter": "Глава",
    "chapter_gen": "Глава",
    "part": "Часть",
    "literature_review": "Обзор литературы",
    "materials_methods": "Материалы и методы исследования",
    "results": "Результаты исследования",
    "discussion": "Обсуждение результатов",
    "conclusion": "Заключение",
    "recommendations": "Практические рекомендации",
    "references": "Список использованных источников",
    "appendix": "Приложение",
    "appendix_gen": "Приложение",
    "figure": "Рисунок",
    "figure_ref": "рис.",
    "table": "Таблица",
    "table_ref": "табл.",
    "formula": "Формула",
    "list_of_figures": "Список рисунков",
    "list_of_tables": "Список таблиц",
    "relevance": "Актуальность темы",
    "goal": "Цель исследования",
    "objectives": "Задачи исследования",
    "object": "Объект исследования",
    "subject": "Предмет исследования",
    "methods": "Методы исследования",
    "novelty": "Научная новизна",
    "practical_value": "Практическая значимость",
    "study_design": "Дизайн исследования",
    "inclusion_criteria": "Критерии включения",
    "exclusion_criteria": "Критерии исключения",
    "sample": "Выборка",
    "statistical_methods": "Методы статистической обработки",
    "ethics": "Этика исследования",
    "ethics_committee": "Этический комитет",
    "consent_note": "От всех пациентов получено письменное информированное согласие",
    "source": "Источник",
    "own_data": "Данные автора",
    "missing_data": "Данные отсутствуют",
    "note": "Примечание",
    "figure_note": "Примечание к рисунку",
    "table_note": "Примечание к таблице",
    "teaching_example": "Учебный пример: данные смоделированы",
    "verification": "Протокол проверки источников",
    "guidelines_note": "Клинические рекомендации",
    "no_data_placeholder": "Данные отсутствуют",
    "data_provenance": "Происхождение данных рисунков",
    "ministry": "Министерство",
    "university": "Университет",
    "faculty": "Факультет",
    "chair": "Кафедра",
    "topic": "Тема",
    "performed_by": "Выполнил",
    "supervisor": "Научный руководитель",
    "reviewer": "Рецензент",
    "head_of_chair": "Заведующий кафедрой",
    "student": "Студент",
    "group": "Группа",
    "city_year": "Город — год",
    "defense_date": "Дата защиты",
    "grade": "Оценка",
    "work_type_course": "КУРСОВАЯ РАБОТА",
    "work_type_diploma": "ВЫПУСКНАЯ КВАЛИФИКАЦИОННАЯ РАБОТА",
    "work_type_master": "МАГИСТЕРСКАЯ ДИССЕРТАЦИЯ",
    "and_others": "и др.",
    "total": "Всего",
    "group_word": "Группа",
    "patients": "пациент",
    "male": "мужчина",
    "female": "женщина",
    "age": "возраст",
    "mean": "среднее",
}

MONTHS_RU = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


class Russian(Language):
    code = "ru"
    name = "Русский"

    def __init__(self) -> None:
        super().__init__(
            code=self.code,
            name=self.name,
            terms=TERMS_RU,
            months=MONTHS_RU,
            decimal_separator=",",
            thousands_separator=" ",
        )

    def plural(self, n: int, forms: tuple[str, str, str]) -> str:
        n = abs(int(n)) % 100
        n1 = n % 10
        if 10 < n < 20:
            return forms[2]
        if 1 < n1 < 5:
            return forms[1]
        if n1 == 1:
            return forms[0]
        return forms[2]
