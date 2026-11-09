"""Профиль «Медицина»: чтение настроек и построение плана IMRAD.

Здесь же живут правила, которые защищают работу от выдуманных данных:

* ``DataPolicy`` — метки происхождения утверждений (источник / собственные
  данные / данных нет). Утверждение без метки не попадает в текст;
* ``check_work()`` — проверка объёма, числа источников и наличия собственных
  данных; если данных нет — возвращает вопросы к автору, а не числа.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..model import Plan, Topic
from ..settings import APP_DIR
from ..lang import get_language
from .sections import build_outline, flatten, outline_to_plan

try:  # PyYAML входит в requirements.txt
    import yaml
except ImportError:  # pragma: no cover — профиль тогда берётся из кода
    yaml = None


CONFIG_DIR = APP_DIR / "config"
MEDICINE_YML = CONFIG_DIR / "medicine.yml"
UNIVERSITY_YML = CONFIG_DIR / "university.yml"


def _read_yaml(path: Path) -> dict:
    if not path.exists() or yaml is None:
        return {}
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


# --------------------------------------------------------------------------- #
# Профиль
# --------------------------------------------------------------------------- #


@dataclass
class DataPolicy:
    """Разделение фактов публикаций и собственных данных автора."""

    label_source: str = "source"
    label_own_data: str = "own_data"
    label_unknown: str = "unknown"
    marker_missing: str = "Маълумот нокифоя"
    ask_questions: bool = True
    own_data_sections: tuple[str, ...] = ("ch2", "ch3")
    require_ethics: bool = True
    require_consent: bool = True
    min_n_warning: int = 30

    @classmethod
    def from_dict(cls, data: dict) -> "DataPolicy":
        data = data or {}
        labels = data.get("labels", {}) or {}
        missing = data.get("missing_data", {}) or {}
        own = data.get("own_data", {}) or {}
        return cls(
            label_source=labels.get("source", "source"),
            label_own_data=labels.get("own_data", "own_data"),
            label_unknown=labels.get("unknown", "unknown"),
            marker_missing=missing.get("marker_tg", "Маълумот нокифоя"),
            ask_questions=bool(missing.get("ask_questions", True)),
            own_data_sections=tuple(own.get("allowed_sections", ("ch2", "ch3"))),
            require_ethics=bool(own.get("require_ethics_block", True)),
            require_consent=bool(own.get("require_consent_note", True)),
            min_n_warning=int(own.get("min_n_warning", 30)),
        )


@dataclass
class SourcePolicy:
    databases: list[str] = field(default_factory=lambda: ["pubmed", "europepmc", "crossref"])
    require_doi_or_pmid: bool = True
    verify_doi: bool = True
    min_year: int = 2010
    prefer_guidelines: bool = True
    guideline_sources: list[str] = field(default_factory=list)
    reject_unverified: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "SourcePolicy":
        data = data or {}
        return cls(
            databases=list(data.get("preferred_databases", ["pubmed", "europepmc", "crossref"])),
            require_doi_or_pmid=bool(data.get("require_doi_or_pmid", True)),
            verify_doi=bool(data.get("verify_doi", True)),
            min_year=int(data.get("min_year", 2010)),
            prefer_guidelines=bool(data.get("prefer_guidelines", True)),
            guideline_sources=list(data.get("guideline_sources", [])),
            reject_unverified=bool(data.get("reject_unverified", True)),
        )


@dataclass
class StatPolicy:
    decimal_separator: str = ","
    p_format: str = "p<0,05"
    p_decimals: int = 3
    mean_sd: str = "M±SD"
    median_iqr: str = "Me [Q1; Q3]"
    ci_format: str = "95 % ДИ: {lo}–{hi}"
    percent_decimals: int = 1
    alpha: float = 0.05

    @classmethod
    def from_dict(cls, data: dict) -> "StatPolicy":
        data = data or {}
        return cls(
            decimal_separator=data.get("decimal_separator", ","),
            p_format=data.get("p_format", "p<0,05"),
            p_decimals=int(data.get("p_value_decimals", 3)),
            mean_sd=data.get("mean_sd", "M±SD"),
            median_iqr=data.get("median_iqr", "Me [Q1; Q3]"),
            ci_format=data.get("ci_format", "95 % ДИ: {lo}–{hi}"),
            percent_decimals=int(data.get("percent_decimals", 1)),
            alpha=float(data.get("significance_level", 0.05)),
        )

    def mean_sd_str(self, mean: float, sd: float, digits: int = 1) -> str:
        return f"{self.fmt(mean, digits)}±{self.fmt(sd, digits)}"

    def median_iqr_str(self, median: float, q1: float, q3: float, digits: int = 1) -> str:
        return (
            f"{self.fmt(median, digits)} "
            f"[{self.fmt(q1, digits)}; {self.fmt(q3, digits)}]"
        )

    def p_str(self, value: float | None) -> str:
        if value is None:
            return "p = —"
        if value < self.alpha:
            return self.p_format.replace(",", self.decimal_separator)
        return f"p = {self.fmt(value, self.p_decimals)}"

    def ci_str(self, lo: float, hi: float, level: int = 95, digits: int | None = None) -> str:
        d = digits if digits is not None else self.auto_digits(lo, hi)
        return f"{level} % ДИ: {self.fmt(lo, d)}–{self.fmt(hi, d)}"

    @staticmethod
    def auto_digits(*values: float) -> int:
        """Единицы — один знак, доли (p, AUC, ДИ) — два."""
        return 2 if any(abs(float(v)) < 1 for v in values) else 1

    def fmt(self, value: float, digits: int | None = None) -> str:
        from decimal import Decimal, ROUND_HALF_UP

        d = digits if digits is not None else self.auto_digits(value)
        q = Decimal(1).scaleb(-d)
        text = f"{Decimal(str(float(value))).quantize(q, rounding=ROUND_HALF_UP):f}"
        return text.replace(".", self.decimal_separator)

    def percent_str(self, value: float) -> str:
        return f"{self.fmt(value, self.percent_decimals)} %"


@dataclass
class MedicalProfile:
    """Сводная конфигурация: университет + медицина + политика данных."""

    university: dict = field(default_factory=dict)
    medicine: dict = field(default_factory=dict)
    work: dict = field(default_factory=dict)
    layout: dict = field(default_factory=dict)
    gost: dict = field(default_factory=dict)
    volumes: dict = field(default_factory=dict)
    data_policy: DataPolicy = field(default_factory=DataPolicy)
    source_policy: SourcePolicy = field(default_factory=SourcePolicy)
    stats: StatPolicy = field(default_factory=StatPolicy)

    # ------------------------------------------------------------------ загрузка
    @classmethod
    def load(cls) -> "MedicalProfile":
        uni = _read_yaml(UNIVERSITY_YML)
        med = _read_yaml(MEDICINE_YML)
        return cls(
            university=uni.get("university", {}) or {},
            medicine=med,
            work=uni.get("work", {}) or {},
            layout=uni.get("layout", {}) or {},
            gost=uni.get("gost", {}) or {},
            volumes=uni.get("volumes", {}) or {},
            data_policy=DataPolicy.from_dict(med.get("data_policy", {})),
            source_policy=SourcePolicy.from_dict(med.get("sources", {})),
            stats=StatPolicy.from_dict(med.get("statistics", {})),
        )

    # -------------------------------------------------------------------- геттеры
    @property
    def main_language(self) -> str:
        return (self.work or {}).get("main_language", "tg")

    @property
    def default_work_type(self) -> str:
        return (self.work or {}).get("default_type", "diploma")

    @property
    def numbering(self) -> str:
        return (self.gost or {}).get("numbering", "per_chapter")

    def n_chapters(self, work_type: str) -> int:
        structure = (self.medicine or {}).get("structure", {}) or {}
        cfg = structure.get(work_type, {}) or {}
        return int(cfg.get("chapters", 2 if work_type == "course" else 4))

    def pages_range(self, work_type: str) -> tuple[int, int]:
        key = f"{work_type}_pages"
        rng = (self.volumes or {}).get(key, [50, 80]) or [50, 80]
        return int(rng[0]), int(rng[1])

    def sources_min(self, work_type: str) -> int:
        table = (self.volumes or {}).get("sources_min", {}) or {}
        return int(table.get(work_type, 20 if work_type == "course" else 40))

    def own_data_required(self, work_type: str) -> bool:
        table = (self.volumes or {}).get("own_data_required", {}) or {}
        return bool(table.get(work_type, work_type in ("diploma", "master")))

    def required_sections(self) -> list[str]:
        uni_list = (self.university,)
        _ = uni_list
        return list((self._raw_university().get("required_sections", []) or []))

    def _raw_university(self) -> dict:
        return _read_yaml(UNIVERSITY_YML).get("university", {}) or {}

    def raw(self) -> dict:
        return _read_yaml(UNIVERSITY_YML)


WORK_YML = CONFIG_DIR / "work.yml"
WORK_EXAMPLE_YML = CONFIG_DIR / "work.example.yml"


def load_work(path: Path | None = None) -> dict:
    """Описание конкретной работы (автор, тема, наличие своих данных).

    Берётся ``config/work.yml``; если его нет — ``config/work.example.yml``
    (шаблон с пустыми полями, данные не подставляются).
    """
    path = path or (WORK_YML if WORK_YML.exists() else WORK_EXAMPLE_YML)
    return _read_yaml(path)


_PROFILE_CACHE: MedicalProfile | None = None


def get_profile(reload: bool = False) -> MedicalProfile:
    global _PROFILE_CACHE
    if _PROFILE_CACHE is None or reload:
        _PROFILE_CACHE = MedicalProfile.load()
    return _PROFILE_CACHE


# --------------------------------------------------------------------------- #
# Построение плана
# --------------------------------------------------------------------------- #


def build_medical_plan(
    topic: Topic,
    work_type: str | None = None,
    profile: MedicalProfile | None = None,
    with_appendices: bool = True,
) -> tuple[Plan, list]:
    """План медицинской работы по схеме IMRAD.

    Возвращает ``(plan, outline)`` — ``outline`` используется рендерерами
    (Word/PDF) для автоматической нумерации и для титульного листа.
    """
    profile = profile or get_profile()
    wt = work_type or topic.work_type or profile.default_work_type
    outline = build_outline(
        work_type=wt,
        n_chapters=profile.n_chapters(wt),
        with_appendices=with_appendices,
    )
    plan = outline_to_plan(outline, topic)
    return plan, outline


# --------------------------------------------------------------------------- #
# Проверки работы
# --------------------------------------------------------------------------- #


@dataclass
class CheckResult:
    ok: bool
    level: str  # info | warn | error
    code: str
    message: str
    question: str = ""  # вопрос к автору, если данных не хватает


def check_work(
    work_type: str,
    profile: MedicalProfile | None = None,
    n_sources: int = 0,
    n_verified: int = 0,
    n_pages: int | None = None,
    own_data: dict | None = None,
    lang_code: str = "tg",
) -> list[CheckResult]:
    """Проверка соответствия требованиям университета.

    Если собственных клинических данных нет — вместо цифр в работу попадает
    пометка «Маълумот нокифоя», а автору задаются вопросы (``question``).
    """
    profile = profile or get_profile()
    lang = get_language(lang_code)
    out: list[CheckResult] = []

    lo, hi = profile.pages_range(work_type)
    if n_pages is not None:
        if n_pages < lo:
            out.append(
                CheckResult(
                    False, "warn", "pages_low",
                    f"Ҳаҷми кор {n_pages} саҳифа — камтар аз талабот ({lo}–{hi} саҳифа).",
                )
            )
        elif n_pages > hi:
            out.append(
                CheckResult(
                    True, "info", "pages_high",
                    f"Ҳаҷми кор {n_pages} саҳифа — бештар аз тавсия ({lo}–{hi} саҳифа).",
                )
            )

    need = profile.sources_min(work_type)
    if n_verified < need:
        out.append(
            CheckResult(
                False, "warn", "sources_low",
                f"Сарчашмаҳои санҷидашуда: {n_verified} аз {need} (ҳамагӣ {n_sources}).",
                "Оё темаи корро васеъ кардан мумкин аст ё манбаъҳои иловагӣ доред?",
            )
        )

    own = own_data or {}
    if profile.own_data_required(work_type) and not own.get("available"):
        out.append(
            CheckResult(
                False, "warn", "own_data_missing",
                f"Барои кори {work_type} маълумоти шахсии клиникӣ лозим аст; "
                f"ба ҷои он дар бобҳои 2 ва 3 ишораи «{lang.missing_data()}» гузошта мешавад.",
                "Лутфан файли маълумотҳоро (CSV/Excel) фиристед ё тарҳи таҳқиқотро "
                "(намуна, гурӯҳҳо, меъёрҳо) тавсиф кунед.",
            )
        )
    elif own.get("available"):
        n = own.get("n_expected")
        if n is not None and n < profile.data_policy.min_n_warning:
            out.append(
                CheckResult(
                    True, "warn", "sample_small",
                    f"Ҳаҷми интихоб n={n} — камтар аз {profile.data_policy.min_n_warning}; "
                    "инро дар маҳдудиятҳо қайд кунед.",
                )
            )
        if profile.data_policy.require_ethics and not own.get("ethics_approved"):
            out.append(
                CheckResult(
                    False, "warn", "ethics_missing",
                    "Барои таҳқиқоти клиникӣ иҷозати Кумитаи ахлоқ лозим аст.",
                    "Оё тасдиқи Кумитаи ахлоқ (рақами протокол, сана) мавҷуд аст?",
                )
            )
        if profile.data_policy.require_consent and not own.get("consent_obtained"):
            out.append(
                CheckResult(
                    False, "warn", "consent_missing",
                    "Дар боби 2 бояд қайди ризоияти хаттии беморон бошад.",
                    "Оё ризоияти хаттии беморон гирифта шудааст?",
                )
            )
    return out


def questions_for_missing_data(lang_code: str = "tg") -> list[str]:
    """Список вопросов, которые система задаёт автору вместо генерации данных."""
    if lang_code == "ru":
        return [
            "Есть ли у вас собственные данные (файл CSV/Excel) или только обзор литературы?",
            "Какой дизайн исследования: проспективный, ретроспективный, поперечный?",
            "Критерии включения и исключения пациентов?",
            "Объём выборки n и как сформированы группы сравнения?",
            "Какие показатели measured и в каких единицах?",
            "Период набора материала (даты) и база исследования?",
            "Есть ли одобрение этического комитета и письменное согласие пациентов?",
        ]
    return [
        "Оё маълумоти шахсии клиникии шумо (файли CSV/Excel) ҳаст ё танҳо баррасии адабиёт?",
        "Тарҳи таҳқиқот: ояндадор, ретроспективӣ ё буришӣ?",
        "Меъёрҳои дохилшавӣ ва хориҷшавии беморон кадомҳоянд?",
        "Ҳаҷми интихоб (n) ва тарзи ташкили гурӯҳҳои муқоисавӣ?",
        "Кадом нишондиҳандаҳо чен карда шуданд ва бо кадом воҳидҳо?",
        "Давраи ҷамъоварии мавод (санаҳо) ва пойгоҳи таҳқиқот?",
        "Оё иҷозати Кумитаи ахлоқ ва ризоияти хаттии беморон мавҷуд аст?",
    ]
