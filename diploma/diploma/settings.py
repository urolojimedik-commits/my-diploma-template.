"""Настройки и расположение каталогов системы."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Каталог пакета: <repo>/diploma/diploma
PACKAGE_DIR = Path(__file__).resolve().parent
APP_DIR = PACKAGE_DIR.parent  # <repo>/diploma
REPO_ROOT = APP_DIR.parent  # <repo>

DATA_DIR = APP_DIR / "data"
ASSETS_DIR = APP_DIR / "assets"
BUILD_DIR = APP_DIR / "build"

# Параметры по умолчанию, переопределяются через CLI/веб-интерфейс.
DEFAULT_BIB_STYLE = "gost"  # gost | apa | ieee | vancouver
DEFAULT_LANGUAGE = "ru-RU"
DEFAULT_PDF_ENGINE = "auto"  # auto | latex | builtin


@dataclass
class Settings:
    """Конфигурация одного прогона конвейера."""

    topic: str = ""
    work_type: str = "diploma"  # diploma | course | bachelor | master
    out_dir: Path = BUILD_DIR
    bib_style: str = DEFAULT_BIB_STYLE
    language: str = DEFAULT_LANGUAGE
    pdf_engine: str = DEFAULT_PDF_ENGINE
    max_sources: int = 20
    search_offline: bool = False  # не обращаться к сети (только проверенный корпус)
    verify_doi: bool = True
    author: str = "Иванов И. И."
    group: str = ""
    chair: str = ""
    supervisor: str = ""
    institution: str = ""
    city: str = ""
    year: int | None = None
    text_backend: str = "deterministic"  # deterministic | llm
    llm_model: str = ""
    llm_base_url: str = ""
    make_zip: bool = True
    export_quarto: bool = True
    figure_dpi: int = 200
    line_spacing: float = 1.5
    font_size_pt: int = 14
    extra: dict = field(default_factory=dict)

    def ensure_dirs(self) -> None:
        self.out_dir = Path(self.out_dir)
        (self.out_dir / "media").mkdir(parents=True, exist_ok=True)
        (self.out_dir / "data").mkdir(parents=True, exist_ok=True)

    @property
    def work_type_ru(self) -> str:
        return {
            "diploma": "выпускная квалификационная работа",
            "bachelor": "выпускная квалификационная работа (бакалавриат)",
            "master": "выпускная квалификационная работа (магистратура)",
            "course": "курсовая работа",
        }.get(self.work_type, "выпускная квалификационная работа")


def load_dotenv(path: Path | None = None) -> None:
    """Минималистичная поддержка .env (без внешних зависимостей)."""
    path = path or (REPO_ROOT / ".env")
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def has_pandoc() -> bool:
    from .render.pandoc_utils import pandoc_available

    return pandoc_available()


def has_quarto() -> bool:
    from shutil import which

    return which("quarto") is not None


def has_latex() -> bool:
    from shutil import which

    return any(which(x) for x in ("xelatex", "pdflatex", "lualatex", "tectonic"))
