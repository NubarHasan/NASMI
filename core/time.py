from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from core.exceptions import ValidationError
from core.guards import require

_UTC = UTC

_ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
_ISO_FORMAT_COMPACT = "%Y-%m-%dT%H:%M:%SZ"


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=_UTC)
    return dt.astimezone(_UTC)


def utcnow() -> datetime:
    return datetime.now(_UTC)


def utctoday() -> date:
    return datetime.now(_UTC).date()


def utc_timestamp() -> float:
    return datetime.now(_UTC).timestamp()


def utcnow_iso() -> str:
    return format_timestamp(utcnow())


def parse_timestamp(value: str) -> datetime:
    require(isinstance(value, str), "value must be a string")
    require(bool(value.strip()), "value must not be empty")
    for fmt in (_ISO_FORMAT, _ISO_FORMAT_COMPACT):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=_UTC)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(value)
        return _to_utc(dt)
    except ValueError:
        pass
    raise ValidationError(f"cannot parse timestamp: {value!r}")


def is_valid_timestamp(value: str) -> bool:
    if not isinstance(value, str):
        return False
    if not value.strip():
        return False
    try:
        parse_timestamp(value)
        return True
    except (ValidationError, ValueError):
        return False


def format_timestamp(dt: datetime) -> str:
    require(isinstance(dt, datetime), "dt must be a datetime")
    return _to_utc(dt).strftime(_ISO_FORMAT)


def format_date(d: date) -> str:
    require(isinstance(d, date), "d must be a date")
    return d.isoformat()


def duration_seconds(start: datetime, end: datetime) -> float:
    require(isinstance(start, datetime), "start must be a datetime")
    require(isinstance(end, datetime), "end must be a datetime")
    return (_to_utc(end) - _to_utc(start)).total_seconds()


def age_seconds(dt: datetime) -> float:
    require(isinstance(dt, datetime), "dt must be a datetime")
    return duration_seconds(dt, utcnow())


def is_expired(dt: datetime, ttl_seconds: float) -> bool:
    require(isinstance(dt, datetime), "dt must be a datetime")
    require(ttl_seconds >= 0, "ttl_seconds must be non-negative")
    return age_seconds(dt) >= ttl_seconds


def add_seconds(dt: datetime, seconds: float) -> datetime:
    require(isinstance(dt, datetime), "dt must be a datetime")
    require(seconds >= 0, "seconds must be non-negative")
    return _to_utc(dt) + timedelta(seconds=seconds)


def subtract_seconds(dt: datetime, seconds: float) -> datetime:
    require(isinstance(dt, datetime), "dt must be a datetime")
    require(seconds >= 0, "seconds must be non-negative")
    return _to_utc(dt) - timedelta(seconds=seconds)


def is_before(a: datetime, b: datetime) -> bool:
    require(isinstance(a, datetime), "a must be a datetime")
    require(isinstance(b, datetime), "b must be a datetime")
    return _to_utc(a) < _to_utc(b)


def is_after(a: datetime, b: datetime) -> bool:
    require(isinstance(a, datetime), "a must be a datetime")
    require(isinstance(b, datetime), "b must be a datetime")
    return _to_utc(a) > _to_utc(b)
