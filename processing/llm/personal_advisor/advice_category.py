from __future__ import annotations

from enum import StrEnum


class AdviceCategory(StrEnum):
    DOCUMENTS = "documents"
    FINANCIAL = "financial"
    HEALTH = "health"
    LEGAL = "legal"
    FAMILY = "family"
    EMPLOYMENT = "employment"
    CONFLICTS = "conflicts"
    GENERAL = "general"
