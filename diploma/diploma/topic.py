"""Шаг 1. Разбор темы научной работы.

Из строки темы извлекаются: тип работы, ключевые слова (русские и английские),
объект, предмет, цель, задачи и методы, а также «части» названия
(процесс / метод / предметная область), которые используются при построении
плана. Всё, что выводится здесь, — либо прямая перефразировка темы, либо
шаблонные формулировки, не содержащие фактических утверждений о мире.
Фактические утверждения появляются только на шаге написания текста и только
со ссылками на проверенные источники.
"""

from __future__ import annotations

import re

from .model import Topic
from .ru_en import RU_EN, _STOPWORDS_RU, to_english

WORK_TYPE_PATTERNS = [
    (r"\bкурсов(ая|ой)\b|\bкурсовая работа\b", "course"),
    (r"\bмагистерск(ая|ой)\b|\bмагистратура\b", "master"),
    (r"\bбакалаврск(ая|ой)\b|\bбакалавриат\b", "bachelor"),
    (r"\bдипломн(ая|ой)\b|\bвкр\b|\bвыпускная квалификационная\b", "diploma"),
]

PROCESS_WORDS = (
    "Применение|Разработка|Исследование|Анализ|Оценка|Сравнение|Сравнительный анализ|"
    "Совершенствование|Проектирование|Моделирование|Оптимизация|Повышение|Формирование|"
    "Развитие|Использование|Внедрение|Обоснование|Построение|Создание"
)

METHOD_HINTS = {
    "анализ": "анализ научной литературы и нормативных документов",
    "обзор": "систематический обзор источников",
    "сравнение": "сравнительный анализ",
    "сравнительный": "сравнительный анализ",
    "разработка": "проектирование и разработка",
    "модель": "математическое и компьютерное моделирование",
    "моделирование": "компьютерное моделирование",
    "эксперимент": "вычислительный эксперимент",
    "оценка": "оценка качества по количественным метрикам",
    "эффективность": "оценка эффективности по количественным метрикам",
    "статисти": "статистическая обработка данных",
    "данные": "анализ наборов данных",
    "опрос": "анкетирование",
    "алгоритм": "разработка и анализ алгоритмов",
    "классификация": "построение моделей классификации",
    "машинное обучение": "методы машинного обучения",
    "глубокое обучение": "методы глубокого обучения",
    "нейрон": "нейросетевые модели",
    "измерение": "измерительный эксперимент",
    "диагностика": "анализ диагностической точности",
}

DISCIPLINE_HINTS = {
    "уролог": "урология",
    "мочекамен": "урология",
    "почк": "урология / нефрология",
    "кардио": "кардиология",
    "онколог": "онкология",
    "эконом": "экономика",
    "финанс": "финансы",
    "юрид": "юриспруденция",
    "прав": "юриспруденция",
    "педагог": "педагогика",
    "психолог": "психология",
    "машин": "информационные технологии",
    "нейро": "информационные технологии",
    "алгоритм": "информационные технологии",
    "данных": "информационные технологии",
    "программ": "информационные технологии",
    "информацион": "информационные технологии",
}


def detect_work_type(text: str) -> str:
    low = text.lower()
    for pattern, kind in WORK_TYPE_PATTERNS:
        if re.search(pattern, low):
            return kind
    return "diploma"


def tokenize_ru(text: str) -> list[str]:
    words = re.split(r"[\s,.;:!?()\[\]\"«»/—-]+", text.lower())
    return [w for w in words if len(w) > 2 and w not in _STOPWORDS_RU]


def extract_keywords(text: str, limit: int = 8) -> list[str]:
    """Ключевые слова: сначала термины словаря, затем значимые слова темы."""
    low = text.lower()
    found: list[str] = []
    for term in sorted((k for k in RU_EN if len(k) > 3), key=len, reverse=True):
        if term in low:
            if not any(term in f for f in found):
                found.append(term)
    tokens = tokenize_ru(text)
    for t in tokens:
        if not any(t in f or f in t for f in found):
            found.append(t)
        if len(found) >= limit:
            break
    return found[:limit]


def split_title(title: str) -> tuple[str, str, str]:
    """Разбирает название на (процесс, метод, предметная область).

    Пример: «Применение методов машинного обучения для автоматизированной
    диагностики мочекаменной болезни по данным компьютерной томографии»
    → («Применение», «методов машинного обучения»,
       «автоматизированной диагностики мочекаменной болезни по данным
       компьютерной томографии»).

    Если шаблон не распознан, возвращается («», «», исходное название).
    """
    text = title.strip().rstrip(".")
    m = re.match(rf"^({PROCESS_WORDS})\s+(.{{3,}})$", text, flags=re.I)
    if not m:
        return "", "", text
    process = m.group(1)
    rest = m.group(2)
    parts = re.split(r"\s+(?:для|в целях|на основе|с целью)\s+", rest, maxsplit=1)
    if len(parts) == 2:
        method, domain = parts
    else:
        # делим по первому предлогу: всё до него — метод, после — область
        m2 = re.match(r"^(.{3,90}?)\s+(?:в|на|по|при|с)\s+(.{3,})$", rest)
        if m2:
            method, domain = m2.group(1), m2.group(2)
        else:
            method, domain = "", rest
    return process.strip(), method.strip(), domain.strip()


def detect_methods(text: str) -> list[str]:
    low = text.lower()
    methods: list[str] = []
    for hint, name in METHOD_HINTS.items():
        if hint in low and name not in methods:
            methods.append(name)
    if not methods:
        methods = ["анализ научной литературы и нормативных документов", "сравнительный анализ"]
    return methods


def detect_discipline(text: str) -> str:
    low = text.lower()
    for hint, name in DISCIPLINE_HINTS.items():
        if hint in low:
            return name
    return ""


def normalize_title(raw: str) -> str:
    """Приводит тему к виду заголовка, не меняя смысл."""
    title = re.sub(r"\s+", " ", raw.strip())
    title = re.sub(
        r"^(тема\s*(работы|курсовой|диплома)?\s*[:.\-–—]?\s*)|"
        r"^(курсовая\s+работа|выпускная\s+квалификационная\s+работа|дипломная\s+работа|"
        r"магистерская\s+диссертация)\s*(на\s+тему)?\s*[:.\-–—]?\s*",
        "",
        title,
        flags=re.I,
    )
    title = re.sub(r"\s*\(\s*\)", "", title).strip(" .:;-–—«»\"'")
    if not title:
        title = raw.strip()
    return title[:1].upper() + title[1:] if title else title


def build_topic(raw: str, work_type: str | None = None) -> Topic:
    title = normalize_title(raw)
    keywords_ru = extract_keywords(title)
    methods = detect_methods(title)
    discipline = detect_discipline(title)
    process, method_gen, domain_gen = split_title(title)

    # Объект, предмет, цель и задачи формулируются через название целиком —
    # это гарантирует грамматическую правильность и не добавляет выдуманных
    # утверждений.
    object_ru = f"предметная область, охватываемая темой «{title}»"
    subject_ru = f"методы и подходы ({methods[0]}), рассматриваемые в рамках темы «{title}»"
    goal_ru = (
        f"систематизация и критическое сопоставление сведений по теме «{title}» "
        "на основе проверенных научных источников"
    )
    tasks = [
        f"раскрыть содержание и уточнить понятийный аппарат по теме «{title}»;",
        "выполнить поиск, проверку и отбор научных источников по теме исследования;",
        f"систематизировать и сравнить используемые подходы ({methods[0]});",
        "сформулировать выводы и наметить направления дальнейшей работы.",
    ]
    return Topic(
        raw=raw,
        title=title,
        work_type=work_type or detect_work_type(raw),
        discipline=discipline,
        object_ru=object_ru,
        subject_ru=subject_ru,
        goal_ru=goal_ru,
        tasks_ru=tasks,
        methods_ru=methods,
        keywords_ru=keywords_ru,
        keywords_en=[to_english(k) for k in keywords_ru],
        title_process=process,
        title_method=method_gen,
        title_domain=domain_gen or title,
    )
