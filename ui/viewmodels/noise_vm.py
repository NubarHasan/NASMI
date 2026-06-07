from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from infrastructure.db.repositories.sqlite_noise_repository import (
    NoiseItem,
    SqliteNoiseRepository,
)
from ui.services.api_client import _get_db


@dataclass(frozen=True)
class NoiseActionResult:
    success: bool
    message: str = ""
    error: str = ""


class NoiseVM:
    def __init__(self) -> None:
        self._repo = SqliteNoiseRepository(_get_db())

    def count_open(self) -> int:
        try:
            return self._repo.count_open()
        except Exception:
            return 0

    def load_open(self, limit: int = 10) -> tuple[NoiseItem, ...]:
        try:
            return self._repo.list_open(limit=limit)
        except Exception:
            return ()

    def load_all(self, limit: int = 50) -> tuple[NoiseItem, ...]:
        try:
            return self._repo.list_all(limit=limit)
        except Exception:
            return ()

    def ignore(self, noise_id: str) -> NoiseActionResult:
        try:
            self._repo.update_status(noise_id, "ignored")
            return NoiseActionResult(success=True, message="Noise item ignored")
        except Exception as exc:
            return NoiseActionResult(success=False, error=str(exc))

    def mark_reviewed(self, noise_id: str) -> NoiseActionResult:
        try:
            self._repo.update_status(noise_id, "reviewed")
            return NoiseActionResult(success=True, message="Noise item reviewed")
        except Exception as exc:
            return NoiseActionResult(success=False, error=str(exc))

    def reopen(self, noise_id: str) -> NoiseActionResult:
        try:
            self._repo.update_status(noise_id, "open")
            return NoiseActionResult(success=True, message="Noise item reopened")
        except Exception as exc:
            return NoiseActionResult(success=False, error=str(exc))

    def delete(self, noise_id: str) -> NoiseActionResult:
        try:
            self._repo.delete(noise_id)
            return NoiseActionResult(success=True, message="Noise item deleted")
        except Exception as exc:
            return NoiseActionResult(success=False, error=str(exc))

    def save_edit(
        self,
        noise_id: str,
        raw_text: str,
        reason: str,
        confidence: float,
        metadata_text: str,
    ) -> NoiseActionResult:
        try:
            raw_text = raw_text.strip()
            reason = reason.strip()

            if not raw_text:
                return NoiseActionResult(success=False, error="Raw text is empty")

            if not reason:
                return NoiseActionResult(success=False, error="Reason is empty")

            metadata: dict[str, Any] = {}
            if metadata_text.strip():
                parsed = json.loads(metadata_text)
                if not isinstance(parsed, dict):
                    return NoiseActionResult(
                        success=False, error="Metadata must be a JSON object"
                    )
                metadata = parsed

            self._repo.update_text(
                noise_id=noise_id,
                raw_text=raw_text,
                reason=reason,
                confidence=confidence,
                metadata=metadata,
            )
            return NoiseActionResult(success=True, message="Noise item saved")
        except Exception as exc:
            return NoiseActionResult(success=False, error=str(exc))

    def create_test_noise(self) -> NoiseActionResult:
        try:
            self._repo.create(
                raw_text="Unclear German OCR fragment: Aufenthaltstitel ... gültig bis ...",
                reason="Low confidence OCR fragment needs human review",
                stage="extraction",
                confidence=0.35,
                metadata={
                    "source": "manual_test",
                    "language": "de",
                },
            )
            return NoiseActionResult(success=True, message="Test noise item created")
        except Exception as exc:
            return NoiseActionResult(success=False, error=str(exc))
