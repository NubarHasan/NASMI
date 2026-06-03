from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Final

_DEFAULT_PIVOT_YEAR: Final[int] = 30
_DEFAULT_CENTURY_20: Final[int] = 2000
_DEFAULT_CENTURY_19: Final[int] = 1900
_MAX_HUMAN_AGE: Final[int] = 120
_MAX_EXPIRY_YEARS: Final[int] = 30

_GERMAN_DATE_PATTERNS: Final[list[tuple[re.Pattern[str], bool]]] = [
    (re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$"), False),
    (re.compile(r"^(\d{1,2})-(\d{1,2})-(\d{4})$"), False),
    (re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$"), False),
    (re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{2})$"), True),
    (re.compile(r"^(\d{1,2})-(\d{1,2})-(\d{2})$"), True),
]

_ISO_PATTERN: Final[re.Pattern[str]] = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


class GermanDateStatus(StrEnum):
    VALID = "VALID"
    INVALID_FORMAT = "INVALID_FORMAT"
    INVALID_DATE = "INVALID_DATE"


@dataclass(frozen=True)
class GermanDateParseResult:
    status: GermanDateStatus
    value: date | None
    raw: str
    errors: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == GermanDateStatus.VALID

    @classmethod
    def ok(cls, value: date, raw: str) -> GermanDateParseResult:
        return cls(status=GermanDateStatus.VALID, value=value, raw=raw, errors=())

    @classmethod
    def fail(
        cls,
        status: GermanDateStatus,
        raw: str,
        reason: str,
    ) -> GermanDateParseResult:
        return cls(status=status, value=None, raw=raw, errors=(reason,))


def resolve_century(
    yy: int,
    pivot_year: int = _DEFAULT_PIVOT_YEAR,
) -> int:
    if not (0 <= yy <= 99):
        raise ValueError(f"yy must be 0-99, got {yy}")
    return _DEFAULT_CENTURY_20 + yy if yy <= pivot_year else _DEFAULT_CENTURY_19 + yy


def _safe_future_date(base: date, years: int) -> date:
    try:
        return date(base.year + years, base.month, base.day)
    except ValueError:
        return date(base.year + years, base.month, 28)


def _make_date(year: int, month: int, day: int, raw: str) -> GermanDateParseResult:
    try:
        return GermanDateParseResult.ok(date(year, month, day), raw)
    except ValueError as exc:
        return GermanDateParseResult.fail(GermanDateStatus.INVALID_DATE, raw, str(exc))


def parse_mrz_date(
    value: str,
    pivot_year: int = _DEFAULT_PIVOT_YEAR,
) -> GermanDateParseResult:
    raw = value.strip()
    if len(raw) != 6 or not raw.isdigit():
        return GermanDateParseResult.fail(
            GermanDateStatus.INVALID_FORMAT,
            raw,
            f"MRZ date must be 6 digits, got {raw!r}",
        )
    yy = int(raw[0:2])
    month = int(raw[2:4])
    day = int(raw[4:6])
    year = resolve_century(yy, pivot_year)
    return _make_date(year, month, day, raw)


def parse_german_date(
    value: str,
    pivot_year: int = _DEFAULT_PIVOT_YEAR,
) -> GermanDateParseResult:
    raw = value.strip()

    m = _ISO_PATTERN.match(raw)
    if m:
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return _make_date(year, month, day, raw)

    for pattern, two_digit_year in _GERMAN_DATE_PATTERNS:
        m = pattern.match(raw)
        if m is None:
            continue
        day_v, month_v, year_v = int(m.group(1)), int(m.group(2)), int(m.group(3))
        year_full = resolve_century(year_v, pivot_year) if two_digit_year else year_v
        return _make_date(year_full, month_v, day_v, raw)

    return GermanDateParseResult.fail(
        GermanDateStatus.INVALID_FORMAT,
        raw,
        f"unrecognized date format: {raw!r}",
    )


def try_parse_date(
    value: str,
    pivot_year: int = _DEFAULT_PIVOT_YEAR,
) -> GermanDateParseResult:
    raw = value.strip()
    if len(raw) == 6 and raw.isdigit():
        return parse_mrz_date(raw, pivot_year)
    return parse_german_date(raw, pivot_year)


def is_past_date(d: date) -> bool:
    return d < date.today()


def is_future_date(d: date) -> bool:
    return d > date.today()


def validate_birth_date(
    value: str,
    pivot_year: int = _DEFAULT_PIVOT_YEAR,
) -> GermanDateParseResult:
    result = try_parse_date(value, pivot_year)
    if not result.is_valid:
        return result
    assert result.value is not None
    dob = result.value
    today = date.today()
    if not is_past_date(dob):
        return GermanDateParseResult.fail(
            GermanDateStatus.INVALID_DATE,
            value,
            f"birth date must be in the past, got {dob.isoformat()}",
        )
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if age > _MAX_HUMAN_AGE:
        return GermanDateParseResult.fail(
            GermanDateStatus.INVALID_DATE,
            value,
            f"birth date implies age {age} > {_MAX_HUMAN_AGE}, likely OCR error",
        )
    return result


def validate_expiry_date(
    value: str,
    pivot_year: int = _DEFAULT_PIVOT_YEAR,
) -> GermanDateParseResult:
    result = try_parse_date(value, pivot_year)
    if not result.is_valid:
        return result
    assert result.value is not None
    expiry = result.value
    today = date.today()
    if not is_future_date(expiry):
        return GermanDateParseResult.fail(
            GermanDateStatus.INVALID_DATE,
            value,
            f"expiry date must be in the future, got {expiry.isoformat()}",
        )
    max_expiry = _safe_future_date(today, _MAX_EXPIRY_YEARS)
    if expiry > max_expiry:
        return GermanDateParseResult.fail(
            GermanDateStatus.INVALID_DATE,
            value,
            f"expiry date {expiry.isoformat()} exceeds {_MAX_EXPIRY_YEARS}-year limit",
        )
    return result
