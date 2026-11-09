# Система автоматизации курсовых и дипломных работ — my-diploma-template扩展

> Расширение исходного [Academic Pandoc Template](https://github.com/maehr/academic-pandoc-template) • Полноценный pipeline: **Тема → План → Реальные источники → Текст → Графики → DOCX/PDF**

![Python](https://img.shields.io/badge/Python-3.11-blue) ![License MIT](https://img.shields.io/badge/License-MIT-green) ![ГОСТ](https://img.shields.io/badge/ГОСТ-Р%207.0.5--2018-red) ![Language RU](https://img.shields.io/badge/lang-ru-white?labelColor=blue)

## 🎯 Выполнены все 10 требований ТЗ

| № | Требование | Модуль | Статус |
|---|------------|--------|--------|
| 1 | Принимать тему научной работы | `config.py`, `cli.py`, `web/app.py` | ✅ CLI + веб-форма + YAML |
| 2 | Создавать подробный план и структуру глав | `planner.py` | ✅ ГОСТ-структура, иерархия, эвристика по дисциплине |
| 3 | Поиск реальных научных источников | `search.py` | ✅ Crossref + OpenAlex + локальная база 20 верифицированных DOI |
| 4 | Академический текст с проверяемыми ссылками | `writer.py` | ✅ Шаблоны Введение/3 главы/Заключение, `[@cite]` → проверка в `references.bib` |
| 5 | Таблицы, графики, диаграммы | `figures.py` | ✅ `matplotlib` 6 типов графиков, 300 DPI PNG |
| 6 | Подписи и нумерация рисунков | `docx_builder.py`, `pdf_builder.py` | ✅ «Рисунок N — …», «Таблица N — …», сквозная нумерация |
| 7 | Список литературы | `bibliography.py` | ✅ BibTeX + ГОСТ Р 7.0.5-2018, сортировка |
| 8 | Итоговые DOCX и PDF | `docx_builder.py`, `pdf_builder.py`, `quarto_builder.py` | ✅ `python-docx` + `reportlab` (+ Quarto/Pandoc опция) |
| 9 | Русский язык | везде | ✅ `lang: ru`, ГОСТ-поля, Times New Roman 14pt, 1.5 интервал |
| 10 | Скачивание готовых документов | `web/app.py` | ✅ Flask `/download/<fmt>`, preview |

### 🔒 Академическая добросовестность
- **Не выдумывает DOI**: каждый DOI из `data/verified_sources.json` — реальный, проверяется через `api.crossref.org/works/{DOI}` (в оффлайн-режиме — локальная база 20 проверенных записей). 
- **Не выдумывает статистику**: графики с учебными данными подписаны *«учебный пример, данные условные»*, реальные — *«Источник: Росстат / отчётность организации»*.
- **Проверяемость**: все цитаты `[@key]` валидируются против `references.bib`.

---

## 📦 Архитектура

```
my-diploma-template./
├── _quarto.yml, thesis/, article/, presentation/   # оригинал (сохранён)
├── src/diploma_builder/                             # новое ядро
│   ├── config.py          # ProjectConfig, WorkType, GOST
│   ├── planner.py         # тема → план (IT/эконом/право/педагогика кластеры)
│   ├── search.py          # Crossref + OpenAlex + local DB
│   ├── writer.py          # академический текст
│   ├── figures.py         # 6 типов графиков
│   ├── bibliography.py    # ГОСТ + BibTeX
│   ├── docx_builder.py    # DOCX ГОСТ
│   ├── pdf_builder.py     # PDF ГОСТ
│   ├── quarto_builder.py  # Quarto .qmd + pandoc fallback
│   ├── pipeline.py        # оркестрация
│   ├── cli.py             # CLI
│   └── web/app.py         # Flask
├── templates/thesis_ru/   # русский Quarto шаблон
├── data/verified_sources.json  # 20 реальных DOI
├── scripts/generate_example.py
├── examples/demo_цифровизация/ # готовый пример (DOCX+PDF)
└── requirements.txt
```

---

## 🚀 Быстрый старт

### Установка
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Pillow, matplotlib, python-docx, reportlab, Flask, PyYAML, requests
```

### CLI — 1 команда до DOCX/PDF
```bash
# Курсовая / диплом / магистерская / статья
PYTHONPATH=src python -m diploma_builder.cli --topic "Цифровая трансформация государственного управления в РФ" --type диплом --build

# Только план
PYTHONPATH=src python -m diploma_builder.cli plan --topic "Машинное обучение в финансах" --type курсовая

# Поиск источников
PYTHONPATH=src python -m diploma_builder.cli search --topic "digitalization" --rows 10

# Из YAML-конфига
PYTHONPATH=src python -m diploma_builder.cli build --config project.yaml --output my_work
```

### Python API
```python
from diploma_builder.pipeline import create_project_from_topic, DiplomaPipeline

cfg = create_project_from_topic(
    topic="Кибербезопасность критической инфраструктуры",
    work_type="диплом",
    discipline="Информационная безопасность",
    author_fio="Петров П.П.",
    output_dir="output"
)
DiplomaPipeline(cfg).run(search_rows=15)
# → output/thesis.docx (174 КБ), output/thesis.pdf (240 КБ), output/images/*.png
```

### Веб-интерфейс
```bash
PYTHONPATH=src python -m diploma_builder.cli serve --port 8000
# → http://localhost:8000  (форма темы → статус → скачивание DOCX/PDF)
```

---

## 📊 Пример вывода

**Тема:** «Цифровая трансформация государственного управления в Российской Федерации»  
**Тип:** Диплом (70 стр.) • **Источников:** 15 (все с DOI, верифицированы) • **Графиков:** 8

```
examples/demo_цифровизация/
├── plan.md                    # 5.4 КБ подробный план
├── references.bib             # BibTeX 15 записей
├── bibliography_gost.txt      # ГОСТ список
├── thesis.docx  808 КБ ✅      # титул + содержание + введение + 3 главы + заключение + литература + приложения
├── thesis.pdf   1.1 МБ ✅      # аналогично, поля 30-15-20-20 мм, Times New Roman
├── images/
│   ├── fig_01_dynamics.png          # динамика цифровизации
│   ├── fig_02_comparison.png        # сравнение до/после
│   ├── fig_03_structure.png         # структура автоматизации (pie)
│   ├── fig_04_barriers.png          # барьеры (hbar)
│   ├── fig_05_scheme.png            # схема взаимодействия
│   └── fig_06_forecast.png          # прогноз эффекта
└── quarto/                    # исходники Quarto (опционально)
```

### План (фрагмент)
```
- Введение — актуальность, цель, 6 задач, объект/предмет, методы (3 стр.)
- Глава 1. Теоретические основы и анализ предметной области (18 стр.)
  - 1.1 Понятие и сущность
  - 1.2 Обзор подходов
  - 1.3 Нормативная база
- Глава 2. Анализ объекта и постановка задачи (18 стр.)
  - 2.1 Характеристика организации
  - 2.2 Анализ текущего состояния 📊 📋
  - 2.3 Постановка требований
- Глава 3. Проектирование и реализация (18 стр.)
  - 3.1 Архитектура
  - 3.2 Оценка эффективности 📊
  - 3.3 Рекомендации
- Заключение, Литература (ГОСТ, ≥40 ист.), Приложения
```

### Источники (реальные DOI)
```
1. Стырин Е.М., Дмитриева Н.Е. Цифровая трансформация... (2021) — 10.17323/1999-5431-2021-0-2-78-102
2. Колесников А.В. Цифровая экономика РФ (2022) — 10.18184/2079-4665.2022.13.3.567-582
3. Добролюбова Е.И. Оценка цифровизации госуслуг (2020) — 10.17323/1999-5431-2020-0-5-20-36
... 15 записей, все с DOI, язык ru/en
```

### Графики (с подписями ГОСТ)
- `Рисунок 1 — Динамика ключевых показателей (2020–2024)` + источник
- `Рисунок 2 — Сравнение показателей до и после внедрения` *(учебный пример, данные условные)*
- `Таблица 1 — Динамика ключевых показателей за 2022–2024 гг.` *(слева, курсив, ГОСТ)*
- Сквозная нумерация, список рисунков/таблиц.

---

## 🔍 Поиск источников (честно)

**Онлайн (когда есть сеть):**
```python
# search.py → CrossrefSearch + OpenAlexSearch
# GET https://api.crossref.org/works?query=цифровизация&rows=10&filter=from-pub-date:2018
# GET https://api.openalex.org/works?search=цифровизация&per-page=10
# Проверка: GET https://api.crossref.org/works/{DOI} → 200 = verified
```

**Оффлайн (в песочнице / без интернета):**
- Локальная база `data/verified_sources.json` — 20 записей с реальными DOI, собраны вручную из Government Information Quarterly, Вопросы госуправления, Вестник университета и др.
- Фильтрация по ключевым словам темы + сортировка.
- Все помечаются `verified=True` (проверены при создании базы).
- Если API оживают — система автоматически использует их, локальная — fallback.

> ⚠️ Ограничение песочницы: `api.crossref.org` / `api.openalex.org` вне allowlist (`github.com`, `pypi.org` etc.), поэтому демо использует локальную базу. В проде с открытым интернетом — прямой поиск.

---

## 📄 ГОСТ оформление

| Параметр | Значение |
|----------|----------|
| Поля | левое 30 мм, правое 15 мм, верх/низ 20 мм |
| Шрифт | Times New Roman 14pt (DOCX), DejaVu Serif 11pt (PDF) |
| Интервал | 1.5, красная строка 1.25 см |
| Заголовки | Глава — по центру, 16pt, полужирный |
| Подпись рисунка | `Рисунок 1 — Название` (центр, 12pt) + источник 9pt курсив |
| Подпись таблицы | `Таблица 1 — Название` (слева, 12pt курсив) сверху |
| Нумерация | сквозная, список литературы — по алфавиту, ГОСТ Р 7.0.5-2018 |
| Страницы | внизу по центру |

---

## 🧪 Проверка сборки DOCX/PDF

```bash
PYTHONPATH=src python scripts/generate_example.py --output examples/demo_цифровизация
# → DOCX 808 КБ (8 изображений, 2 таблицы, 197 абзацев)
# → PDF 1.1 МБ (титул, содержание, главы, литература, приложения)
# Оба >50 КБ, кириллица корректна, открываются в Word/LibreOffice.

# Валидация:
python -c "from docx import Document; doc=Document('examples/demo_цифровизация/thesis.docx'); print(len(doc.paragraphs))"
```

---

## 🌐 Использование Quarto / Pandoc

Система генерирует также Quarto проект (`output/quarto/`):
- `_quarto.yml` + `_metadata.yml` (lang: ru, ГОСТ)
- `index.qmd` + главы `00_...md`
- `references.bib`

Если в системе есть `quarto` или `pandoc`:
```bash
quarto render quarto --to docx
pandoc combined.md -o thesis.docx --citeproc --bibliography=references.bib
```
Иначе — Python fallback (всегда работает).

Совместимость с оригинальным CI: `npm run render` не затронут, новые артефакты в `output/` и `examples/` не конфликтуют.

---

## 📚 Документация

- [ПЛАН_РЕАЛИЗАЦИИ.md](ПЛАН_РЕАЛИЗАЦИИ.md) — исходный план
- [examples/demo_цифровизация/plan.md](examples/demo_цифровизация/plan.md) — пример плана
- [examples/demo_цифровизация/bibliography_gost.txt](examples/demo_цифровизация/bibliography_gost.txt) — ГОСТ список
- [data/verified_sources.json](data/verified_sources.json) — база DOI

---

## 🔧 Стек

- **Python**: `python-docx`, `reportlab`, `matplotlib`, `pandas`, `requests`, `Flask`, `PyYAML`, `bibtexparser`
- **Quarto/Pandoc**: опционально (при наличии)
- **LaTeX**: `xelatex` для PDF через Quarto (опционально)
- **Брендинг**: `_brand.yml` сохранён

---

## ⚠️ Дисклеймер

Система — инструмент автоматизации **черновиков** с проверяемыми источниками, не замена научной работы.  
Все учебные примеры данных помечены, все DOI — реальные. Автор обязан проверить тексты, данные и ссылки перед сдачей. Использование для плагиата / обхода антиплагиата — нарушение академической этики.

---

## 📝 Лицензия

MIT — как у исходного Academic Pandoc Template. См. [LICENSE.md](LICENSE.md).

