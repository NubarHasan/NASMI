from __future__ import annotations

import logging

from core.identifiers import generate_vault_id
from core.time import utcnow_iso
from core.types import EntityId, VaultId
from knowledge.vault import Vault
from processing.llm.advisor_factory import (
    make_null_advisors,
    make_personal_advisor,
    make_proactive_advisor,
)
from processing.llm.advisory_result import SUPPORTED_LOCALES, AdvisoryResult
from processing.llm.llm_factory import make_fast_llm
from processing.llm.personal_advisor.advice_item import PersonalAdvisoryResult
from ui.services.api_client import get_entity_repo, get_profile_query

_log = logging.getLogger(__name__)


def _build_vault(entity_id_str: str) -> Vault | None:
    try:
        entity_id = EntityId(entity_id_str)
        entity = get_entity_repo().get(entity_id)
        if entity is None:
            _log.warning("advisory_vm: entity not found: %s", entity_id_str)
            return None

        vault = Vault(
            vault_id=VaultId(generate_vault_id()),
            entities={entity_id: entity},
            profiles={},
            conflicts={},
            created_at=utcnow_iso(),
        )

        profile = get_profile_query().get_profile(entity_id)
        if profile is not None:
            vault = vault.update_profile(profile)

        return vault
    except Exception:
        _log.exception("advisory_vm: failed to build vault for %s", entity_id_str)
        return None


class AdvisoryVM:

    def refresh(
        self,
        entity_id: str,
        use_llm: bool = True,
    ) -> tuple[PersonalAdvisoryResult | None, AdvisoryResult | None]:
        vault = _build_vault(entity_id)
        if vault is None:
            return None, None

        try:
            if use_llm:
                personal_advisor = make_personal_advisor(fast=True)
                proactive_advisor = make_proactive_advisor(fast=True)
            else:
                proactive_advisor, personal_advisor = make_null_advisors()

            personal = personal_advisor.advise(vault, entity_id)
            proactive = proactive_advisor.advise(vault)
            return personal, proactive

        except Exception:
            _log.exception("advisory_vm: advisor failed for entity %s", entity_id)
            try:
                proactive_null, personal_null = make_null_advisors()
                return personal_null.advise(vault, entity_id), proactive_null.advise(
                    vault
                )
            except Exception:
                return None, None

    def chat(
        self,
        entity_id: str,
        question: str,
    ) -> str:
        vault = _build_vault(entity_id)
        if vault is None:
            return "Could not load entity data."

        try:
            from core.types import EntityId as EID

            profile = vault.get_profile(EID(entity_id))

            if profile is not None:
                advisor = make_personal_advisor(fast=True)
                result = advisor.ask(vault, entity_id, question)

                if result.llm_summary and result.llm_summary.strip():
                    return result.llm_summary

                if result.llm_failure:
                    _log.warning(
                        "advisory_vm: chat LLM failure: %s", result.llm_failure
                    )
                    return f"⚠️ Advisor error: {result.llm_failure}"

            _log.info(
                "advisory_vm: no profile for %s — using direct LLM fallback", entity_id
            )
            llm = make_fast_llm()
            response = llm.complete(
                prompt=question,
                context={"task": "direct_chat", "entity_id": entity_id},
            )

            if response.raw_text and response.raw_text.strip():
                return response.raw_text

            if response.has_error:
                _log.warning("advisory_vm: direct LLM failure: %s", response.failure)
                return f"⚠️ LLM error: {response.failure}"

            return "⚠️ No response generated. Try a more specific question."

        except Exception:
            _log.exception("advisory_vm: chat failed for entity %s", entity_id)
            return "An error occurred while processing your question."

    def get_supported_locales(self) -> frozenset[str]:
        return SUPPORTED_LOCALES
