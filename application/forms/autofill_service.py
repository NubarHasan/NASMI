from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from application.ports.form_mapping_repository import FormMappingRepository
from application.ports.form_template_repository import FormTemplateRepository
from core.guards import require
from core.types import FormTemplateId
from forms.autofill_engine import AutofillEngine
from forms.autofill_preview import AutofillPreview
from knowledge.knowledge_fact_type import KnowledgeFactType


class TemplateNotFoundError(Exception):
    def __init__(self, template_id: FormTemplateId) -> None:
        super().__init__(f"FormTemplate not found: {template_id!r}")
        self.template_id = template_id


class MappingNotFoundError(Exception):
    def __init__(self, template_id: FormTemplateId) -> None:
        super().__init__(f"FormMapping not found for template: {template_id!r}")
        self.template_id = template_id


class AutofillService:
    """
    Application Service.

    Responsibility: orchestrate (load template + load mapping + invoke engine).

    Does NOT:
      - implement mapping logic
      - implement autofill logic
      - persist anything
      - interact with UI
    """

    def __init__(
        self,
        template_repository: FormTemplateRepository,
        mapping_repository: FormMappingRepository,
        autofill_engine: AutofillEngine,
    ) -> None:
        require(
            template_repository is not None,
            "template_repository is required",
        )
        require(
            mapping_repository is not None,
            "mapping_repository is required",
        )
        require(
            autofill_engine is not None,
            "autofill_engine is required",
        )
        self._template_repository = template_repository
        self._mapping_repository = mapping_repository
        self._autofill_engine = autofill_engine

    def run(
        self,
        template_id: FormTemplateId,
        facts: Mapping[KnowledgeFactType, Any],
    ) -> AutofillPreview:
        """
        Load template and mapping, invoke AutofillEngine, return AutofillPreview.

        Raises:
            TemplateNotFoundError: if no template exists for template_id.
            MappingNotFoundError:  if no mapping exists for template_id.
        """
        require(isinstance(facts, Mapping), "facts must implement Mapping")

        template = self._template_repository.get_by_id(template_id)
        if template is None:
            raise TemplateNotFoundError(template_id)

        mapping = self._mapping_repository.get_by_template_id(template_id)
        if mapping is None:
            raise MappingNotFoundError(template_id)

        return self._autofill_engine.run(
            template=template,
            mapping=mapping,
            facts=facts,
        )
