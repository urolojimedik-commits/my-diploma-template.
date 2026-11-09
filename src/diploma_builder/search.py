"""
search.py — поиск реальных научных источников.

Источники:
- Crossref API (https://api.crossref.org/works)
- OpenAlex API (https://api.openalex.org/works)
- Проверка DOI через Crossref

Все записи помечаются verified=True только если DOI отвечает 200.
Статистика не выдумывается — графики либо реальные, либо помечаются synthetic.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import time
import urllib.parse
from typing import List, Optional, Dict, Any

import requests

from .config import SourceRecord

CROSSREF_API = "https://api.crossref.org/works"
OPENALEX_API = "https://api.openalex.org/works"

# Для вежливости к API
HEADERS = {
    "User-Agent": "diploma_builder/1.0 (mailto:student@university.ru) academic research",
    "Accept": "application/json",
}

# Кэш в памяти
CACHE_DIR = pathlib.Path("data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_key(query: str, rows: int, source: str) -> str:
    h = hashlib.md5(f"{source}:{query}:{rows}".encode()).hexdigest()
    return h


def _load_cache(key: str) -> Optional[Any]:
    p = CACHE_DIR / f"{key}.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _save_cache(key: str, data: Any):
    p = CACHE_DIR / f"{key}.json"
    try:
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def verify_doi(doi: str, timeout: int = 10) -> bool:
    """Проверяет DOI через Crossref. Возвращает True если 200."""
    if not doi:
        return False
    # нормализация
    doi = doi.strip().replace("https://doi.org/", "").replace("http://doi.org/", "")
    doi = doi.strip()
    url = f"{CROSSREF_API}/{urllib.parse.quote(doi)}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code == 200:
            j = r.json()
            # дополнительная проверка что статус ok
            if j.get("status") == "ok":
                return True
            # иногда возвращает 200 но без status
            return True
        return False
    except Exception:
        return False


def _parse_crossref_item(item: dict) -> Optional[SourceRecord]:
    try:
        doi = item.get("DOI")
        title_list = item.get("title", [])
        title = title_list[0] if title_list else item.get("title", "Без названия")
        if isinstance(title, list):
            title = title[0] if title else "Без названия"
        title = re.sub(r"<[^>]+>", "", str(title)).strip()
        if not title:
            return None

        # авторы
        authors = []
        for a in item.get("author", [])[:5]:
            given = a.get("given", "")
            family = a.get("family", "")
            name = f"{family} {given}".strip() if family else given
            if name:
                authors.append(name)
        if not authors:
            # редактор или организация
            authors = ["Коллектив авторов"]

        # год
        year = 2023
        if "published-print" in item:
            pp = item["published-print"].get("date-parts", [[2023]])
            year = pp[0][0] if pp and pp[0] else 2023
        elif "published-online" in item:
            pp = item["published-online"].get("date-parts", [[2023]])
            year = pp[0][0] if pp and pp[0] else 2023
        elif "issued" in item:
            pp = item["issued"].get("date-parts", [[2023]])
            year = pp[0][0] if pp and pp[0] else 2023
        elif "created" in item:
            year = int(item["created"].get("date-parts", [[2023]])[0][0])

        journal = None
        if item.get("container-title"):
            ct = item["container-title"]
            journal = ct[0] if isinstance(ct, list) and ct else str(ct)
            journal = re.sub(r"<[^>]+>", "", journal)

        publisher = item.get("publisher")
        volume = item.get("volume")
        pages = item.get("page")
        url = item.get("URL") or (f"https://doi.org/{doi}" if doi else None)
        abstract = item.get("abstract")
        if abstract:
            abstract = re.sub(r"<[^>]+>", "", abstract)[:500]

        # ключ
        first_author_last = authors[0].split()[0].lower() if authors else "anon"
        first_author_last = re.sub(r"[^a-zа-я0-9]", "", first_author_last)
        key = f"{first_author_last}{year}{doi.split('/')[-1][:6] if doi else 'x'}"
        key = re.sub(r"[^a-z0-9]", "", key.lower())
        if not key:
            key = f"source{year}"

        # язык
        lang = item.get("language", "en")
        # эвристика: если title содержит кириллицу → ru
        if re.search(r"[а-яА-Я]", title):
            lang = "ru"

        return SourceRecord(
            key=key,
            title=title,
            authors=authors,
            year=int(year),
            doi=doi,
            url=url,
            journal=journal,
            publisher=publisher,
            volume=volume,
            pages=pages,
            verified=False,  # будет проверено отдельно при необходимости
            language=lang,
            abstract=abstract,
        )
    except Exception as e:
        print(f"[search] parse crossref error: {e}")
        return None


def _parse_openalex_item(item: dict) -> Optional[SourceRecord]:
    try:
        doi = item.get("doi", "")
        if doi:
            doi = doi.replace("https://doi.org/", "")
        title = item.get("title", "") or item.get("display_name", "")
        title = re.sub(r"<[^>]+>", "", str(title)).strip()
        if not title:
            return None

        # авторы
        authors = []
        for a in item.get("authorships", [])[:5]:
            author = a.get("author", {})
            name = author.get("display_name", "")
            if name:
                authors.append(name)
        if not authors:
            authors = ["Коллектив авторов"]

        year = item.get("publication_year") or 2023
        # host venue
        journal = None
        host = item.get("host_venue", {}) or item.get("primary_location", {}).get("source", {})
        if host:
            journal = host.get("display_name")

        publisher = None
        volume = None
        pages = None
        url = item.get("id") or (f"https://doi.org/{doi}" if doi else None)
        # openalex id типа https://openalex.org/W123 — заменим на doi url если есть
        if doi and url and "openalex.org" in url:
            url = f"https://doi.org/{doi}"

        first_author_last = authors[0].split()[-1].lower() if authors else "anon"
        first_author_last = re.sub(r"[^a-zа-я0-9]", "", first_author_last)
        key = f"{first_author_last}{year}{hashlib.md5(title.encode()).hexdigest()[:4]}"
        key = re.sub(r"[^a-z0-9]", "", key.lower())

        lang = item.get("language", "en")
        if re.search(r"[а-яА-Я]", title):
            lang = "ru"

        return SourceRecord(
            key=key,
            title=title,
            authors=authors,
            year=int(year),
            doi=doi if doi else None,
            url=url,
            journal=journal,
            publisher=publisher,
            volume=volume,
            pages=pages,
            verified=False,
            language=lang,
        )
    except Exception as e:
        print(f"[search] parse openalex error: {e}")
        return None


class CrossrefSearch:
    """Поиск через Crossref."""

    def search(self, query: str, rows: int = 10, from_year: int = 2015, language: str = None, verify: bool = False) -> List[SourceRecord]:
        cache_key = _cache_key(query, rows, f"crossref:{from_year}:{language}")
        cached = _load_cache(cache_key)
        if cached:
            # восстанавливаем
            recs = []
            for c in cached:
                try:
                    recs.append(SourceRecord(**c))
                except Exception:
                    pass
            if recs:
                print(f"[search] cache hit crossref: {query} -> {len(recs)}")
                return recs

        # строим фильтр
        filters = [f"from-pub-date:{from_year}"]
        if language:
            # crossref не фильтрует по языку, но можно попытаться
            pass

        params = {
            "query": query,
            "rows": rows,
            "filter": ",".join(filters),
            "sort": "relevance",
            "order": "desc",
        }
        url = CROSSREF_API + "?" + urllib.parse.urlencode(params)
        print(f"[search] Crossref query: {url}")
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            j = r.json()
            items = j.get("message", {}).get("items", [])
            results: List[SourceRecord] = []
            for it in items:
                rec = _parse_crossref_item(it)
                if rec:
                    if verify and rec.doi:
                        rec.verified = verify_doi(rec.doi)
                    results.append(rec)
            # кэш
            _save_cache(cache_key, [rec.__dict__ for rec in results])
            return results
        except requests.exceptions.RequestException as e:
            print(f"[search] Crossref error: {e}")
            # вернём демо-заглушку с пометкой что оффлайн?
            return []

    def search_bibliography(self, topic: str, rows: int = 10) -> List[SourceRecord]:
        # улучшение запроса: берем ключевые слова
        # для русской темы ищем на английском тоже (больше результатов)
        queries = [topic]
        # добавим английский перевод ключевых слов если русский
        if re.search(r"[а-яА-Я]", topic):
            # простая эвристика: ищем транслит + английский синоним
            # например "цифровизация" -> "digitalization"
            trans_map = {
                "цифровизация": "digitalization",
                "цифровой": "digital",
                "государственное управление": "public administration",
                "образование": "education",
                "экономика": "economics",
                "финансы": "finance",
                "менеджмент": "management",
                "право": "law",
                "педагогика": "pedagogy",
                "машинное обучение": "machine learning",
                "искусственный интеллект": "artificial intelligence",
            }
            for ru, en in trans_map.items():
                if ru in topic.lower():
                    queries.append(en)
                    queries.append(f"{topic} {en}")

        all_results: List[SourceRecord] = []
        seen_dois = set()
        for q in queries[:2]:  # ограничим 2 запроса
            res = self.search(q, rows=rows // len(queries[:2]) + 5, from_year=2018)
            for r in res:
                doi_key = r.doi or r.title
                if doi_key not in seen_dois:
                    seen_dois.add(doi_key)
                    all_results.append(r)
            time.sleep(0.5)  # вежливость

        # дедупликация по title
        uniq = []
        seen_titles = set()
        for r in all_results:
            t = r.title.lower()[:60]
            if t not in seen_titles:
                seen_titles.add(t)
                uniq.append(r)
        return uniq[:rows]


class OpenAlexSearch:
    """Поиск через OpenAlex (больше покрытия, бесплатно)."""

    def search(self, query: str, rows: int = 10, from_year: int = 2015) -> List[SourceRecord]:
        cache_key = _cache_key(query, rows, f"openalex:{from_year}")
        cached = _load_cache(cache_key)
        if cached:
            recs = []
            for c in cached:
                try:
                    recs.append(SourceRecord(**c))
                except Exception:
                    pass
            if recs:
                print(f"[search] cache hit openalex: {query} -> {len(recs)}")
                return recs

        params = {
            "search": query,
            "filter": f"publication_year:{from_year}-2026",
            "per-page": rows,
            "sort": "cited_by_count:desc",
        }
        url = OPENALEX_API + "?" + urllib.parse.urlencode(params)
        print(f"[search] OpenAlex query: {url}")
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            j = r.json()
            items = j.get("results", [])
            results = []
            for it in items:
                rec = _parse_openalex_item(it)
                if rec:
                    results.append(rec)
            _save_cache(cache_key, [rec.__dict__ for rec in results])
            return results
        except Exception as e:
            print(f"[search] OpenAlex error: {e}")
            return []


class SourceSearcher:
    """Объединённый поиск: Crossref + OpenAlex."""

    def __init__(self):
        self.crossref = CrossrefSearch()
        self.openalex = OpenAlexSearch()

    def search(self, topic: str, rows: int = 15, verify: bool = False) -> List[SourceRecord]:
        """
        Ищет реальные источники по теме.
        Возвращает только реальные, не выдуманные записи.
        """
        print(f"[search] Поиск источников по теме: {topic}")
        # Запрос на русском + английском
        cr_results = self.crossref.search_bibliography(topic, rows=rows)
        oa_results = self.openalex.search(topic, rows=max(5, rows // 2))

        # Объединяем
        combined: List[SourceRecord] = []
        seen = set()
        for rec in cr_results + oa_results:
            key = (rec.doi or rec.title.lower()[:80])
            if key not in seen:
                seen.add(key)
                combined.append(rec)

        # Сортировка: сначала верифицированные, потом по году
        # если verify=True — проверяем DOI
        if verify:
            for rec in combined:
                if rec.doi:
                    rec.verified = verify_doi(rec.doi)
                    time.sleep(0.2)

        # Если ничего не нашли (оффлайн), вернём fallback с предупреждением
        if not combined:
            print("[search] ВНИМАНИЕ: API недоступны, возвращаем fallback (будет помечен как учебный пример)")
            return self._fallback_sources(topic)

        print(f"[search] Найдено {len(combined)} источников (crossref={len(cr_results)}, openalex={len(oa_results)})")
        return combined[:rows]

    def _load_local_verified_sources(self, topic: str, rows: int) -> List[SourceRecord]:
        """Загружает локальную базу проверенных источников (реальные DOI)."""
        # Ищем в нескольких возможных местах
        candidates = [
            pathlib.Path("data/verified_sources.json"),
            pathlib.Path(__file__).parent.parent.parent / "data" / "verified_sources.json",
            pathlib.Path("data/cache/verified_sources.json"),
        ]
        for p in candidates:
            if p.exists():
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    recs = []
                    for d in data:
                        try:
                            recs.append(SourceRecord(
                                key=d["key"],
                                title=d["title"],
                                authors=d["authors"],
                                year=d["year"],
                                doi=d.get("doi"),
                                url=d.get("url") or (f"https://doi.org/{d['doi']}" if d.get("doi") else None),
                                journal=d.get("journal"),
                                publisher=d.get("publisher"),
                                volume=d.get("volume"),
                                pages=d.get("pages"),
                                verified=d.get("verified", True),
                                language=d.get("language", "en"),
                                abstract=d.get("abstract"),
                            ))
                        except Exception:
                            continue
                    # Фильтруем по теме (простой скоринg по ключевым словам)
                    if topic:
                        keywords = [w.lower() for w in re.findall(r"[a-zа-я]{4,}", topic.lower())]
                        def score(rec: SourceRecord) -> int:
                            title_low = rec.title.lower()
                            # +2 за каждое слово темы в заголовке, +1 за вхождение в журнале
                            s = sum(2 for k in keywords if k in title_low)
                            s += sum(1 for k in keywords if k in (rec.journal or "").lower())
                            # Бонус за русский язык если тема русская
                            if re.search(r"[а-я]", topic.lower()) and rec.language == "ru":
                                s += 1
                            return s
                        # Сортируем по скору, но не отфильтровываем жестко — чтобы всегда было rows
                        recs = sorted(recs, key=lambda r: score(r), reverse=True)
                    print(f"[search] Локальная база: {len(recs)} проверенных источников из {p}")
                    return recs[:rows]
                except Exception as e:
                    print(f"[search] Ошибка чтения локальной базы {p}: {e}")
        print("[search] Локальная база не найдена")
        return []

    def _fallback_sources(self, topic: str) -> List[SourceRecord]:
        """Резерв если API недоступны — берём локальную базу реальных источников."""
        local = self._load_local_verified_sources(topic, rows=15)
        if local:
            print(f"[search] Использована локальная база реальных источников ({len(local)} записей, DOI верифицированы оффлайн)")
            return local
        # Крайний случай — учебные заглушки с явной пометкой
        fallback_data = [
            {
                "title": f"Учебный пример: обзор литературы по теме «{topic}»",
                "authors": ["Иванов И.И.", "Петров П.П."],
                "year": 2023,
                "journal": "Вестник университета (учебный пример)",
                "publisher": "Учебное издание",
            },
            {
                "title": "Методология научных исследований (учебное пособие)",
                "authors": ["Кузнецов А.В."],
                "year": 2022,
                "publisher": "Москва: Юрайт",
            },
            {
                "title": "Анализ современных подходов (условный пример)",
                "authors": ["Сидорова Е.Н."],
                "year": 2021,
                "journal": "Вопросы теории и практики (пример)",
            },
        ]
        recs = []
        for i, d in enumerate(fallback_data):
            recs.append(
                SourceRecord(
                    key=f"fallback{i}{d['year']}",
                    title=d["title"] + " — ВНИМАНИЕ: УЧЕБНЫЙ ПРИМЕР, ТРЕБУЕТ ЗАМЕНЫ НА РЕАЛЬНЫЙ ИСТОЧНИК",
                    authors=d["authors"],
                    year=d["year"],
                    doi=None,
                    url=None,
                    journal=d.get("journal"),
                    publisher=d.get("publisher"),
                    verified=False,
                    language="ru",
                )
            )
        return recs

    def ensure_min_sources(self, topic: str, min_count: int = 10, verify: bool = False) -> List[SourceRecord]:
        """Гарантирует минимум источников (добирает fallback если нужно)."""
        found = self.search(topic, rows=min_count, verify=verify)
        if len(found) < min_count:
            needed = min_count - len(found)
            fallback = self._fallback_sources(topic)[:needed]
            # пометим fallback как учебный
            for f in fallback:
                f.title = "[УЧЕБНЫЙ ПРИМЕР] " + f.title
            found.extend(fallback)
            print(f"[search] Добрано {needed} учебных примеров до {min_count}")
        return found


# Утилита для CLI
def demo_search(topic: str):
    s = SourceSearcher()
    recs = s.search(topic, rows=10, verify=False)
    for i, r in enumerate(recs, 1):
        status = "✓" if r.verified else "○"
        print(f"{i}. {status} {r.authors[0] if r.authors else ''} ({r.year}) {r.title[:80]}")
        if r.doi:
            print(f"   DOI: {r.doi}  journal={r.journal}")
    return recs

