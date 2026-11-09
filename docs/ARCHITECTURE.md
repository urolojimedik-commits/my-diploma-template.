# Архитектура системы

## Компоненты

### 1. Planner (`planner.py`)
- Вход: тема (строка), тип работы, дисциплина
- Кластеризация: `it` | `economy` | `law` | `pedagogy` | `default` по ключевым словам
- Профили: курсовая 30 стр / диплом 70 / магистерская 90 — кол-во глав, секций, источников
- Выход: `ProjectConfig.plan` — иерархия `ChapterPlan` с `FigureSpec`/`TableSpec`

### 2. Search (`search.py`)
```
topic → CrossrefSearch	search_bibliography() → _parse_crossref_item()
      → OpenAlexSearch	search() → _parse_openalex_item()
      → merge + dedup по DOI/title → verify_doi() (опционально)
      → fallback: data/verified_sources.json → filter by topic → return 15
```
- Кэш: `data/cache/<md5>.json`
- Проверка DOI: GET `api.crossref.org/works/{DOI}` → 200
- Локальная база: 20 реальных записей, все verified=True

### 3. Writer (`writer.py`)
- Шаблоны: INTRO_TEMPLATE, CHAPTER1/2/3_TEMPLATE, CONCLUSION_TEMPLATE (русский академический стиль)
- `_safe_format()` — замена только известных ключей, сохранение `{#fig-...}`
- `_pick_cites()` — циклический выбор ключей из sources
- Выход: `Dict[filename.md: content]` (Markdown + Quarto cross-ref)

### 4. Figures (`figures.py`)
- FigureFactory(output_dir/images)
- Методы: `bar_chart`, `line_chart`, `pie_chart`, `grouped_bar`, `horizontal_bar`, `diagram_scheme`
- Настройки: DejaVu Sans, DPI 300, палитра #1f4e79, подписи 7pt курсив, пометка synthetic
- `create_demo_set()` — 6 типов графиков, `generate_for_plan()` — по FigureSpec

### 5. Bibliography (`bibliography.py`)
- BibliographyManager(sources)
- `sort_gost()` — русские → латиница → год
- `to_bibtex()` — уникализация ключей, запись в references.bib
- `to_gost_list()` — формат «1. Автор Название // Журнал — год — DOI»
- `verify_all()` — статистика

### 6. DocxBuilder (`docx_builder.py`)
- Document() → set_margins(30,15,20,20 мм)
- _create_title_page(): министерство, тип, тема, автор/руководитель, город-год
- _create_toc_placeholder(): план как список
- _add_text_with_citations(): парсер Markdown → docx (заголовки, абзацы, списки, цитаты, таблицы markdown, изображения `![...](...)`)
- add_table_gost(): Light Grid Accent 1, заливка заголовка #D9E2F3
- add_figure_gost(): 14 см width, подпись «Рисунок N — …», источник 9pt
- build(): параграфы 14pt Times New Roman, 1.5 интервал, 1.25 см отступ, нумерация страниц

### 7. PdfBuilder (`pdf_builder.py`)
- SimpleDocTemplate(A4, margins 30/15/20/20 мм)
- Шрифты: DejaVuSerif.ttf → GOST, fallback Helvetica
- _init_styles(): GOST_Normal 11pt, Heading1 15pt центр, Caption 9pt центр, SourceNote 7pt серый
- _story_title_page(), _story_toc(), _parse_markdown_to_story() — аналогично DOCX
- doc.build(onFirstPage=_footer) — нумерация внизу центр

### 8. QuartoBuilder (`quarto_builder.py`)
- Генерация _quarto.yml (project default), _metadata.yml (lang ru, ГОСТ CSL, toc, lof, lot)
- references.bib, index.qmd (include всех глав)
- render(): quarto render → pandoc fallback → None (Python fallback уже есть)

### 9. Pipeline (`pipeline.py`)
```
Planner → Search → Bibliography → Figures → Writer (+ appendix) → Docx → Pdf → Quarto
```
- Директория: output/ + images/ + quarto/
- Логирование каждого этапа
- Возвращает Dict[artifact: Path]

### 10. Web (`web/app.py`)
- Flask create_app(): / (form), /build (POST, thread), /status/<id>, /result/<id>, /download/<id>/<fmt>, /image/<id>/<name>, /search, /health
- Хранилище: JOBS dict (id → status, topic, output_dir)
- Шаблоны: base.html, index.html, building.html (polling), result.html (скачивание + preview), search.html
- Запуск: `python -m diploma_builder.cli serve --port 8000` → 0.0.0.0 для preview

## Поток данных

```
Тема (строка)
  → Planner → план (JSON + Markdown)
  → Search → List[SourceRecord] (15, verified)
  → Bibliography → references.bib + gost.txt
  → Figures → 8 PNG (images/)
  → Writer → 5 MD глав + article.md (с [@cite])
  → DocxBuilder → thesis.docx (808 КБ, 8 img, 2 tbl)
  → PdfBuilder → thesis.pdf (1.1 МБ)
  → QuartoBuilder → quarto/*.qmd + references.bib
  → Web → download links
```

## Расширяемость
- Новый кластер в DISCIPLINE_TEMPLATES → кастомные заголовки глав
- Новый тип WorkType → добавить в WORK_STRUCTURES
- Новый график → метод в FigureFactory
- Новый поисковик → класс с .search() → добавить в SourceSearcher

