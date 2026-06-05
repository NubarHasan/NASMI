from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.guards import require
from forms.autofill_preview import AutofillPreview
from forms.form_mapping import FormMapping
from forms.form_template import FormTemplate
from knowledge.knowledge_fact_type import KnowledgeFactType


class AutofillEngine:
    """
    Pure Domain Service.

    Responsibility: combine (template + mapping + facts) → AutofillPreview.

    Does NOT:
      - fetch or resolve FormMapping
      - access any Repository or Infrastructure
      - persist or submit anything
      - interact with UI or Application Layer
    """

    def run(
        self,
        template: FormTemplate,
        mapping: FormMapping,
        facts: Mapping[KnowledgeFactType, Any],
    ) -> AutofillPreview:
        require(isinstance(template, FormTemplate), "template must be a FormTemplate")
        require(isinstance(mapping, FormMapping), "mapping must be a FormMapping")
        require(isinstance(facts, Mapping), "facts must implement Mapping")
        require(
            template.template_id == mapping.template_id,
            "template and mapping must share the same template_id",
        )

        return AutofillPreview.build(
            template=template,
            mapping=mapping,
            facts=facts,
        )
