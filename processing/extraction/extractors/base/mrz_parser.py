from __future__ import annotations

import calendar
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final

_TD1_LINES: Final[int] = 3
_TD1_CHARS: Final[int] = 30
_TD2_LINES: Final[int] = 2
_TD2_CHARS: Final[int] = 36
_TD3_LINES: Final[int] = 2
_TD3_CHARS: Final[int] = 44

_FILLER: Final[str] = "<"
_MIN_LINE_RATIO: Final[float] = 0.75
_MIN_FILLER_DENSITY: Final[float] = 0.05
_CHECK_DIGIT_WEIGHTS: Final[tuple[int, ...]] = (7, 3, 1)

_VALID_SEX_CHARS: Final[frozenset[str]] = frozenset({"M", "F", "X", "<"})

_VALID_DOC_CODES: Final[frozenset[str]] = frozenset(
    {
        "P",
        "I",
        "ID",
        "A",
        "C",
        "V",
    }
)

_OCR_NUMERIC_MAP: Final[dict[str, str]] = {
    "O": "0",
    "o": "0",
    "I": "1",
    "i": "1",
    "l": "1",
    "B": "8",
    "S": "5",
    "s": "5",
    "G": "6",
    "Z": "2",
    "Q": "0",
}

_OCR_ALPHA_MAP: Final[dict[str, str]] = {
    "0": "O",
    "1": "I",
}

_MRZ_LINE_PATTERN: Final[re.Pattern[str]] = re.compile(r"[A-Z0-9<]{15,44}")


class MRZType(StrEnum):
    TD1 = "TD1"
    TD2 = "TD2"
    TD3 = "TD3"
    UNKNOWN = "UNKNOWN"


class MRZParseStatus(StrEnum):
    VALID = "VALID"
    PARTIAL = "PARTIAL"
    INVALID = "INVALID"
    OCR_CORRUPTED = "OCR_CORRUPTED"


class MrzField(StrEnum):
    DOCUMENT_CODE = "document_code"
    ISSUING_COUNTRY = "issuing_country"
    SURNAME = "surname"
    GIVEN_NAMES = "given_names"
    DOCUMENT_NUMBER = "document_number"
    NATIONALITY = "nationality"
    DATE_OF_BIRTH = "date_of_birth"
    SEX = "sex"
    EXPIRY_DATE = "expiry_date"
    PERSONAL_NUMBER = "personal_number"
    OPTIONAL_DATA = "optional_data"
    OPTIONAL_DATA_1 = "optional_data_1"
    OPTIONAL_DATA_2 = "optional_data_2"


@dataclass(frozen=True)
class MrzCheckResult:
    field_name: str
    expected_check_digit: str
    actual_check_digit: str
    is_valid: bool

    @classmethod
    def of(cls, field_name: str, value: str, check_char: str) -> MrzCheckResult:
        expected = _compute_check_digit(value)
        return cls(
            field_name=field_name,
            expected_check_digit=expected,
            actual_check_digit=check_char,
            is_valid=(expected == check_char),
        )


@dataclass(frozen=True)
class MrzParseResult:
    mrz_type: MRZType
    status: MRZParseStatus
    raw_lines: tuple[str, ...]
    normalized_lines: tuple[str, ...]
    fields: Mapping[MrzField, str]
    check_results: tuple[MrzCheckResult, ...]
    confidence: float
    errors: tuple[str, ...]
    overall_check_success: bool

    @property
    def is_valid(self) -> bool:
        return self.status == MRZParseStatus.VALID

    def field(self, key: MrzField) -> str | None:
        return self.fields.get(key)

    def clean(self, key: MrzField) -> str | None:
        value = self.fields.get(key)
        if value is None:
            return None
        return value.replace(_FILLER, "").strip() or None


def _compute_check_digit(value: str) -> str:
    total = 0
    for idx, ch in enumerate(value):
        weight = _CHECK_DIGIT_WEIGHTS[idx % 3]
        if ch == _FILLER:
            numeric = 0
        elif ch.isdigit():
            numeric = int(ch)
        elif ch.isalpha():
            numeric = ord(ch.upper()) - ord("A") + 10
        else:
            numeric = 0
        total += numeric * weight
    return str(total % 10)


def _repair_numeric_field(value: str) -> str:
    return "".join(_OCR_NUMERIC_MAP.get(ch, ch) for ch in value)


def _repair_alphanumeric_field(value: str) -> str:
    return "".join(_OCR_ALPHA_MAP.get(ch, ch) for ch in value)


def _normalize_line(raw: str, expected_length: int) -> str:
    ln = raw.upper().strip()
    ln = re.sub(r"\s+", "", ln)
    if len(ln) < expected_length:
        ln = ln.ljust(expected_length, _FILLER)
    elif len(ln) > expected_length:
        ln = ln[:expected_length]
    return ln


def _split_name(name_field: str) -> tuple[str, str]:
    parts = name_field.split("<<", 1)
    surname = parts[0].replace("<", " ").strip()
    given = parts[1].replace("<", " ").strip() if len(parts) > 1 else ""
    return surname, given


def _is_candidate_line(line: str, expected_length: int) -> bool:
    clean = re.sub(r"\s+", "", line.upper().strip())
    return len(clean) >= int(expected_length * _MIN_LINE_RATIO)


def _extract_doc_code(line: str) -> str:
    clean = re.sub(r"\s+", "", line.upper().strip())
    if len(clean) < 1:
        return ""
    ch0 = _OCR_ALPHA_MAP.get(clean[0], clean[0])
    ch1 = _OCR_ALPHA_MAP.get(clean[1], clean[1]) if len(clean) > 1 else _FILLER
    two_char = ch0 + ch1
    if two_char in _VALID_DOC_CODES:
        return two_char
    if ch0 in _VALID_DOC_CODES:
        return ch0
    return two_char


def _has_valid_doc_code(line: str) -> bool:
    return _extract_doc_code(line) in _VALID_DOC_CODES


def _filler_density(line: str) -> float:
    clean = re.sub(r"\s+", "", line.upper().strip())
    if not clean:
        return 0.0
    return clean.count(_FILLER) / len(clean)


def _validate_sex(sex: str, errors: list[str]) -> None:
    if sex not in _VALID_SEX_CHARS:
        errors.append(f"invalid sex character: {sex!r}")


def _validate_mrz_date(value: str, field_name: str, errors: list[str]) -> None:
    if len(value) != 6 or not value.isdigit():
        errors.append(f"{field_name}: not a 6-digit value: {value!r}")
        return
    year = int(value[0:2])
    month = int(value[2:4])
    day = int(value[4:6])
    if not (1 <= month <= 12):
        errors.append(f"{field_name}: invalid month {month:02d} in {value!r}")
        return
    max_day = calendar.monthrange(2000 + year, month)[1]
    if not (1 <= day <= max_day):
        errors.append(
            f"{field_name}: invalid day {day:02d} for month {month:02d} in {value!r}"
        )


def _build_result(
    mrz_type: MRZType,
    raw_lines: tuple[str, ...],
    norm: tuple[str, ...],
    fields: dict[MrzField, str],
    checks: list[MrzCheckResult],
    errors: list[str],
) -> MrzParseResult:
    valid_checks = sum(1 for c in checks if c.is_valid)
    confidence = round(valid_checks / len(checks), 4) if checks else 0.0
    overall_check_success = valid_checks == len(checks)
    status = _determine_status(errors, confidence)
    return MrzParseResult(
        mrz_type=mrz_type,
        status=status,
        raw_lines=raw_lines,
        normalized_lines=norm,
        fields=MappingProxyType(fields),
        check_results=tuple(checks),
        confidence=confidence,
        errors=tuple(errors),
        overall_check_success=overall_check_success,
    )


def _determine_status(errors: list[str], confidence: float) -> MRZParseStatus:
    if not errors:
        return MRZParseStatus.VALID
    if confidence >= 0.5:
        return MRZParseStatus.PARTIAL
    if confidence > 0.0:
        return MRZParseStatus.OCR_CORRUPTED
    return MRZParseStatus.INVALID


def _make_unknown(
    raw_lines: tuple[str, ...],
    reason: str = "unable to detect MRZ type",
) -> MrzParseResult:
    return MrzParseResult(
        mrz_type=MRZType.UNKNOWN,
        status=MRZParseStatus.INVALID,
        raw_lines=raw_lines,
        normalized_lines=raw_lines,
        fields=MappingProxyType({}),
        check_results=(),
        confidence=0.0,
        errors=(reason,),
        overall_check_success=False,
    )


def detect_type(lines: list[str]) -> MRZType:
    if (
        len(lines) == _TD1_LINES
        and all(_is_candidate_line(ln, _TD1_CHARS) for ln in lines)
        and _has_valid_doc_code(lines[0])
    ):
        return MRZType.TD1
    if (
        len(lines) == _TD2_LINES
        and all(_is_candidate_line(ln, _TD2_CHARS) for ln in lines)
        and _has_valid_doc_code(lines[0])
    ):
        return MRZType.TD2
    if (
        len(lines) == _TD3_LINES
        and all(_is_candidate_line(ln, _TD3_CHARS) for ln in lines)
        and _has_valid_doc_code(lines[0])
    ):
        return MRZType.TD3
    return MRZType.UNKNOWN


def normalize(lines: list[str], mrz_type: MRZType) -> tuple[str, ...]:
    length_map = {
        MRZType.TD1: _TD1_CHARS,
        MRZType.TD2: _TD2_CHARS,
        MRZType.TD3: _TD3_CHARS,
    }
    length = length_map.get(mrz_type, _TD3_CHARS)
    return tuple(_normalize_line(ln, length) for ln in lines)


def extract_mrz_lines(text: str) -> list[str]:
    candidates: list[str] = []
    for ln in text.splitlines():
        clean = re.sub(r"\s+", "", ln.upper().strip())
        if _MRZ_LINE_PATTERN.fullmatch(clean):
            candidates.append(clean)
    if len(candidates) >= 2:
        return candidates
    relaxed: list[str] = []
    for ln in text.splitlines():
        clean = re.sub(r"\s+", "", ln.upper().strip())
        if (
            len(clean) >= 25
            and re.search(r"[A-Z<]{3,}", clean)
            and _filler_density(clean) >= _MIN_FILLER_DENSITY
        ):
            relaxed.append(clean)
    return relaxed if len(relaxed) >= 2 else []


def validate_check_digits(result: MrzParseResult) -> tuple[MrzCheckResult, ...]:
    return result.check_results


def parse_text(text: str) -> MrzParseResult:
    lines = extract_mrz_lines(text)
    if not lines:
        return _make_unknown((), reason="no MRZ lines detected in text")
    return parse(lines)


def _parse_td3(
    raw_lines: tuple[str, ...],
    norm: tuple[str, ...],
) -> MrzParseResult:
    errors: list[str] = []
    checks: list[MrzCheckResult] = []

    ln1 = norm[0]
    ln2 = norm[1]

    doc_code = ln1[0:2].rstrip(_FILLER)
    issuing = _repair_alphanumeric_field(ln1[2:5])
    name_field = ln1[5:44]
    surname, given = _split_name(name_field)

    doc_number = _repair_alphanumeric_field(ln2[0:9])
    doc_number_cd = ln2[9]
    nationality = _repair_alphanumeric_field(ln2[10:13])
    dob = _repair_numeric_field(ln2[13:19])
    dob_cd = ln2[19]
    sex = ln2[20]
    expiry = _repair_numeric_field(ln2[21:27])
    expiry_cd = ln2[27]
    personal = ln2[28:42]
    personal_cd = ln2[42]
    composite_cd = ln2[43]

    checks.append(MrzCheckResult.of(MrzField.DOCUMENT_NUMBER, ln2[0:9], doc_number_cd))
    checks.append(MrzCheckResult.of(MrzField.DATE_OF_BIRTH, ln2[13:19], dob_cd))
    checks.append(MrzCheckResult.of(MrzField.EXPIRY_DATE, ln2[21:27], expiry_cd))
    checks.append(MrzCheckResult.of(MrzField.PERSONAL_NUMBER, ln2[28:42], personal_cd))

    composite_raw = (
        ln2[0:9]
        + ln2[9]
        + ln2[13:19]
        + ln2[19]
        + ln2[21:27]
        + ln2[27]
        + ln2[28:42]
        + ln2[42]
    )
    checks.append(MrzCheckResult.of("composite", composite_raw, composite_cd))

    for chk in checks:
        if not chk.is_valid:
            errors.append(
                f"check digit failed: {chk.field_name} "
                f"(expected={chk.expected_check_digit}, got={chk.actual_check_digit})"
            )

    _validate_sex(sex, errors)
    _validate_mrz_date(dob, MrzField.DATE_OF_BIRTH, errors)
    _validate_mrz_date(expiry, MrzField.EXPIRY_DATE, errors)

    fields: dict[MrzField, str] = {
        MrzField.DOCUMENT_CODE: doc_code,
        MrzField.ISSUING_COUNTRY: issuing,
        MrzField.SURNAME: surname,
        MrzField.GIVEN_NAMES: given,
        MrzField.DOCUMENT_NUMBER: doc_number,
        MrzField.NATIONALITY: nationality,
        MrzField.DATE_OF_BIRTH: dob,
        MrzField.SEX: sex,
        MrzField.EXPIRY_DATE: expiry,
        MrzField.PERSONAL_NUMBER: personal,
    }

    return _build_result(MRZType.TD3, raw_lines, norm, fields, checks, errors)


def _parse_td1(
    raw_lines: tuple[str, ...],
    norm: tuple[str, ...],
) -> MrzParseResult:
    errors: list[str] = []
    checks: list[MrzCheckResult] = []

    ln1 = norm[0]
    ln2 = norm[1]
    ln3 = norm[2]

    doc_code = ln1[0:2].rstrip(_FILLER)
    issuing = _repair_alphanumeric_field(ln1[2:5])
    doc_number = _repair_alphanumeric_field(ln1[5:14])
    doc_number_cd = ln1[14]
    optional1 = ln1[15:30]

    dob = _repair_numeric_field(ln2[0:6])
    dob_cd = ln2[6]
    sex = ln2[7]
    expiry = _repair_numeric_field(ln2[8:14])
    expiry_cd = ln2[14]
    nationality = _repair_alphanumeric_field(ln2[15:18])
    optional2 = ln2[18:29]
    composite_cd = ln2[29]

    name_field = ln3[0:30]
    surname, given = _split_name(name_field)

    checks.append(MrzCheckResult.of(MrzField.DOCUMENT_NUMBER, ln1[5:14], doc_number_cd))
    checks.append(MrzCheckResult.of(MrzField.DATE_OF_BIRTH, ln2[0:6], dob_cd))
    checks.append(MrzCheckResult.of(MrzField.EXPIRY_DATE, ln2[8:14], expiry_cd))

    composite_raw = ln1[5:30] + ln2[0:7] + ln2[8:29]
    checks.append(MrzCheckResult.of("composite", composite_raw, composite_cd))

    for chk in checks:
        if not chk.is_valid:
            errors.append(
                f"check digit failed: {chk.field_name} "
                f"(expected={chk.expected_check_digit}, got={chk.actual_check_digit})"
            )

    _validate_sex(sex, errors)
    _validate_mrz_date(dob, MrzField.DATE_OF_BIRTH, errors)
    _validate_mrz_date(expiry, MrzField.EXPIRY_DATE, errors)

    fields: dict[MrzField, str] = {
        MrzField.DOCUMENT_CODE: doc_code,
        MrzField.ISSUING_COUNTRY: issuing,
        MrzField.SURNAME: surname,
        MrzField.GIVEN_NAMES: given,
        MrzField.DOCUMENT_NUMBER: doc_number,
        MrzField.NATIONALITY: nationality,
        MrzField.DATE_OF_BIRTH: dob,
        MrzField.SEX: sex,
        MrzField.EXPIRY_DATE: expiry,
        MrzField.OPTIONAL_DATA_1: optional1.strip(_FILLER),
        MrzField.OPTIONAL_DATA_2: optional2.strip(_FILLER),
    }

    return _build_result(MRZType.TD1, raw_lines, norm, fields, checks, errors)


def _parse_td2(
    raw_lines: tuple[str, ...],
    norm: tuple[str, ...],
) -> MrzParseResult:
    errors: list[str] = []
    checks: list[MrzCheckResult] = []

    ln1 = norm[0]
    ln2 = norm[1]

    doc_code = ln1[0:2].rstrip(_FILLER)
    issuing = _repair_alphanumeric_field(ln1[2:5])
    name_field = ln1[5:36]
    surname, given = _split_name(name_field)

    doc_number = _repair_alphanumeric_field(ln2[0:9])
    doc_number_cd = ln2[9]
    nationality = _repair_alphanumeric_field(ln2[10:13])
    dob = _repair_numeric_field(ln2[13:19])
    dob_cd = ln2[19]
    sex = ln2[20]
    expiry = _repair_numeric_field(ln2[21:27])
    expiry_cd = ln2[27]
    optional = ln2[28:35]
    composite_cd = ln2[35]

    checks.append(MrzCheckResult.of(MrzField.DOCUMENT_NUMBER, ln2[0:9], doc_number_cd))
    checks.append(MrzCheckResult.of(MrzField.DATE_OF_BIRTH, ln2[13:19], dob_cd))
    checks.append(MrzCheckResult.of(MrzField.EXPIRY_DATE, ln2[21:27], expiry_cd))

    composite_raw = (
        ln2[0:9] + ln2[9] + ln2[13:19] + ln2[19] + ln2[21:27] + ln2[27] + ln2[28:35]
    )
    checks.append(MrzCheckResult.of("composite", composite_raw, composite_cd))

    for chk in checks:
        if not chk.is_valid:
            errors.append(
                f"check digit failed: {chk.field_name} "
                f"(expected={chk.expected_check_digit}, got={chk.actual_check_digit})"
            )

    _validate_sex(sex, errors)
    _validate_mrz_date(dob, MrzField.DATE_OF_BIRTH, errors)
    _validate_mrz_date(expiry, MrzField.EXPIRY_DATE, errors)

    fields: dict[MrzField, str] = {
        MrzField.DOCUMENT_CODE: doc_code,
        MrzField.ISSUING_COUNTRY: issuing,
        MrzField.SURNAME: surname,
        MrzField.GIVEN_NAMES: given,
        MrzField.DOCUMENT_NUMBER: doc_number,
        MrzField.NATIONALITY: nationality,
        MrzField.DATE_OF_BIRTH: dob,
        MrzField.SEX: sex,
        MrzField.EXPIRY_DATE: expiry,
        MrzField.OPTIONAL_DATA: optional.strip(_FILLER),
    }

    return _build_result(MRZType.TD2, raw_lines, norm, fields, checks, errors)


def parse(lines: list[str]) -> MrzParseResult:
    if not lines or not any(ln.strip() for ln in lines):
        return _make_unknown((), reason="empty input")

    raw_lines = tuple(lines)
    mrz_type = detect_type(lines)

    if mrz_type == MRZType.UNKNOWN:
        return _make_unknown(raw_lines)

    norm = normalize(lines, mrz_type)

    if mrz_type == MRZType.TD3:
        return _parse_td3(raw_lines, norm)
    if mrz_type == MRZType.TD1:
        return _parse_td1(raw_lines, norm)
    return _parse_td2(raw_lines, norm)
