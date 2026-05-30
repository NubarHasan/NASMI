from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any

from core.exceptions import ValidationError
from core.guards import require

_HASH_ALGORITHM = "sha256"
_CHUNK_SIZE = 65_536
_HMAC_ALGORITHM = "sha256"
_DIGEST_LENGTH = 64

GENESIS_DIGEST: str = hashlib.sha256(b"").hexdigest()


def _new_sha256() -> Any:
    return hashlib.new(_HASH_ALGORITHM)


def hash_bytes(data: bytes) -> str:
    require(isinstance(data, bytes), "data must be bytes")
    h = _new_sha256()
    h.update(data)
    return h.hexdigest()


def hash_str(value: str) -> str:
    require(isinstance(value, str), "value must be a string")
    h = _new_sha256()
    h.update(value.encode("utf-8"))
    return h.hexdigest()


def hash_file(path: Path) -> str:
    require(isinstance(path, Path), "path must be a Path")
    require(path.is_file(), f"path is not a file: {path}")
    h = _new_sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(_CHUNK_SIZE):
            h.update(chunk)
    return h.hexdigest()


def hash_dict(obj: dict[str, Any]) -> str:
    require(isinstance(obj, dict), "obj must be a dict")
    canonical = json.dumps(
        obj, sort_keys=True, ensure_ascii=True, separators=(",", ":")
    )
    return hash_str(canonical)


def hash_json(payload: Any) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")
    )
    return hash_str(canonical)


def is_valid_digest(value: str) -> bool:
    if not isinstance(value, str):
        return False
    if len(value) != _DIGEST_LENGTH:
        return False
    return all(c in "0123456789abcdef" for c in value)


def assert_valid_digest(value: str) -> None:
    if not is_valid_digest(value):
        raise ValidationError(f"invalid sha256 digest: {value!r}")


def hash_chain(previous_digest: str, payload_digest: str) -> str:
    assert_valid_digest(previous_digest)
    assert_valid_digest(payload_digest)
    combined = (previous_digest + payload_digest).encode("utf-8")
    h = _new_sha256()
    h.update(combined)
    return h.hexdigest()


def verify_chain(
    previous_digest: str,
    payload_digest: str,
    expected_chain_digest: str,
) -> bool:
    assert_valid_digest(previous_digest)
    assert_valid_digest(payload_digest)
    assert_valid_digest(expected_chain_digest)
    actual = hash_chain(previous_digest, payload_digest)
    return hmac.compare_digest(actual, expected_chain_digest)


def verify_hash(data: bytes, expected: str) -> bool:
    require(isinstance(data, bytes), "data must be bytes")
    require(isinstance(expected, str), "expected must be a string")
    assert_valid_digest(expected)
    actual = hash_bytes(data)
    return hmac.compare_digest(actual, expected)


def verify_file_hash(path: Path, expected: str) -> bool:
    require(isinstance(path, Path), "path must be a Path")
    require(isinstance(expected, str), "expected must be a string")
    assert_valid_digest(expected)
    actual = hash_file(path)
    return hmac.compare_digest(actual, expected)


def hmac_sign(data: bytes, key: bytes) -> str:
    require(isinstance(data, bytes), "data must be bytes")
    require(isinstance(key, bytes), "key must be bytes")
    require(len(key) > 0, "key must not be empty")
    return hmac.new(key, data, _HMAC_ALGORITHM).hexdigest()


def hmac_verify(data: bytes, key: bytes, signature: str) -> bool:
    require(isinstance(data, bytes), "data must be bytes")
    require(isinstance(key, bytes), "key must be bytes")
    require(isinstance(signature, str), "signature must be a string")
    require(len(key) > 0, "key must not be empty")
    assert_valid_digest(signature)
    expected = hmac_sign(data, key)
    return hmac.compare_digest(expected, signature)


def genesis_digest() -> str:
    return GENESIS_DIGEST
