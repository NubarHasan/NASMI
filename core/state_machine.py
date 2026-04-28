from enum import Enum


class DocumentState(Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    REVIEWED = "REVIEWED"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    ARCHIVED = "ARCHIVED"


class EntityState(Enum):
    NEW = "NEW"
    VALIDATED = "VALIDATED"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    CONFLICTED = "CONFLICTED"
    EXPIRED = "EXPIRED"


DOCUMENT_TRANSITIONS: dict[DocumentState, list[DocumentState]] = {
    DocumentState.UPLOADED: [DocumentState.PROCESSING],
    DocumentState.PROCESSING: [DocumentState.REVIEWED, DocumentState.ARCHIVED],
    DocumentState.REVIEWED: [DocumentState.ACTIVE, DocumentState.ARCHIVED],
    DocumentState.ACTIVE: [DocumentState.EXPIRED, DocumentState.ARCHIVED],
    DocumentState.EXPIRED: [DocumentState.ARCHIVED],
    DocumentState.ARCHIVED: [],
}

ENTITY_TRANSITIONS: dict[EntityState, list[EntityState]] = {
    EntityState.NEW: [EntityState.VALIDATED, EntityState.CONFLICTED],
    EntityState.VALIDATED: [EntityState.ACTIVE, EntityState.CONFLICTED],
    EntityState.ACTIVE: [
        EntityState.ARCHIVED,
        EntityState.CONFLICTED,
        EntityState.EXPIRED,
    ],
    EntityState.CONFLICTED: [EntityState.VALIDATED, EntityState.ARCHIVED],
    EntityState.EXPIRED: [EntityState.ARCHIVED],
    EntityState.ARCHIVED: [],
}


class StateMachine:

    def transition_document(
        self, current: DocumentState, target: DocumentState
    ) -> DocumentState:
        if target not in DOCUMENT_TRANSITIONS[current]:
            raise ValueError(
                f"Invalid document transition: {current.value} → {target.value}"
            )
        return target

    def transition_entity(
        self, current: EntityState, target: EntityState
    ) -> EntityState:
        if target not in ENTITY_TRANSITIONS[current]:
            raise ValueError(
                f"Invalid entity transition: {current.value} → {target.value}"
            )
        return target
