"""Таджикский язык оформления (тоҷикӣ, кириллица).

Терминология сверена с устоявшейся таджикской медицинской и академической
практикой. Специфичные буквы таджикского алфавита (Ғ Ӣ Қ Ӯ Ҳ Ҷ) поддерживаются
шрифтами DejaVu (PDF) и Times New Roman (Word) — проверено.
"""

from __future__ import annotations

from .base import Language

TERMS_TG: dict[str, str] = {
    # структура работы
    "title_page": "Варақи унвонӣ",
    "contents": "Мундариҷа",
    "annotation": "Аннотатсия",
    "keywords": "Калимаҳои калидӣ",
    "abbreviations": "Рӯйхати ихтисораҳо",
    "introduction": "Муқаддима",
    "chapter": "Боб",
    "chapter_gen": "Боби",
    "part": "Қисм",
    "literature_review": "Баррасии адабиёт",
    "materials_methods": "Мавод ва усулҳои таҳқиқот",
    "results": "Натиҷаҳои таҳқиқот",
    "discussion": "Муҳокимаи натиҷаҳо",
    "conclusion": "Хулоса",
    "recommendations": "Тавсияҳои амалӣ",
    "references": "Рӯйхати адабиёт",
    "appendix": "Замима",
    "appendix_gen": "Замимаи",
    # объекты
    "figure": "Расм",
    "figure_ref": "расми",
    "table": "Ҷадвал",
    "table_ref": "ҷадвали",
    "formula": "Формула",
    "list_of_figures": "Рӯйхати расмҳо",
    "list_of_tables": "Рӯйхати ҷадвалҳо",
    # введение и методы
    "relevance": "Аҳамияти мавзӯъ",
    "goal": "Мақсади таҳқиқот",
    "objectives": "Вазифаҳои таҳқиқот",
    "object": "Объекти таҳқиқот",
    "subject": "Мавзӯи таҳқиқот",
    "methods": "Усулҳои таҳқиқот",
    "novelty": "Навоварии илмӣ",
    "practical_value": "Аҳамияти амалӣ",
    "study_design": "Тарҳи таҳқиқот",
    "inclusion_criteria": "Меъёрҳои дохилшавӣ",
    "exclusion_criteria": "Меъёрҳои хориҷшавӣ",
    "sample": "Интихоб",
    "statistical_methods": "Усулҳои оморӣ",
    "ethics": "Ахлоқи таҳқиқот",
    "ethics_committee": "Кумитаи ахлоқ",
    "consent_note": "Ризоияти хаттии ҳамаи беморон гирифта шудааст",
    # подписи и пометки
    "source": "Сарчашма",
    "own_data": "Маълумоти муаллиф",
    "missing_data": "Маълумот нокифоя",
    "note": "Эзоҳ",
    "figure_note": "Эзоҳ ба расм",
    "table_note": "Эзоҳ ба ҷадвал",
    "teaching_example": "Намунаи таълимӣ: маълумотҳо моделсозӣ шудаанд",
    "verification": "Протоколи санҷиши сарчашмаҳо",
    "guidelines_note": "Дастурамали клиникӣ",
    "no_data_placeholder": "Маълумот нокифоя",
    "data_provenance": "Пайдоиши маълумотҳои расмҳо",
    # титульный лист
    "ministry": "Вазорат",
    "university": "Донишгоҳ",
    "faculty": "Факултет",
    "chair": "Кафедра",
    "topic": "Мавзӯъ",
    "performed_by": "Иҷрокунанда",
    "supervisor": "Роҳбари илмӣ",
    "reviewer": "Муқарриз",
    "head_of_chair": "Мудири кафедра",
    "student": "Донишҷӯ",
    "group": "Гурӯҳ",
    "city_year": "Шаҳр — сол",
    "defense_date": "Санаи ҳимоя",
    "grade": "Баҳо",
    "work_type_course": "КОРИ КУРСӢ",
    "work_type_diploma": "КОРИ ХАТМКУНАНДАГОН (ВКР)",
    "work_type_master": "РИСОЛАИ МАГИСТРӢ",
    # частые слова
    "and_others": "ва диг.",
    "total": "Ҳамагӣ",
    "group_word": "Гурӯҳ",
    "patients": "бемор",
    "male": "мард",
    "female": "зан",
    "age": "сину сол",
    "mean": "миёна",
}

MONTHS_TG = [
    "январ", "феврал", "март", "апрел", "май", "июн",
    "июл", "август", "сентябр", "октябр", "ноябр", "декабр",
]


class Tajik(Language):
    code = "tg"
    name = "Тоҷикӣ"

    def __init__(self) -> None:
        super().__init__(
            code=self.code,
            name=self.name,
            terms=TERMS_TG,
            months=MONTHS_TG,
            decimal_separator=",",
            thousands_separator=" ",
        )

    def date_str(self, value=None) -> str:
        import datetime

        value = value or datetime.date.today()
        return f"«{value.day:02d}» {self.months[value.month - 1]}и {value.year}"
