from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

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

_DB_PATH = Path("data/nasmi.db")


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


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    if not _table_exists(conn, table):
        return set()
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(row["name"]) for row in rows}


def _safe_count(conn: sqlite3.Connection, table: str) -> int:
    if not _table_exists(conn, table):
        return 0
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _rows(
    conn: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()
) -> list[dict[str, Any]]:
    try:
        return [dict(row) for row in conn.execute(query, params).fetchall()]
    except Exception:
        _log.exception("advisory_vm: query failed: %s", query)
        return []


def _jsonish(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value)


def _compact_row(row: dict[str, Any], max_fields: int = 8) -> str:
    parts: list[str] = []
    for key, value in row.items():
        if value is None:
            continue
        text = _jsonish(value).strip()
        if not text:
            continue
        if len(text) > 180:
            text = text[:180] + "..."
        parts.append(f"{key}={text}")
        if len(parts) >= max_fields:
            break
    return " | ".join(parts)


def _entity_section(conn: sqlite3.Connection, entity_id: str) -> str:
    if not _table_exists(conn, "entities"):
        return "ENTITY:\n- entities table not found"

    cols = _columns(conn, "entities")
    if "entity_id" in cols:
        rows = _rows(
            conn, "SELECT * FROM entities WHERE entity_id = ? LIMIT 1", (entity_id,)
        )
    elif "id" in cols:
        rows = _rows(conn, "SELECT * FROM entities WHERE id = ? LIMIT 1", (entity_id,))
    else:
        rows = _rows(conn, "SELECT * FROM entities LIMIT 1")

    if not rows:
        return f"ENTITY:\n- Active entity id: {entity_id}\n- Entity row not found"

    return "ENTITY:\n- " + _compact_row(rows[0], max_fields=12)


def _documents_section(conn: sqlite3.Connection, entity_id: str) -> str:
    if not _table_exists(conn, "documents"):
        return "DOCUMENTS:\n- documents table not found"

    cols = _columns(conn, "documents")
    where = ""
    params: tuple[Any, ...] = ()

    if "entity_id" in cols:
        where = "WHERE entity_id = ?"
        params = (entity_id,)

    rows = _rows(
        conn, f"SELECT * FROM documents {where} ORDER BY rowid DESC LIMIT 8", params
    )
    total = _safe_count(conn, "documents")

    lines = ["DOCUMENTS:", f"- Total documents in database: {total}"]
    if not rows:
        lines.append("- No document rows found for this entity")
        return "\n".join(lines)

    for row in rows:
        lines.append(f"- {_compact_row(row, max_fields=8)}")
    return "\n".join(lines)


def _facts_section(conn: sqlite3.Connection, entity_id: str) -> str:
    if not _table_exists(conn, "facts"):
        return "FACTS:\n- facts table not found"

    cols = _columns(conn, "facts")
    total = _safe_count(conn, "facts")

    where = ""
    params: tuple[Any, ...] = ()
    if "entity_id" in cols:
        where = "WHERE entity_id = ?"
        params = (entity_id,)

    rows = _rows(
        conn, f"SELECT * FROM facts {where} ORDER BY rowid DESC LIMIT 30", params
    )

    lines = ["FACTS:", f"- Total facts in database: {total}"]
    if not rows:
        lines.append("- No fact rows found for this entity")
        return "\n".join(lines)

    if "status" in cols:
        status_rows = _rows(
            conn,
            f"SELECT status, COUNT(*) as count FROM facts {where} GROUP BY status",
            params,
        )
        if status_rows:
            lines.append("- Fact status counts:")
            for row in status_rows:
                lines.append(f"  - {row.get('status')}: {row.get('count')}")

    lines.append("- Recent facts:")
    for row in rows:
        lines.append(f"  - {_compact_row(row, max_fields=10)}")

    return "\n".join(lines)


def _review_section(conn: sqlite3.Connection, entity_id: str) -> str:
    if not _table_exists(conn, "review_cases"):
        return "REVIEW QUEUE:\n- review_cases table not found"

    cols = _columns(conn, "review_cases")
    total = _safe_count(conn, "review_cases")

    where = ""
    params: tuple[Any, ...] = ()
    if "entity_id" in cols:
        where = "WHERE entity_id = ?"
        params = (entity_id,)

    rows = _rows(
        conn, f"SELECT * FROM review_cases {where} ORDER BY rowid DESC LIMIT 25", params
    )

    lines = ["REVIEW QUEUE:", f"- Total review cases in database: {total}"]

    if "status" in cols:
        status_rows = _rows(
            conn,
            f"SELECT status, COUNT(*) as count FROM review_cases {where} GROUP BY status",
            params,
        )
        if status_rows:
            lines.append("- Review status counts:")
            for row in status_rows:
                lines.append(f"  - {row.get('status')}: {row.get('count')}")

    if not rows:
        lines.append("- No review cases found for this entity")
        return "\n".join(lines)

    lines.append("- Recent review cases:")
    for row in rows:
        lines.append(f"  - {_compact_row(row, max_fields=10)}")

    return "\n".join(lines)


def _profile_section(conn: sqlite3.Connection, entity_id: str) -> str:
    if not _table_exists(conn, "profiles"):
        return "PROFILE:\n- profiles table not found"

    cols = _columns(conn, "profiles")
    if "entity_id" in cols:
        rows = _rows(
            conn, "SELECT * FROM profiles WHERE entity_id = ? LIMIT 1", (entity_id,)
        )
    else:
        rows = _rows(conn, "SELECT * FROM profiles LIMIT 1")

    if not rows:
        return (
            "PROFILE:\n"
            "- Profile not found for the active entity\n"
            "- Most likely reason: no accepted facts have been used to build a trusted profile yet"
        )

    return "PROFILE:\n- " + _compact_row(rows[0], max_fields=15)


def _noise_section(conn: sqlite3.Connection) -> str:
    if not _table_exists(conn, "noise_items"):
        return "NOISE POOL:\n- noise_items table not found"

    total = _safe_count(conn, "noise_items")
    rows = _rows(conn, "SELECT * FROM noise_items ORDER BY rowid DESC LIMIT 10")

    lines = ["NOISE POOL:", f"- Total noise items: {total}"]
    if not rows:
        lines.append("- No noise items currently stored")
        return "\n".join(lines)

    for row in rows:
        lines.append(f"- {_compact_row(row, max_fields=8)}")
    return "\n".join(lines)


def _database_health_section(conn: sqlite3.Connection) -> str:
    tables = [
        "entities",
        "documents",
        "sources",
        "facts",
        "evidence",
        "fact_evidence",
        "provenance",
        "review_cases",
        "review_decisions",
        "profiles",
        "conflicts",
        "noise_items",
        "jobs",
    ]

    lines = ["DATABASE HEALTH:"]
    for table in tables:
        lines.append(f"- {table}: {_safe_count(conn, table)}")
    return "\n".join(lines)


def _build_system_context(entity_id: str) -> str:
    if not _DB_PATH.exists():
        return "NASMI DATABASE:\n- data/nasmi.db not found"

    try:
        with _connect() as conn:
            sections = [
                _database_health_section(conn),
                _entity_section(conn, entity_id),
                _profile_section(conn, entity_id),
                _documents_section(conn, entity_id),
                _facts_section(conn, entity_id),
                _review_section(conn, entity_id),
                _noise_section(conn),
            ]
            return "\n\n".join(sections)
    except Exception:
        _log.exception("advisory_vm: failed to build system context")
        return "NASMI DATABASE:\n- Failed to read system context"


def _build_grounded_prompt(entity_id: str, question: str, context: str) -> str:
    return f"""
You are NASMI Advisory Assistant.

You must answer using only the NASMI system context below.
Do not pretend that you know information that is not present.
If the user asks who they are, inspect ENTITY, PROFILE, FACTS, DOCUMENTS, and REVIEW QUEUE.
If the profile is missing, explain exactly why.
If facts exist but review cases are high, explain that the system has extracted data but it is not yet trusted enough for profile building.
If data is missing, say what is missing and what the user should do next.
Be direct, practical, and specific.
Do not give generic marketing explanations.
Do not say "I can process" if the data is already present.
Answer in the same language as the user's question.

ACTIVE ENTITY ID:
{entity_id}

NASMI SYSTEM CONTEXT:
{context}

USER QUESTION:
{question}

ANSWER:
""".strip()


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
        if not question.strip():
            return "Please ask a specific question."

        context = _build_system_context(entity_id)
        prompt = _build_grounded_prompt(entity_id, question, context)

        try:
            llm = make_fast_llm()
            response = llm.complete(
                prompt=prompt,
                context={
                    "task": "nasmi_grounded_advisory_chat",
                    "entity_id": entity_id,
                },
            )

            if response.raw_text and response.raw_text.strip():
                return response.raw_text.strip()

            if response.has_error:
                _log.warning("advisory_vm: grounded LLM failure: %s", response.failure)
                return self._fallback_answer(entity_id, question, context)

            return self._fallback_answer(entity_id, question, context)

        except Exception:
            _log.exception("advisory_vm: grounded chat failed for entity %s", entity_id)
            return self._fallback_answer(entity_id, question, context)

    def _fallback_answer(
        self,
        entity_id: str,
        question: str,
        context: str,
    ) -> str:
        question_lower = question.lower()

        if (
            "who" in question_lower
            or "guess" in question_lower
            or "who i am" in question_lower
        ):
            return (
                f"I found the active entity `{entity_id}`, but I cannot reliably identify you yet.\n\n"
                "Current NASMI state shows that documents and extracted facts exist, but no trusted profile has been built yet. "
                "This usually means the extracted facts are still waiting in the Review Queue and have not been accepted as trusted facts.\n\n"
                "Next step: open Review Queue, accept the correct identity facts such as name, birth date, address, document number, or residence permit validity. "
                "After that NASMI can build the profile and answer who you are from verified data."
            )

        if "profile" in question_lower:
            return (
                f"Profile is not available for entity `{entity_id}` yet.\n\n"
                "Reason: NASMI has extracted data, but the profile builder needs accepted trusted facts. "
                "Accept the correct review cases first, then rebuild the profile."
            )

        if "review" in question_lower:
            return (
                "The Review Queue is currently the main blocker. "
                "NASMI has many extracted candidates, but they need confirmation before becoming trusted profile facts."
            )

        return (
            "I loaded NASMI database context, but the LLM did not return a usable answer.\n\n"
            "Important current state:\n"
            f"- Active entity: `{entity_id}`\n"
            "- Documents exist\n"
            "- Facts exist\n"
            "- Profile is missing\n"
            "- Review Queue contains many cases\n\n"
            "Next practical step: review and accept the correct facts, then rebuild the profile."
        )

    def get_supported_locales(self) -> frozenset[str]:
        return SUPPORTED_LOCALES
