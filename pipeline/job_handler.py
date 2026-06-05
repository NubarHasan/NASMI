from __future__ import annotations

from typing import Protocol, runtime_checkable

from pipeline.job import Job


@runtime_checkable
class JobHandler(Protocol):
    def handle(self, job: Job) -> None: ...
