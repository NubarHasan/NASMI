from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from audit.audit_entry import AuditEntry
from core.guards import require
from core.types import AuditId


@dataclass(frozen=True)
class AuditChain:
    entries: tuple[AuditEntry, ...]

    def __post_init__(self) -> None:
        self._validate_structure()

    def _validate_structure(self) -> None:
        require(isinstance(self.entries, tuple), "entries must be a tuple")

        seen_ids: set[AuditId] = set()

        for index, entry in enumerate(self.entries):
            require(
                isinstance(entry, AuditEntry),
                f"entry at index {index} must be an AuditEntry",
            )
            require(
                entry.audit_id not in seen_ids,
                f"duplicate audit_id '{entry.audit_id}' at index {index}",
            )
            seen_ids.add(entry.audit_id)

            if index == 0:
                require(
                    entry.previous_hash is None,
                    f"first entry must have previous_hash=None, "
                    f"got '{entry.previous_hash}'",
                )
            else:
                previous = self.entries[index - 1]
                require(
                    entry.previous_hash == previous.entry_hash,
                    f"chain broken at index {index}: "
                    f"expected previous_hash='{previous.entry_hash}', "
                    f"got '{entry.previous_hash}'",
                )
                require(
                    entry.occurred_at >= previous.occurred_at,
                    f"ordering violation at index {index}: "
                    f"occurred_at '{entry.occurred_at}' is before "
                    f"previous '{previous.occurred_at}'",
                )

    def verify_integrity(self, secret_key: bytes) -> bool:
        self._validate_structure()
        return all(entry.verify(secret_key) for entry in self.entries)

    def append(self, entry: AuditEntry) -> AuditChain:
        require(isinstance(entry, AuditEntry), "entry must be an AuditEntry")

        if self.entries:
            latest = self.entries[-1]
            require(
                entry.audit_id != latest.audit_id,
                f"duplicate audit_id '{entry.audit_id}'",
            )
            require(
                entry.previous_hash == latest.entry_hash,
                f"entry.previous_hash must equal latest entry_hash "
                f"'{latest.entry_hash}'",
            )
            require(
                entry.occurred_at >= latest.occurred_at,
                f"entry.occurred_at must not be before latest "
                f"occurred_at '{latest.occurred_at}'",
            )
        else:
            require(
                entry.previous_hash is None,
                "first entry must have previous_hash=None",
            )

        return AuditChain(entries=self.entries + (entry,))

    def latest_entry(self) -> AuditEntry | None:
        return self.entries[-1] if self.entries else None

    def latest_hash(self) -> str | None:
        latest = self.latest_entry()
        return latest.entry_hash if latest is not None else None

    def is_empty(self) -> bool:
        return len(self.entries) == 0

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self) -> Iterator[AuditEntry]:
        return iter(self.entries)

    @classmethod
    def empty(cls) -> AuditChain:
        return cls(entries=())

    @classmethod
    def from_entries(cls, entries: Iterable[AuditEntry]) -> AuditChain:
        return cls(entries=tuple(entries))
