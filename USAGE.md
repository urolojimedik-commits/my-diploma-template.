# Инструкция по использованию

## 1. Установка

```bash
git clone https://github.com/urolojimedik-commits/my-diploma-template..git
cd my-diploma-template.
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Требования: Python 3.11+, pip, LibreOffice/Word для проверки DOCX.

## 2. CLI

### Собрать диплом (все этапы)
```bash
PYTHONPATH=src python -m diploma_builder.cli --topic "Цифровая трансформация госуправления" --type диплом --build
# → output/thesis.docx, output/thesis.pdf, output/images/*.png, output/references.bib
```

### Только план
```bash
PYTHONPATH=src python -m diploma_builder.cli plan --topic "ИИ в образовании" --type курсовая
cat output/plan.md
```

### Поиск источников
```bash
PYTHONPATH=src python -m diploma_builder.cli search --topic "machine learning" --rows 5
# Ищет в Crossref/OpenAlex или локальной базе, выводит DOI
```

### Из YAML
```yaml
# my_project.yaml
topic: "Развитие электронного документооборота"
work_type: диплом
discipline: Информационные системы
author:
  fio: "Сидорова А.А., ИВТ-22"
  supervisor: "Иванов Б.Б., д.т.н."
output_dir: my_diploma
```
```bash
PYTHONPATH=src python -m diploma_builder.cli build --config my_project.yaml
```

### Справка
```bash
PYTHONPATH=src python -m diploma_builder.cli --help
PYTHONPATH=src python -m diploma_builder.cli build --help
PYTHONPATH=src python -m diploma_builder.cli search --help
```

## 3. Python API

```python
from pathlib import Path
from diploma_builder.pipeline import create_project_from_topic, DiplomaPipeline
from diploma_builder.config import WorkType

cfg = create_project_from_topic(
    topic="Кибербезопасность КИИ",
    work_type="магистерская",
    discipline="Информационная безопасность",
    author_fio="Петров П.П., ИБ-23",
    output_dir="output_кии"
)
# Кастомизация
cfg.author.supervisor = "Сидоров С.С., к.т.н."
cfg.organization.university = "МГТУ им. Баумана"

pipeline = DiplomaPipeline(cfg)
results = pipeline.run(search_rows=15, verify_sources=False)
print(results["docx"])  # Path("output_кии/thesis.docx")
print(results["pdf"])   # Path("output_кии/thesis.pdf")
```

## 4. Веб-интерфейс

```bash
PYTHONPATH=src python -m diploma_builder.cli serve --port 8000
# Откройте http://localhost:8000
# 1. Введите тему → 2. Выберите тип → 3. Нажмите "Создать" → 4. Дождитесь → 5. Скачайте DOCX/PDF
```

Для деплоя:
```bash
gunicorn --bind 0.0.0.0:8000 diploma_builder.web.app:create_app()
# или
python -m diploma_builder.web.app
```

## 5. Quarto (опционально)

Если установлен Quarto/Pandoc:
```bash
quarto render examples/demo_цифровизация/quarto --to docx
# или
quarto render examples/demo_цифровизация/quarto --to pdf
```

Сгенерированный Python DOCX/PDF уже ГОСТ-совместим, Quarto — доп. опция.

## 6. Структура вывода

```
output/
├── plan.md                     # план Markdown
├── project.yaml                # конфиг
├── sources.json                # метаданные источников
├── references.bib              # BibTeX
├── bibliography_gost.txt       # ГОСТ список
├── 00_Введение.md              # главы Markdown
├── 01_Глава_1.md
├── 02_Глава_2.md
├── 03_Глава_3.md
├── 50_Заключение.md
├── 60_Приложения_Иллюстрации.md
├── article.md                  # научная статья
├── images/*.png                # 8 графиков
├── thesis.docx                 # DOCX ГОСТ
├── thesis.pdf                  # PDF ГОСТ
└── quarto/                     # Quarto проект
```

## 7. Кастомизация ГОСТ

В `src/diploma_builder/config.py`:
```python
GOST = {
  "margins_mm": {"left": 30, "right": 15, "top": 20, "bottom": 20},
  "font": {"name": "Times New Roman", "size_pt": 14},
  "line_spacing": 1.5,
  "paragraph_indent_cm": 1.25,
}
```

В `docx_builder.py` → `set_margins()`, `add_paragraph_styled()`.

## 8. Добавление своих источников

Отредактируйте `data/verified_sources.json`:
```json
{
  "key": "ivanov2024mytopic",
  "title": "Моя статья",
  "authors": ["Иванов И.И."],
  "year": 2024,
  "doi": "10.xxxx/yyyy",
  "journal": "Вестник",
  "verified": true
}
```

Или добавьте после генерации в `output/references.bib` и пересоберите DOCX:
```python
from diploma_builder.config import SourceRecord
from diploma_builder.pipeline import DiplomaPipeline
cfg.sources.append(SourceRecord(key="my2024", title="...", authors=["..."], year=2024, doi="10.xxxx"))
```

## 9. Частые вопросы

**Q: Crossref недоступен?**
A: Система автоматически использует локальную базу 20 проверенных DOI. В проде с интернетом — онлайн поиск.

**Q: Графики с какими данными?**
A: Реальные — из `REAL_DATASETS` (Росстат тренд), учебные — помечены «данные условные». Замените на свои CSV.

**Q: PDF кириллица кракозябры?**
A: Проверьте наличие `/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf`. Установите `fonts-dejavu-core`.

**Q: Как изменить тему после генерации?**
A: Отредактируйте `output/01_Глава_1.md` и пересоберите:
```bash
PYTHONPATH=src python -c "from diploma_builder.pipeline import ...; ..."
```

## 10. Проверка

```bash
# DOCX открывается?
libreoffice examples/demo_цифровизация/thesis.docx
# PDF открывается?
evince examples/demo_цифровизация/thesis.pdf
# Счётчик
ls -lh examples/demo_цифровизация/thesis.docx  # 808K
```
