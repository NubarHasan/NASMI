from __future__ import annotations

from application.services.knowledge_service import KnowledgeApplicationService
from core.guards import require
from core.identifiers import is_valid_entity_id
from core.types import EntityId
from knowledge.profile_builder import ProfileBuilder
from knowledge.profile_schema_registry import get_schema, has_schema
from processing.profile_build.profile_build_result import ProfileBuildResult


class ProfileBuildService:

    def __init__(self, knowledge_app_service: KnowledgeApplicationService) -> None:
        require(
            isinstance(knowledge_app_service, KnowledgeApplicationService),
            "knowledge_app_service must be a KnowledgeApplicationService",
        )
        self._ks = knowledge_app_service

    def build(
        self,
        entity_id: EntityId,
        entity_type: str,
        display_name: str,
        metadata: dict[str, object] | None = None,
    ) -> ProfileBuildResult:
        require(is_valid_entity_id(entity_id), "invalid entity_id")
        require(bool(entity_type.strip()), "entity_type must not be blank")
        require(bool(display_name.strip()), "display_name must not be blank")
        require(
            has_schema(entity_type),
            f"no profile schema registered for entity_type: {entity_type!r}",
        )

        schema = get_schema(entity_type)
        accepted = self._ks.list_accepted_facts(entity_id)

        builder = ProfileBuilder(
            entity_id=entity_id,
            entity_type=entity_type,
            schema=schema,
        )

        skipped = 0
        for fact in accepted:
            if fact.field_name not in schema:
                skipped += 1
                continue
            builder.add_fact(fact)

        profile = builder.build(
            display_name=display_name,
            metadata=metadata,
        )

        return ProfileBuildResult(
            entity_id=entity_id,
            profile=profile,
            fields_built=len(builder.covered_fields()),
            fields_missing=tuple(builder.missing_fields()),
            completeness=builder.completeness(),
            skipped_facts=skipped,
        )
