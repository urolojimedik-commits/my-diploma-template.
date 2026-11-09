"""Русско-английский словарь терминов для построения поисковых запросов.

Словарь не является переводчиком общего назначения: он покрывает термины,
типичные для тематики курсовых и дипломных работ, и расширяется файлом
``data/ru_en.json``. Неизвестные слова транслитерируются — это лучше, чем
молча отбросить часть темы при поиске.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .settings import DATA_DIR

RU_EN: dict[str, str] = {
    # медицина
    "мочекаменная болезнь": "urolithiasis kidney stone",
    "мочекаменной болезни": "urolithiasis kidney stone",
    "уролитиаз": "urolithiasis",
    "уролитиаза": "urolithiasis",
    "камни почек": "kidney stones",
    "камней почек": "kidney stones",
    "камня почек": "kidney stone",
    "почки": "kidney",
    "почек": "kidney",
    "почечный": "renal",
    "гидронефроз": "hydronephrosis",
    "пиелонефрит": "pyelonephritis",
    "аденома предстательной железы": "benign prostatic hyperplasia",
    "рак предстательной железы": "prostate cancer",
    "цистит": "cystitis",
    "урология": "urology",
    "урологический": "urological",
    "урологическая": "urological",
    "эндоскопия": "endoscopy",
    "эндоскопический": "endoscopic",
    "уретероскопия": "ureteroscopy",
    "литотрипсия": "lithotripsy",
    "диагностика": "diagnosis detection",
    "диагностики": "diagnosis detection",
    "лечение": "treatment",
    "лечения": "treatment",
    "терапия": "therapy",
    "клинический": "clinical",
    "клинические": "clinical",
    "пациент": "patient",
    "пациентов": "patients",
    "заболевание": "disease",
    "заболевания": "disease",
    "заболеваемость": "incidence",
    "распространённость": "prevalence",
    "осложнение": "complication",
    "осложнения": "complications",
    "рецидив": "recurrence",
    "рецидивы": "recurrence",
    "хирургический": "surgical",
    "операция": "surgery",
    "операции": "surgery",
    "выживаемость": "survival",
    "качество жизни": "quality of life",
    "фактор риска": "risk factor",
    "факторы риска": "risk factors",
    "ожирение": "obesity",
    "сахарный диабет": "diabetes mellitus",
    # визуализация
    "компьютерная томография": "computed tomography CT",
    "компьютерной томографии": "computed tomography CT",
    "компьютерно-томографический": "computed tomography CT",
    "магнитно-резонансная томография": "magnetic resonance imaging MRI",
    "ультразвуковое исследование": "ultrasound imaging",
    "ультразвуковая": "ultrasound",
    "рентген": "X-ray radiography",
    "визуализация": "imaging",
    "изображения": "images",
    "изображений": "images",
    "изображение": "image",
    "сегментация": "segmentation",
    "сегментации": "segmentation",
    # информатика и ИИ
    "искусственный интеллект": "artificial intelligence",
    "искусственного интеллекта": "artificial intelligence",
    "машинное обучение": "machine learning",
    "машинного обучения": "machine learning",
    "глубокое обучение": "deep learning",
    "глубокого обучения": "deep learning",
    "нейронная сеть": "neural network",
    "нейронные сети": "neural networks",
    "нейронных сетей": "neural networks",
    "свёрточная нейронная сеть": "convolutional neural network CNN",
    "свёрточные нейронные сети": "convolutional neural networks CNN",
    "нейросеть": "neural network",
    "трансформер": "transformer",
    "компьютерное зрение": "computer vision",
    "обработка изображений": "image processing",
    "распознавание образов": "pattern recognition",
    "классификация": "classification",
    "кластеризация": "clustering",
    "регрессия": "regression",
    "прогнозирование": "prediction forecasting",
    "прогноз": "prediction",
    "анализ данных": "data analysis",
    "обработка данных": "data processing",
    "алгоритм": "algorithm",
    "алгоритмы": "algorithms",
    "алгоритмов": "algorithms",
    "модель": "model",
    "модели": "models",
    "моделей": "models",
    "метод": "method",
    "методы": "methods",
    "методов": "methods",
    "подход": "approach",
    "подходы": "approaches",
    "точность": "accuracy",
    "эффективность": "effectiveness performance",
    "автоматизация": "automation",
    "автоматический": "automated",
    "автоматизированный": "automated",
    "программное обеспечение": "software",
    "информационная система": "information system",
    "база данных": "database",
    "нейросетевой": "neural network",
    # общие научные термины
    "исследование": "study research",
    "исследования": "study research",
    "анализ": "analysis",
    "методика": "methodology",
    "разработка": "development",
    "разработки": "development",
    "применение": "application",
    "применения": "application",
    "применении": "application",
    "сравнение": "comparison",
    "сравнительный": "comparative",
    "сравнительная": "comparative",
    "оценка": "evaluation assessment",
    "повышение": "improvement",
    "управление": "management",
    "система": "system",
    "системы": "systems",
    "технология": "technology",
    "технологии": "technology",
    "процесс": "process",
    "процессы": "processes",
    "структура": "structure",
    "показатель": "indicator",
    "показатели": "indicators",
    "качество": "quality",
    "результат": "result",
    "результаты": "results",
    "современный": "modern",
    "современные": "modern",
    "перспективы": "prospects",
    "проблема": "problem",
    "проблемы": "problems",
}

# Транслитерация для слов, отсутствующих в словаре.
_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
    "я": "ya",
}

_STOPWORDS_RU = {
    "и", "в", "во", "на", "за", "по", "для", "при", "с", "со", "к", "от", "до", "из",
    "у", "о", "об", "а", "но", "как", "что", "это", "не", "или", "же", "бы", "ли",
    "теме", "тема", "работы", "работа", "работе", "данных", "данные", "на основе",
    "основе", "путем", "пути", "также", "его", "ее", "их", "том", "том числе",
}


def load_overrides() -> dict[str, str]:
    path = DATA_DIR / "ru_en.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def transliterate(word: str) -> str:
    return "".join(_TRANSLIT.get(ch, ch) for ch in word.lower())


def to_english(text: str) -> str:
    """Переводит термины словарём; неизвестные слова транслитерирует."""
    overrides = {**RU_EN, **load_overrides()}
    text_low = text.lower()
    # Сначала -- многословные термины (от длинных к коротким)
    for term in sorted(overrides, key=len, reverse=True):
        if term in text_low:
            text_low = re.sub(re.escape(term), " " + overrides[term] + " ", text_low)
    words = [w for w in re.split(r"[\s,.;:()\[\]\"«»—-]+", text_low) if w]
    out: list[str] = []
    for w in words:
        if w.isascii():
            out.append(w)
        elif w in _STOPWORDS_RU:
            continue
        elif w in overrides:
            out.append(overrides[w])
        else:
            out.append(transliterate(w))
    return " ".join(out)
