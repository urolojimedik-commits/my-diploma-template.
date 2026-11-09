"""Провайдеры поиска реальных научных источников.

Реализованы публичные API, не требующие ключей:

* **Crossref**   — https://api.crossref.org (метаданные DOI, ~150 млн записей);
* **OpenAlex**   — https://api.openalex.org (агрегированный индекс);
* **arXiv**      — http://export.arxiv.org/api/query (препринты);
* **Semantic Scholar** — https://api.semanticscholar.org (граф цитирований);
* **Seed corpus**— локальный проверенный корпус (работает без интернета).

Ни один провайдер не «придумывает» записи: возвращаются только те поля,
которые прислал API. Если сеть недоступна, провайдер поднимает
``ProviderUnavailable``, и конвейер переходит на проверенный корпус,
явно помечая этот факт в отчёте.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

from ..model import Author, Source

USER_AGENT = "diploma-automation/1.0 (academic writing assistant; mailto:diploma-agent@example.org)"
DEFAULT_TIMEOUT = 20
DEFAULT_MAILTO = "diploma-agent@example.org"


class ProviderUnavailable(RuntimeError):
    """Провайдер недоступен (нет сети, тайм-аут, ошибка API)."""


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #


def http_get_json(url: str, timeout: int = DEFAULT_TIMEOUT, headers: dict | None = None) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, TimeoutError) as exc:  # сеть недоступна
        raise ProviderUnavailable(f"{url}: {exc}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # arXiv и некоторые прокси отдают XML/текст — разбираем вызывающим кодом
        return raw


def http_get_text(url: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise ProviderUnavailable(f"{url}: {exc}") from exc


# --------------------------------------------------------------------------- #
# Нормализация
# --------------------------------------------------------------------------- #

_JATS_RE = re.compile(r"<[^>]+>")


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = _JATS_RE.sub(" ", value)
    value = value.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", " ", value).strip()


def make_key(authors: list[Author], year: int | None, title: str) -> str:
    """Стабильный цитатный ключ вида ``yildirim2021``."""
    base = ""
    if authors and authors[0].family:
        base = re.sub(r"[^a-zа-яё]", "", authors[0].family.lower())
        base = base[:18]
    if not base:
        words = [w for w in re.split(r"\W+", title.lower()) if len(w) > 3]
        base = (words[0] if words else "ref")[:18]
    return f"{base}{year or ''}".strip("_") or "ref"


def dedupe_key(source: Source) -> str:
    if source.doi:
        return "doi:" + source.doi.lower()
    return "t:" + re.sub(r"\W+", "", source.title.lower())[:80]


# --------------------------------------------------------------------------- #
# Crossref
# --------------------------------------------------------------------------- #

SELECT_FIELDS = (
    "DOI,title,author,issued,container-title,volume,issue,page,publisher,"
    "type,abstract,URL,language,short-container-title,ISSN"
)


class CrossrefProvider:
    name = "crossref"
    base = "https://api.crossref.org/works"

    def search(self, query: str, max_results: int = 20) -> list[Source]:
        params = {
            "query.bibliographic": query,
            "rows": str(max_results),
            "select": SELECT_FIELDS,
            "mailto": DEFAULT_MAILTO,
        }
        url = f"{self.base}?{urllib.parse.urlencode(params)}"
        data = http_get_json(url)
        items = data.get("message", {}).get("items", []) if isinstance(data, dict) else []
        return [s for s in (self._parse(i) for i in items) if s]

    def by_doi(self, doi: str) -> Source | None:
        url = f"{self.base}/{urllib.parse.quote(doi)}?mailto={DEFAULT_MAILTO}"
        data = http_get_json(url)
        if isinstance(data, dict) and data.get("status") == "ok":
            return self._parse(data.get("message", {}))
        return None

    def _parse(self, item: dict) -> Source | None:
        if not item.get("DOI"):
            return None
        title = clean_text((item.get("title") or [""])[0])
        if not title:
            return None
        authors: list[Author] = []
        for a in item.get("author") or []:
            family = (a.get("family") or "").strip()
            given = (a.get("given") or "").strip()
            if not family:
                # иногда Crossref кладёт всё имя в поле name
                name = (a.get("name") or "").strip()
                if not name:
                    continue
                parts = name.split()
                family, given = (parts[0], " ".join(parts[1:]))
            authors.append(Author(family=family, given=given))
        year = None
        for field_name in ("issued", "published-print", "published-online", "created"):
            parts = (item.get(field_name) or {}).get("date-parts") or []
            if parts and parts[0] and parts[0][0]:
                year = int(parts[0][0])
                break
        issued = (item.get("issued") or {}).get("date-parts") or [[None]]
        year = issued[0][0] if issued and issued[0] else year
        container = item.get("container-title") or []
        abstract = clean_text(item.get("abstract"))
        return Source(
            key=make_key(authors, year, title),
            title=title,
            authors=authors,
            year=year,
            venue=clean_text(container[0]) if container else "",
            volume=item.get("volume") or "",
            number=item.get("issue") or "",
            pages=item.get("page") or "",
            publisher=item.get("publisher") or "",
            doi=item.get("DOI"),
            url=item.get("URL") or (f"https://doi.org/{item['DOI']}" if item.get("DOI") else ""),
            type=item.get("type") or "article-journal",
            language=(item.get("language") or "en"),
            provider=self.name,
            abstract=abstract,
        )


# --------------------------------------------------------------------------- #
# OpenAlex
# --------------------------------------------------------------------------- #


class OpenAlexProvider:
    name = "openalex"
    base = "https://api.openalex.org/works"

    def search(self, query: str, max_results: int = 20) -> list[Source]:
        params = {
            "search": query,
            "per-page": str(min(max_results, 50)),
            "mailto": DEFAULT_MAILTO,
        }
        url = f"{self.base}?{urllib.parse.urlencode(params)}"
        data = http_get_json(url)
        items = data.get("results", []) if isinstance(data, dict) else []
        return [s for s in (self._parse(i) for i in items) if s]

    def _parse(self, item: dict) -> Source | None:
        title = clean_text(item.get("title") or item.get("display_name"))
        if not title:
            return None
        authors: list[Author] = []
        for a in item.get("authorships") or []:
            name = ((a.get("author") or {}).get("display_name") or "").strip()
            if not name:
                continue
            parts = name.split()
            authors.append(Author(family=parts[-1], given=" ".join(parts[:-1])))
        year = item.get("publication_year")
        venue = ""
        loc = item.get("primary_location") or {}
        src = loc.get("source") or {}
        if src:
            venue = clean_text(src.get("display_name"))
        biblio = item.get("biblio") or {}
        doi = (item.get("doi") or "").replace("https://doi.org/", "") or None
        abstract = reconstruct_openalex_abstract(item.get("abstract_inverted_index"))
        return Source(
            key=make_key(authors, year, title),
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            volume=biblio.get("volume") or "",
            number=biblio.get("issue") or "",
            pages=(biblio.get("first_page") or "")
            + (f"-{biblio['last_page']}" if biblio.get("last_page") else ""),
            publisher=(src.get("host_organization_name") or ""),
            doi=doi,
            url=item.get("doi") or item.get("id") or "",
            type=(item.get("type") or "article-journal"),
            language=item.get("language") or "en",
            provider=self.name,
            abstract=abstract,
        )


def reconstruct_openalex_abstract(index: dict | None) -> str:
    if not index:
        return ""
    positions: dict[int, str] = {}
    for word, places in index.items():
        for p in places:
            positions[p] = word
    return clean_text(" ".join(positions[i] for i in sorted(positions)))


# --------------------------------------------------------------------------- #
# arXiv
# --------------------------------------------------------------------------- #

_ARXIV_TAG = re.compile(r"<(?P<tag>[a-zA-Z:]+)>(?P<val>.*?)</(?P=tag)>", re.S)


class ArxivProvider:
    name = "arxiv"
    base = "http://export.arxiv.org/api/query"

    def search(self, query: str, max_results: int = 20) -> list[Source]:
        params = {
            "search_query": f"all:{query}",
            "start": "0",
            "max_results": str(max_results),
        }
        url = f"{self.base}?{urllib.parse.urlencode(params)}"
        xml = http_get_text(url, timeout=30)
        return self._parse(xml)

    def _parse(self, xml: str) -> list[Source]:
        out: list[Source] = []
        entries = re.findall(r"<entry>(.*?)</entry>", xml, re.S)
        for entry in entries:
            def tag(name: str) -> str:
                m = _ARXIV_TAG.search(entry.replace(f"<{name}>", f"<{name}>"))
                if m:
                    return clean_text(m.group("val"))
                m = re.search(rf"<{name}[^>]*>(.*?)</{name}>", entry, re.S)
                return clean_text(m.group(1)) if m else ""

            title = tag("title")
            if not title:
                continue
            authors = []
            for a in re.findall(r"<author>(.*?)</author>", entry, re.S):
                m = re.search(r"<name>(.*?)</name>", a, re.S)
                if not m:
                    continue
                parts = clean_text(m.group(1)).split()
                authors.append(Author(family=parts[-1], given=" ".join(parts[:-1])))
            published = tag("published")[:4]
            doi = tag("arxiv:doi") or ""
            arxiv_id = tag("id")
            year = int(published) if published.isdigit() else None
            out.append(
                Source(
                    key=make_key(authors, year, title),
                    title=title,
                    authors=authors,
                    year=year,
                    venue="arXiv preprint",
                    doi=doi or None,
                    url=arxiv_id,
                    type="preprint",
                    provider=self.name,
                    abstract=tag("summary"),
                )
            )
        return out


# --------------------------------------------------------------------------- #
# Semantic Scholar
# --------------------------------------------------------------------------- #


class SemanticScholarProvider:
    name = "semanticscholar"
    base = "https://api.semanticscholar.org/graph/v1/paper/search"

    def search(self, query: str, max_results: int = 20) -> list[Source]:
        params = {
            "query": query,
            "limit": str(min(max_results, 100)),
            "fields": "title,abstract,year,venue,authors,externalIds,publicationTypes,openAccessPdf",
        }
        url = f"{self.base}?{urllib.parse.urlencode(params)}"
        data = http_get_json(url)
        items = data.get("data", []) if isinstance(data, dict) else []
        out: list[Source] = []
        for item in items:
            title = clean_text(item.get("title"))
            if not title:
                continue
            authors = []
            for a in item.get("authors") or []:
                name = (a.get("name") or "").strip()
                if not name:
                    continue
                parts = name.split()
                authors.append(Author(family=parts[-1], given=" ".join(parts[:-1])))
            ext = item.get("externalIds") or {}
            doi = ext.get("DOI")
            year = item.get("year")
            out.append(
                Source(
                    key=make_key(authors, year, title),
                    title=title,
                    authors=authors,
                    year=year,
                    venue=clean_text(item.get("venue")),
                    doi=doi,
                    url=(f"https://doi.org/{doi}" if doi else ""),
                    provider=self.name,
                    abstract=clean_text(item.get("abstract")),
                )
            )
        return out


# --------------------------------------------------------------------------- #
# Локальный проверенный корпус
# --------------------------------------------------------------------------- #


class SeedProvider:
    """Проверенный офлайн-корпус (``data/seed_sources.json``).

    Записи в корпусе уже прошли проверку через Crossref API (см. поля
    ``verified_via`` и ``verified_at``) и содержат выверенные выдержки на
    русском языке, поэтому пригодны для цитирования без доступа к сети.
    """

    name = "seed"
    path = None

    def __init__(self, path=None):
        from ..settings import DATA_DIR

        self.path = Path(path) if path else (DATA_DIR / "seed_sources.json")

    def load(self) -> list[Source]:
        if not Path(self.path).exists():
            return []
        raw = json.loads(Path(self.path).read_text(encoding="utf-8"))
        sources = []
        for item in raw.get("sources", []):
            authors = [Author(**a) for a in item.pop("authors", [])]
            sources.append(Source(authors=authors, **item))
        return sources

    def search(self, query: str, max_results: int = 20) -> list[Source]:
        # Корпус не ищет по сети: он фильтруется поисковым оркестратором.
        return self.load()


# --------------------------------------------------------------------------- #
# Реестр
# --------------------------------------------------------------------------- #

PROVIDERS = {
    "crossref": CrossrefProvider,
    "openalex": OpenAlexProvider,
    "arxiv": ArxivProvider,
    "semanticscholar": SemanticScholarProvider,
    "seed": SeedProvider,
}

DEFAULT_ONLINE_PROVIDERS = ["crossref", "semanticscholar", "openalex", "arxiv"]


def get_provider(name: str):
    cls = PROVIDERS.get(name)
    if cls is None:
        raise KeyError(f"Неизвестный провайдер: {name}")
    return cls()


def search_provider(name: str, query: str, max_results: int = 20) -> list[Source]:
    """Безопасный вызов провайдера: сетевые сбои не роняют конвейер."""
    try:
        return get_provider(name).search(query, max_results)
    except ProviderUnavailable:
        return []
    except Exception:  # битые записи API не должны прерывать поиск
        return []
