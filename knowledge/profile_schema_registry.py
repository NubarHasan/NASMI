from __future__ import annotations

from types import MappingProxyType

from core.guards import require
from knowledge.knowledge_fact_type import KnowledgeFactType

_PERSON_SCHEMA: frozenset[str] = frozenset(
    {
        KnowledgeFactType.PERSON_FIRST_NAME,
        KnowledgeFactType.PERSON_LAST_NAME,
        KnowledgeFactType.PERSON_FULL_NAME,
        KnowledgeFactType.DATE_OF_BIRTH,
        KnowledgeFactType.PLACE_OF_BIRTH,
        KnowledgeFactType.NATIONALITY,
        KnowledgeFactType.ADDRESS_STREET,
        KnowledgeFactType.ADDRESS_HOUSE_NUMBER,
        KnowledgeFactType.ADDRESS_POSTAL_CODE,
        KnowledgeFactType.ADDRESS_CITY,
        KnowledgeFactType.ADDRESS_COUNTRY,
        KnowledgeFactType.PHONE_NUMBER,
        KnowledgeFactType.EMAIL_ADDRESS,
        KnowledgeFactType.IBAN,
        KnowledgeFactType.BIC,
        KnowledgeFactType.BANK_NAME,
        KnowledgeFactType.TAX_ID,
        KnowledgeFactType.IDENTITY_CARD_NUMBER,
        KnowledgeFactType.PASSPORT_NUMBER,
        KnowledgeFactType.MARITAL_STATUS,
        KnowledgeFactType.EMPLOYER_NAME,
        KnowledgeFactType.JOB_TITLE,
    }
)

_DOCUMENT_SCHEMA: frozenset[str] = frozenset(
    {
        KnowledgeFactType.DOCUMENT_DATE,
        KnowledgeFactType.DOCUMENT_REFERENCE,
        KnowledgeFactType.PERSON_FULL_NAME,
    }
)

_SCHEMA_REGISTRY: MappingProxyType[str, frozenset[str]] = MappingProxyType(
    {
        "person": _PERSON_SCHEMA,
        "document": _DOCUMENT_SCHEMA,
    }
)


def get_schema(entity_type: str) -> frozenset[str]:
    require(
        isinstance(entity_type, str) and bool(entity_type.strip()),
        "entity_type must be a non-empty string",
    )
    key = entity_type.strip().lower()
    schema = _SCHEMA_REGISTRY.get(key)
    require(
        schema is not None,
        f"no profile schema registered for entity_type: {entity_type!r}",
    )
    return schema  # type: ignore[return-value]


def has_schema(entity_type: str) -> bool:
    if not isinstance(entity_type, str) or not entity_type.strip():
        return False
    return entity_type.strip().lower() in _SCHEMA_REGISTRY


def list_registered_types() -> tuple[str, ...]:
    return tuple(_SCHEMA_REGISTRY.keys())
