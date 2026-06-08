from __future__ import annotations

import json
import logging
import re
import sqlite3
from pathlib import Path
from typing import Any

from core.identifiers import (
    generate_candidate_fact_id,
    generate_evidence_id,
    generate_review_case_id,
    generate_vault_id,
)
from core.time import utcnow_iso
from core.types import EntityId, VaultId
from knowledge.vault import Vault
from processing.llm.advisor_factory import (
    make_grounded_advisory_llm,
    make_null_advisors,
    make_personal_advisor,
    make_proactive_advisor,
)
from processing.llm.advisory_result import SUPPORTED_LOCALES, AdvisoryResult
from processing.llm.personal_advisor.advice_item import PersonalAdvisoryResult
from ui.services.api_client import get_entity_repo, get_profile_query

_log = logging.getLogger(__name__)

_DB_PATH = Path("data/nasmi.db")
_MAX_CONTEXT_CHARS = 4500
_MAX_PROMPT_CHARS = 6500


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
    conn: sqlite3.Connection,
    query: str,
    params: tuple[Any, ...] = (),
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


def _clean_text(value: Any, max_chars: int = 120) -> str:
    text = _jsonish(value).strip()
    text = re.sub(r"\s+", " ", text)
    bad_fragments = [
        "chat.completion",
        "logprobs",
        "finish_reason",
        "choices",
        "assistant",
        "q4_k_m.gguf",
        "llama",
        "model",
        "object",
        "created",
        "index",
    ]
    lowered = text.lower()
    if any(fragment in lowered for fragment in bad_fragments):
        return ""
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    return text


def _compact_row(
    row: dict[str, Any],
    max_fields: int = 8,
    max_value_chars: int = 100,
) -> str:
    parts: list[str] = []
    preferred = [
        "fact_type",
        "field",
        "name",
        "key",
        "raw_value",
        "normalized_value",
        "value",
        "confidence",
        "status",
        "source_stage",
        "document_id",
        "filename",
        "title",
        "created_at",
        "updated_at",
        "expires_at",
    ]

    ordered_keys = [key for key in preferred if key in row]
    ordered_keys.extend([key for key in row.keys() if key not in ordered_keys])

    for key in ordered_keys:
        value = row.get(key)
        if value is None:
            continue
        text = _clean_text(value, max_value_chars)
        if not text:
            continue
        parts.append(f"{key}={text}")
        if len(parts) >= max_fields:
            break

    return " | ".join(parts)


def _normalize_question(question: str) -> str:
    q = question.strip().lower()
    q = q.replace("?", "")
    q = q.replace("!", "")
    q = re.sub(r"\s+", " ", q)
    return q.strip()


def _is_greeting(question: str) -> bool:
    q = _normalize_question(question)
    greetings = {
        "hi",
        "hello",
        "hey",
        "hi there",
        "hello there",
        "good morning",
        "good afternoon",
        "good evening",
    }
    return q in greetings


def _is_assistant_identity_question(question: str) -> bool:
    q = _normalize_question(question)
    patterns = [
        "who are you",
        "what are you",
        "tell me about yourself",
        "introduce yourself",
        "hi who are you",
        "hello who are you",
        "hey who are you",
    ]
    return any(pattern in q for pattern in patterns)


def _is_assistant_age_question(question: str) -> bool:
    q = _normalize_question(question)
    patterns = [
        "how old are you",
        "what is your age",
        "your age",
        "are you old",
    ]
    return any(pattern in q for pattern in patterns)


def _is_identity_question(question: str) -> bool:
    q = _normalize_question(question)
    identity_phrases = [
        "who am i",
        "who i am",
        "what do you know about me",
        "what you know about me",
        "tell me about me",
        "tell me about myself",
        "do you know me",
        "what is my profile",
        "summarize me",
        "describe me",
    ]
    return any(phrase in q for phrase in identity_phrases)


def _is_review_question(question: str) -> bool:
    q = _normalize_question(question)
    review_phrases = [
        "review",
        "what should i review",
        "review queue",
        "pending facts",
        "pending candidates",
        "what should i accept",
        "what should i fix",
    ]
    return any(phrase in q for phrase in review_phrases)


def _is_profile_question(question: str) -> bool:
    q = _normalize_question(question)
    profile_phrases = [
        "profile",
        "my profile",
        "trusted profile",
        "build profile",
        "rebuild profile",
    ]
    return any(phrase in q for phrase in profile_phrases)


def _is_noise_question(question: str) -> bool:
    q = _normalize_question(question)
    noise_phrases = [
        "noise",
        "noise data",
        "noise pool",
        "check noise",
        "check the noise",
        "check the noise data",
        "show noise",
        "show noise data",
    ]
    return any(phrase in q for phrase in noise_phrases)


def _is_save_info_question(question: str) -> bool:
    q = _normalize_question(question)
    save_words = [
        "save this info",
        "save this information",
        "will you save",
        "can you save",
        "remember this",
        "store this",
        "update my profile",
        "add this to my profile",
    ]
    personal_patterns = [
        "i am ",
        "i'm ",
        "my name is ",
        "years old",
        "my age is ",
    ]
    return any(word in q for word in save_words) and any(
        pattern in q for pattern in personal_patterns
    )


def _greeting_answer(entity_id: str) -> str:
    return (
        "Hi, I am your NASMI Advisory Assistant.\n\n"
        "You can ask me things like:\n"
        "- What do you know about me?\n"
        "- What documents do I have?\n"
        "- What should I review next?\n"
        "- Check the noise data\n\n"
        f"Active entity: `{entity_id}`"
    )


def _assistant_identity_answer() -> str:
    return (
        "I am NASMI Advisory Assistant.\n\n"
        "I help you understand your NASMI data, documents, review queue, profile status, and possible next actions. "
        "I am not the active entity and I should not claim to be you."
    )


def _assistant_age_answer() -> str:
    return (
        "I do not have a personal age. I am NASMI Advisory Assistant, a software assistant inside your NASMI app.\n\n"
        "If you want to ask about your own age, ask: `What do you know about me?`"
    )


def _entity_section(conn: sqlite3.Connection, entity_id: str) -> str:
    if not _table_exists(conn, "entities"):
        return "ENTITY:\n- entities table not found"

    cols = _columns(conn, "entities")
    if "entity_id" in cols:
        rows = _rows(
            conn,
            "SELECT * FROM entities WHERE entity_id = ? LIMIT 1",
            (entity_id,),
        )
    elif "id" in cols:
        rows = _rows(
            conn,
            "SELECT * FROM entities WHERE id = ? LIMIT 1",
            (entity_id,),
        )
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
        conn,
        f"SELECT * FROM documents {where} ORDER BY rowid DESC LIMIT 3",
        params,
    )
    total = _safe_count(conn, "documents")

    lines = ["DOCUMENTS:", f"- Total documents in database: {total}"]
    if not rows:
        lines.append("- No document rows found for this entity")
        return "\n".join(lines)

    for row in rows:
        compact = _compact_row(row, max_fields=6)
        if compact:
            lines.append(f"- {compact}")
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
        conn,
        f"SELECT * FROM facts {where} ORDER BY rowid DESC LIMIT 5",
        params,
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
        compact = _compact_row(row, max_fields=6)
        if compact:
            lines.append(f"  - {compact}")

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
        conn,
        f"SELECT * FROM review_cases {where} ORDER BY rowid DESC LIMIT 6",
        params,
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

    lines.append("- Recent review candidates:")
    for row in rows:
        compact = _compact_row(row, max_fields=6)
        if compact:
            lines.append(f"  - {compact}")

    return "\n".join(lines)


def _profile_section(conn: sqlite3.Connection, entity_id: str) -> str:
    if not _table_exists(conn, "profiles"):
        return "PROFILE:\n- profiles table not found"

    cols = _columns(conn, "profiles")
    if "entity_id" in cols:
        rows = _rows(
            conn,
            "SELECT * FROM profiles WHERE entity_id = ? LIMIT 1",
            (entity_id,),
        )
    else:
        rows = _rows(conn, "SELECT * FROM profiles LIMIT 1")

    if not rows:
        return (
            "PROFILE:\n"
            "- Profile not found for the active entity\n"
            "- Most likely reason: no accepted facts have been used to build a trusted profile yet"
        )

    return "PROFILE:\n- " + _compact_row(rows[0], max_fields=12)


def _noise_rows(conn: sqlite3.Connection, limit: int = 8) -> list[dict[str, Any]]:
    if not _table_exists(conn, "noise_items"):
        return []
    return _rows(conn, f"SELECT * FROM noise_items ORDER BY rowid DESC LIMIT {limit}")


def _noise_section(conn: sqlite3.Connection) -> str:
    if not _table_exists(conn, "noise_items"):
        return "NOISE POOL:\n- noise_items table not found"

    total = _safe_count(conn, "noise_items")
    rows = _noise_rows(conn, limit=3)

    lines = ["NOISE POOL:", f"- Total noise items: {total}"]
    if not rows:
        lines.append("- No noise items currently stored")
        return "\n".join(lines)

    for row in rows:
        compact = _compact_row(row, max_fields=5)
        if compact:
            lines.append(f"- {compact}")
    return "\n".join(lines)


def _database_health_section(conn: sqlite3.Connection) -> str:
    tables = [
        "entities",
        "documents",
        "facts",
        "review_cases",
        "profiles",
        "conflicts",
        "noise_items",
        "jobs",
        "job_queue",
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
            return "\n\n".join(sections)[:_MAX_CONTEXT_CHARS]
    except Exception:
        _log.exception("advisory_vm: failed to build system context")
        return "NASMI DATABASE:\n- Failed to read system context"


def _build_grounded_prompt(entity_id: str, question: str, context: str) -> str:
    prompt = f"""
You are NASMI Advisory Assistant.

Use only the NASMI system context below.
Do not invent facts.
You are the assistant, not the active entity.
Never say that you are the user.
If the user asks who you are, say you are NASMI Advisory Assistant.
If the user asks your age, say you do not have a personal age.
If information is verified in PROFILE or accepted FACTS, say it as trusted.
If information is only in REVIEW QUEUE, say it is an unverified candidate.
If PROFILE is missing, explain that the user must accept correct review facts and rebuild the profile.
Answer in English only.
Keep the answer concise and practical.

ACTIVE ENTITY ID:
{entity_id}

NASMI SYSTEM CONTEXT:
{context}

USER QUESTION:
{question}

ANSWER:
""".strip()
    return prompt[:_MAX_PROMPT_CHARS]


def _get_status_summary(entity_id: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "entity_id": entity_id,
        "documents": 0,
        "facts": 0,
        "review_cases": 0,
        "profiles": 0,
        "review_status": [],
        "fact_status": [],
        "candidates": [],
        "profile": [],
    }

    if not _DB_PATH.exists():
        return result

    try:
        with _connect() as conn:
            result["documents"] = _safe_count(conn, "documents")
            result["facts"] = _safe_count(conn, "facts")
            result["review_cases"] = _safe_count(conn, "review_cases")
            result["profiles"] = _safe_count(conn, "profiles")

            if _table_exists(conn, "review_cases"):
                cols = _columns(conn, "review_cases")
                where = ""
                params: tuple[Any, ...] = ()
                if "entity_id" in cols:
                    where = "WHERE entity_id = ?"
                    params = (entity_id,)

                if "status" in cols:
                    result["review_status"] = _rows(
                        conn,
                        f"SELECT status, COUNT(*) as count FROM review_cases {where} GROUP BY status",
                        params,
                    )

                result["candidates"] = _rows(
                    conn,
                    f"SELECT * FROM review_cases {where} ORDER BY rowid DESC LIMIT 12",
                    params,
                )

            if _table_exists(conn, "facts"):
                cols = _columns(conn, "facts")
                where = ""
                params = ()
                if "entity_id" in cols:
                    where = "WHERE entity_id = ?"
                    params = (entity_id,)

                if "status" in cols:
                    result["fact_status"] = _rows(
                        conn,
                        f"SELECT status, COUNT(*) as count FROM facts {where} GROUP BY status",
                        params,
                    )

            if _table_exists(conn, "profiles"):
                cols = _columns(conn, "profiles")
                if "entity_id" in cols:
                    result["profile"] = _rows(
                        conn,
                        "SELECT * FROM profiles WHERE entity_id = ? LIMIT 1",
                        (entity_id,),
                    )
                else:
                    result["profile"] = _rows(conn, "SELECT * FROM profiles LIMIT 1")

    except Exception:
        _log.exception("advisory_vm: failed to build status summary")

    return result


def _format_candidates(candidates: list[dict[str, Any]], limit: int = 6) -> str:
    if not candidates:
        return "- No visible review candidates are available."

    lines: list[str] = []
    for row in candidates:
        field = (
            row.get("fact_type")
            or row.get("field")
            or row.get("name")
            or row.get("key")
            or "unknown_field"
        )
        value = (
            row.get("normalized_value")
            or row.get("raw_value")
            or row.get("value")
            or row.get("text")
            or ""
        )

        field_text = _clean_text(field, 60)
        value_text = _clean_text(value, 140)

        if not field_text or not value_text:
            continue

        confidence = row.get("confidence")
        status = row.get("status")
        parts = [f"{field_text}: {value_text}"]
        if confidence is not None:
            parts.append(f"confidence={confidence}")
        if status is not None:
            parts.append(f"status={status}")
        lines.append("- " + " | ".join(parts))

        if len(lines) >= limit:
            break

    if not lines:
        return (
            "- Review candidates exist, but the visible rows look noisy or malformed."
        )

    return "\n".join(lines)


def _noise_answer() -> str:
    if not _DB_PATH.exists():
        return "NASMI database was not found."

    try:
        with _connect() as conn:
            if not _table_exists(conn, "noise_items"):
                return "The noise_items table does not exist."

            total = _safe_count(conn, "noise_items")
            rows = _noise_rows(conn, limit=10)

            if not rows:
                return "Noise pool is empty."

            lines = [
                "Noise data summary:",
                f"- Total noise items: {total}",
                "",
                "Recent noise items:",
            ]

            for row in rows:
                compact = _compact_row(row, max_fields=6, max_value_chars=120)
                if compact:
                    lines.append(f"- {compact}")

            return "\n".join(lines)

    except Exception:
        _log.exception("advisory_vm: failed to read noise data")
        return "I could not read the noise data due to a database error."


def _extract_self_declared_facts(question: str) -> list[tuple[str, str]]:
    text = question.strip()
    q = _normalize_question(text)
    facts: list[tuple[str, str]] = []

    name_match = re.search(
        r"\b(?:i am|i'm|my name is)\s+([a-zA-Z][a-zA-Z\s'-]{1,80}?)(?:\s+\d{1,3}\s+years old|\s+and|\s+will|\s+can|\s+save|$)",
        text,
        flags=re.IGNORECASE,
    )
    if name_match:
        name = re.sub(r"\s+", " ", name_match.group(1)).strip()
        if name:
            facts.append(("name", name))

    age_match = re.search(r"\b(\d{1,3})\s+years old\b", q)
    if not age_match:
        age_match = re.search(r"\bmy age is\s+(\d{1,3})\b", q)

    if age_match:
        age = age_match.group(1).strip()
        try:
            age_int = int(age)
            if 0 < age_int < 130:
                facts.append(("age", str(age_int)))
        except Exception:
            pass

    return facts


def _insert_chat_review_case(
    conn: sqlite3.Connection,
    entity_id: str,
    fact_type: str,
    value: str,
    source_text: str,
) -> None:
    cols = _columns(conn, "review_cases")
    now = utcnow_iso()

    data: dict[str, Any] = {
        "review_case_id": str(generate_review_case_id()),
        "entity_id": entity_id,
        "candidate_fact_id": str(generate_candidate_fact_id()),
        "fact_type": fact_type,
        "raw_value": value,
        "normalized_value": value,
        "confidence": 0.5,
        "evidence_ids": json.dumps([str(generate_evidence_id())], ensure_ascii=False),
        "status": "PENDING",
        "priority": "NORMAL",
        "created_at": now,
        "assigned_to": None,
        "metadata": json.dumps(
            {
                "source_stage": "chat_user_claim",
                "source_text": source_text,
                "created_by": "advisory_chat",
                "trust_policy": "unverified_until_user_accepts_review_case",
            },
            ensure_ascii=False,
        ),
    }

    insert_cols = [col for col in data.keys() if col in cols]
    placeholders = ", ".join(["?"] * len(insert_cols))
    col_sql = ", ".join(insert_cols)
    values = tuple(data[col] for col in insert_cols)

    conn.execute(
        f"INSERT INTO review_cases ({col_sql}) VALUES ({placeholders})",
        values,
    )


def _save_info_as_review_candidates(entity_id: str, question: str) -> str:
    facts = _extract_self_declared_facts(question)

    if not facts:
        return (
            "I can help prepare user-provided information for review, but I could not reliably extract a clear fact from your message.\n\n"
            "Try for example:\n"
            "`My name is Nubar Hasan and I am 34 years old. Save this info.`"
        )

    if not _DB_PATH.exists():
        return "NASMI database was not found, so I could not create review candidates."

    try:
        with _connect() as conn:
            if not _table_exists(conn, "review_cases"):
                return "The review_cases table does not exist, so I cannot create pending review candidates."

            for fact_type, value in facts:
                _insert_chat_review_case(conn, entity_id, fact_type, value, question)

            conn.commit()

        lines = [
            "I did not save this as trusted profile data directly.",
            "",
            "I created pending review candidates instead:",
        ]
        for fact_type, value in facts:
            lines.append(f"- {fact_type}: {value}")

        lines.extend(
            [
                "",
                "Next step: go to the Review page, accept the correct candidates, then rebuild the profile.",
            ]
        )

        return "\n".join(lines)

    except Exception:
        _log.exception("advisory_vm: failed to save chat info as review candidates")
        return "I could not create review candidates due to a database error."


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

        if _is_assistant_identity_question(question):
            return _assistant_identity_answer()

        if _is_assistant_age_question(question):
            return _assistant_age_answer()

        if _is_greeting(question):
            return _greeting_answer(entity_id)

        if _is_noise_question(question):
            return _noise_answer()

        if _is_save_info_question(question):
            return _save_info_as_review_candidates(entity_id, question)

        if (
            _is_identity_question(question)
            or _is_review_question(question)
            or _is_profile_question(question)
        ):
            context = _build_system_context(entity_id)
            return self._fallback_answer(entity_id, question, context)

        context = _build_system_context(entity_id)
        prompt = _build_grounded_prompt(entity_id, question, context)

        try:
            llm = make_grounded_advisory_llm()
            response = llm.complete(
                prompt=prompt,
                context={
                    "task": "nasmi_grounded_advisory_chat",
                    "entity_id": entity_id,
                },
            )

            if response.raw_text and response.raw_text.strip():
                text = response.raw_text.strip()
                if "i am nubar" in text.lower() or "i'm nubar" in text.lower():
                    return _assistant_identity_answer()
                return text

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
        summary = _get_status_summary(entity_id)
        candidates = _format_candidates(summary.get("candidates", []))
        has_profile = bool(summary.get("profile"))

        if _is_identity_question(question):
            if has_profile:
                profile_text = "\n".join(
                    f"- {_compact_row(row, max_fields=10)}"
                    for row in summary.get("profile", [])
                    if _compact_row(row, max_fields=10)
                )
                return (
                    f"I found a trusted profile for entity `{entity_id}`:\n\n"
                    f"{profile_text}\n\n"
                    "These are the trusted details currently available. "
                    "You can ask me about your documents, deadlines, risks, or missing facts."
                )

            return (
                f"I can see the active entity `{entity_id}`, but a trusted profile has not been built yet.\n\n"
                "Current NASMI state:\n"
                f"- Documents: {summary.get('documents')}\n"
                f"- Facts: {summary.get('facts')}\n"
                f"- Review cases: {summary.get('review_cases')}\n"
                f"- Profiles: {summary.get('profiles')}\n\n"
                "Extracted but unverified candidates:\n"
                f"{candidates}\n\n"
                "Conclusion: NASMI should not confidently say who you are until the correct facts are accepted from the Review Queue. "
                "Next step: review important candidates such as name, date of birth, address, document number, and expiry dates, then rebuild the profile."
            )

        if _is_profile_question(question):
            if has_profile:
                profile_text = "\n".join(
                    f"- {_compact_row(row, max_fields=10)}"
                    for row in summary.get("profile", [])
                    if _compact_row(row, max_fields=10)
                )
                return f"A trusted profile exists:\n\n{profile_text}"

            return (
                f"No trusted profile exists yet for entity `{entity_id}`.\n\n"
                "Reason: NASMI has extracted data, but those candidates must be accepted from the Review Queue before they become trusted profile facts."
            )

        if _is_review_question(question):
            return (
                "The Review Queue is the main action point now.\n\n"
                f"Review cases: {summary.get('review_cases')}\n\n"
                "Examples of extracted candidates:\n"
                f"{candidates}\n\n"
                "Accept the correct candidates, reject the wrong ones, then rebuild the profile."
            )

        return (
            "I loaded the NASMI database context, but the LLM did not return a usable answer.\n\n"
            "Current state:\n"
            f"- Active entity: `{entity_id}`\n"
            f"- Documents: {summary.get('documents')}\n"
            f"- Facts: {summary.get('facts')}\n"
            f"- Review cases: {summary.get('review_cases')}\n"
            f"- Profiles: {summary.get('profiles')}\n\n"
            "Best next step: review and accept the correct extracted facts, then rebuild the profile."
        )

    def get_supported_locales(self) -> frozenset[str]:
        return SUPPORTED_LOCALES
