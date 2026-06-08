from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.types import EntityId
from ui.services.api_client import _get_db, get_entity, get_knowledge_query


@dataclass(frozen=True)
class ProfileFieldRow:
    field_id: str
    entity_id: str
    field_name: str
    label: str
    value: str
    source: str
    confidence: float | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ProfileBuildResult:
    success: bool
    inserted_count: int = 0
    updated_count: int = 0
    error: str = ""


@dataclass(frozen=True)
class ProfileActionResult:
    success: bool
    error: str = ""


@dataclass(frozen=True)
class ProfileSnapshot:
    entity_id: str
    entity_name: str
    fields: tuple[ProfileFieldRow, ...]
    completeness: float


@dataclass(frozen=True)
class ConnectedEntityFact:
    fact_id: str
    field_name: str
    value: str
    confidence: float | None


@dataclass(frozen=True)
class ConnectedEntityRow:
    relationship_id: str
    entity_id: str
    entity_name: str
    entity_type: str
    relation_type: str
    confidence: float | None
    facts: tuple[ConnectedEntityFact, ...]


@dataclass(frozen=True)
class ProfileSectionSummary:
    section: str
    total_required: int
    filled_required: int
    completeness: float
    missing_fields: tuple[str, ...]


PROFILE_SECTIONS: dict[str, tuple[str, ...]] = {
    "identity": (
        "given_names",
        "surname",
        "full_name",
        "date_of_birth",
        "place_of_birth",
        "nationality",
        "sex",
        "marital_status",
    ),
    "address": (
        "address",
        "street",
        "house_number",
        "zip_code",
        "city",
        "new_address",
        "new_street",
        "new_house_number",
        "new_zip_code",
        "new_city",
    ),
    "passport": (
        "passport_number",
        "issuing_authority",
        "issue_date",
        "valid_until",
        "document_number",
    ),
    "contact": (
        "email",
        "phone",
        "mobile",
    ),
    "residence": (
        "residence_permit_type",
        "residence_permit_number",
        "arrival_date",
        "move_in_date",
        "previous_address",
    ),
    "tax_insurance": (
        "tax_id",
        "health_insurance",
        "social_security_number",
    ),
    "work": (
        "employer",
        "job_title",
        "employment_start_date",
        "income",
    ),
    "education": (
        "school",
        "university",
        "degree",
        "graduation_date",
    ),
    "family": (
        "spouse_name",
        "children",
        "father_name",
        "mother_name",
    ),
}

REQUIRED_PROFILE_FIELDS: tuple[str, ...] = (
    "given_names",
    "surname",
    "date_of_birth",
    "place_of_birth",
    "nationality",
    "address",
    "new_address",
    "passport_number",
)

_LABELS: dict[str, str] = {
    "given_names": "Given Names",
    "surname": "Surname",
    "full_name": "Full Name",
    "date_of_birth": "Date of Birth",
    "place_of_birth": "Place of Birth",
    "nationality": "Nationality",
    "sex": "Sex",
    "marital_status": "Marital Status",
    "address": "Address",
    "street": "Street",
    "house_number": "House Number",
    "zip_code": "ZIP Code",
    "city": "City",
    "new_address": "New Address",
    "new_street": "New Street",
    "new_house_number": "New House Number",
    "new_zip_code": "New ZIP Code",
    "new_city": "New City",
    "passport_number": "Passport Number",
    "issuing_authority": "Issuing Authority",
    "issue_date": "Issue Date",
    "valid_until": "Valid Until",
    "document_number": "Document Number",
    "email": "Email",
    "phone": "Phone",
    "mobile": "Mobile",
    "tax_id": "Tax ID",
    "health_insurance": "Health Insurance",
    "social_security_number": "Social Security Number",
    "residence_permit_type": "Residence Permit Type",
    "residence_permit_number": "Residence Permit Number",
    "arrival_date": "Arrival Date",
    "move_in_date": "Move-in Date",
    "previous_address": "Previous Address",
    "employer": "Employer",
    "job_title": "Job Title",
    "employment_start_date": "Employment Start Date",
    "income": "Income",
    "school": "School",
    "university": "University",
    "degree": "Degree",
    "graduation_date": "Graduation Date",
    "spouse_name": "Spouse Name",
    "children": "Children",
    "father_name": "Father Name",
    "mother_name": "Mother Name",
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _label_for(field_name: str) -> str:
    if field_name in _LABELS:
        return _LABELS[field_name]
    return field_name.replace("_", " ").title()


def _normalise_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalise_field_name(field_name: str) -> str:
    return field_name.strip().lower().replace(" ", "_").replace("-", "_")


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


class ProfileVM:
    def ensure_profile_tables(self) -> None:
        conn = _get_db().connection
        conn.execute("""
            CREATE TABLE IF NOT EXISTS profile_fields (
                field_id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                field_name TEXT NOT NULL,
                label TEXT NOT NULL,
                value TEXT NOT NULL,
                source TEXT NOT NULL,
                confidence REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(entity_id, field_name)
            )
            """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_profile_fields_entity
            ON profile_fields(entity_id)
            """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_profile_fields_entity_field
            ON profile_fields(entity_id, field_name)
            """)
        conn.commit()

    def active_entity_name(self, entity_id: str | None) -> str:
        entity = get_entity(entity_id)
        if entity is None:
            return entity_id or ""
        return entity.display_name

    def load_profile(self, entity_id: str | None) -> ProfileSnapshot | None:
        if not entity_id:
            return None

        self.ensure_profile_tables()

        conn = _get_db().connection
        rows = conn.execute(
            """
            SELECT
                field_id,
                entity_id,
                field_name,
                label,
                value,
                source,
                confidence,
                created_at,
                updated_at
            FROM profile_fields
            WHERE entity_id = ?
            ORDER BY field_name
            """,
            (entity_id,),
        ).fetchall()

        fields = tuple(
            ProfileFieldRow(
                field_id=str(row["field_id"]),
                entity_id=str(row["entity_id"]),
                field_name=str(row["field_name"]),
                label=str(row["label"]),
                value=str(row["value"]),
                source=str(row["source"]),
                confidence=_safe_float(row["confidence"]),
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
            )
            for row in rows
        )

        return ProfileSnapshot(
            entity_id=entity_id,
            entity_name=self.active_entity_name(entity_id),
            fields=fields,
            completeness=self.calculate_completeness(fields),
        )

    def calculate_completeness(self, fields: tuple[ProfileFieldRow, ...]) -> float:
        values = {
            field.field_name: field.value.strip()
            for field in fields
            if field.value.strip()
        }

        if not REQUIRED_PROFILE_FIELDS:
            return 0.0

        filled = sum(1 for name in REQUIRED_PROFILE_FIELDS if values.get(name))
        return round(filled / len(REQUIRED_PROFILE_FIELDS), 2)

    def get_missing_fields(self, fields: tuple[ProfileFieldRow, ...]) -> list[str]:
        values = {
            field.field_name: field.value.strip()
            for field in fields
            if field.value.strip()
        }
        return [name for name in REQUIRED_PROFILE_FIELDS if not values.get(name)]

    def get_fields_by_section(
        self,
        fields: tuple[ProfileFieldRow, ...],
    ) -> dict[str, list[ProfileFieldRow]]:
        organized: dict[str, list[ProfileFieldRow]] = {
            section: [] for section in PROFILE_SECTIONS
        }
        organized["other"] = []

        for field in fields:
            matched = False
            for section, section_fields in PROFILE_SECTIONS.items():
                if field.field_name in section_fields:
                    organized[section].append(field)
                    matched = True
                    break
            if not matched:
                organized["other"].append(field)

        return organized

    def get_section_summaries(
        self,
        fields: tuple[ProfileFieldRow, ...],
    ) -> tuple[ProfileSectionSummary, ...]:
        values = {
            field.field_name: field.value.strip()
            for field in fields
            if field.value.strip()
        }

        summaries: list[ProfileSectionSummary] = []

        for section, section_fields in PROFILE_SECTIONS.items():
            required_in_section = tuple(
                field for field in REQUIRED_PROFILE_FIELDS if field in section_fields
            )

            if not required_in_section:
                continue

            missing = tuple(
                field for field in required_in_section if not values.get(field)
            )
            total_required = len(required_in_section)
            filled_required = total_required - len(missing)
            completeness = (
                round(filled_required / total_required, 2)
                if total_required > 0
                else 0.0
            )

            summaries.append(
                ProfileSectionSummary(
                    section=section,
                    total_required=total_required,
                    filled_required=filled_required,
                    completeness=completeness,
                    missing_fields=missing,
                )
            )

        return tuple(summaries)

    def list_accepted_facts(self, entity_id: str | None) -> list[dict[str, Any]]:
        if not entity_id:
            return []

        try:
            facts = get_knowledge_query().list_accepted_facts(EntityId(entity_id))
            result: list[dict[str, Any]] = []

            for fact in facts:
                value = _normalise_value(
                    getattr(fact, "canonical_value", None)
                    or getattr(fact, "display_value", None)
                    or getattr(fact, "value", None)
                )
                field_name = _normalise_field_name(
                    str(getattr(fact, "field_name", "")).strip()
                    or str(getattr(fact, "attribute_name", "")).strip()
                )

                if not field_name or not value:
                    continue

                result.append(
                    {
                        "field_name": field_name,
                        "label": _label_for(field_name),
                        "value": value,
                        "confidence": getattr(fact, "confidence", None),
                    }
                )

            return result
        except Exception:
            return []

    def build_from_accepted_facts(self, entity_id: str | None) -> ProfileBuildResult:
        if not entity_id:
            return ProfileBuildResult(success=False, error="No active entity selected.")

        self.ensure_profile_tables()

        facts = self.list_accepted_facts(entity_id)
        if not facts:
            return ProfileBuildResult(
                success=False,
                error="No accepted facts found for this entity.",
            )

        conn = _get_db().connection
        inserted_count = 0
        updated_count = 0
        now = _now()

        try:
            for fact in facts:
                field_name = _normalise_field_name(str(fact["field_name"]))
                label = str(fact.get("label") or _label_for(field_name)).strip()
                value = str(fact.get("value") or "").strip()
                confidence = _safe_float(fact.get("confidence"))

                if not field_name or not value:
                    continue

                existing = conn.execute(
                    """
                    SELECT field_id
                    FROM profile_fields
                    WHERE entity_id = ?
                      AND field_name = ?
                    LIMIT 1
                    """,
                    (entity_id, field_name),
                ).fetchone()

                if existing is None:
                    conn.execute(
                        """
                        INSERT INTO profile_fields (
                            field_id,
                            entity_id,
                            field_name,
                            label,
                            value,
                            source,
                            confidence,
                            created_at,
                            updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            f"profile_field_{uuid4().hex}",
                            entity_id,
                            field_name,
                            label,
                            value,
                            "accepted_fact",
                            confidence,
                            now,
                            now,
                        ),
                    )
                    inserted_count += 1
                else:
                    conn.execute(
                        """
                        UPDATE profile_fields
                        SET
                            label = ?,
                            value = ?,
                            source = ?,
                            confidence = ?,
                            updated_at = ?
                        WHERE entity_id = ?
                          AND field_name = ?
                        """,
                        (
                            label,
                            value,
                            "accepted_fact",
                            confidence,
                            now,
                            entity_id,
                            field_name,
                        ),
                    )
                    updated_count += 1

            conn.commit()

            return ProfileBuildResult(
                success=True,
                inserted_count=inserted_count,
                updated_count=updated_count,
            )
        except Exception as exc:
            conn.rollback()
            return ProfileBuildResult(success=False, error=str(exc))

    def add_field(
        self,
        entity_id: str | None,
        field_name: str,
        label: str,
        value: str,
        source: str = "manual",
    ) -> ProfileActionResult:
        if not entity_id:
            return ProfileActionResult(
                success=False, error="No active entity selected."
            )

        clean_field_name = _normalise_field_name(field_name)
        clean_value = value.strip()
        clean_label = label.strip() or _label_for(clean_field_name)

        if not clean_field_name:
            return ProfileActionResult(success=False, error="Field name is required.")

        if not clean_value:
            return ProfileActionResult(success=False, error="Value is required.")

        self.ensure_profile_tables()

        conn = _get_db().connection
        now = _now()

        try:
            conn.execute(
                """
                INSERT INTO profile_fields (
                    field_id,
                    entity_id,
                    field_name,
                    label,
                    value,
                    source,
                    confidence,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_id, field_name)
                DO UPDATE SET
                    label = excluded.label,
                    value = excluded.value,
                    source = excluded.source,
                    updated_at = excluded.updated_at
                """,
                (
                    f"profile_field_{uuid4().hex}",
                    entity_id,
                    clean_field_name,
                    clean_label,
                    clean_value,
                    source,
                    None,
                    now,
                    now,
                ),
            )
            conn.commit()
            return ProfileActionResult(success=True)
        except Exception as exc:
            conn.rollback()
            return ProfileActionResult(success=False, error=str(exc))

    def update_field(
        self,
        field_id: str,
        label: str,
        value: str,
        source: str,
    ) -> ProfileActionResult:
        clean_label = label.strip()
        clean_value = value.strip()
        clean_source = source.strip() or "manual"

        if not field_id:
            return ProfileActionResult(success=False, error="Field ID is required.")

        if not clean_label:
            return ProfileActionResult(success=False, error="Label is required.")

        if not clean_value:
            return ProfileActionResult(success=False, error="Value is required.")

        self.ensure_profile_tables()

        conn = _get_db().connection

        try:
            conn.execute(
                """
                UPDATE profile_fields
                SET
                    label = ?,
                    value = ?,
                    source = ?,
                    updated_at = ?
                WHERE field_id = ?
                """,
                (
                    clean_label,
                    clean_value,
                    clean_source,
                    _now(),
                    field_id,
                ),
            )
            conn.commit()
            return ProfileActionResult(success=True)
        except Exception as exc:
            conn.rollback()
            return ProfileActionResult(success=False, error=str(exc))

    def delete_field(self, field_id: str) -> ProfileActionResult:
        if not field_id:
            return ProfileActionResult(success=False, error="Field ID is required.")

        self.ensure_profile_tables()

        conn = _get_db().connection

        try:
            conn.execute(
                """
                DELETE FROM profile_fields
                WHERE field_id = ?
                """,
                (field_id,),
            )
            conn.commit()
            return ProfileActionResult(success=True)
        except Exception as exc:
            conn.rollback()
            return ProfileActionResult(success=False, error=str(exc))

    def list_connected_entities(self, entity_id: str | None) -> tuple[ConnectedEntityRow, ...]:
        if not entity_id:
            return ()

        conn = _get_db().connection

        try:
            rows = conn.execute(
                """
                SELECT
                    r.relationship_id,
                    r.target_entity_id,
                    r.relation_type,
                    r.confidence,
                    e.display_name,
                    e.entity_type
                FROM entity_relationships r
                JOIN entities e ON e.entity_id = r.target_entity_id
                WHERE r.source_entity_id = ?
                ORDER BY r.relation_type, e.display_name
                """,
                (entity_id,),
            ).fetchall()

            connected: list[ConnectedEntityRow] = []

            for row in rows:
                target_entity_id = str(row["target_entity_id"])

                fact_rows = conn.execute(
                    """
                    SELECT
                        fact_id,
                        field_name,
                        canonical_value,
                        confidence
                    FROM facts
                    WHERE entity_id = ?
                      AND status = 'accepted'
                    ORDER BY field_name
                    """,
                    (target_entity_id,),
                ).fetchall()

                facts = tuple(
                    ConnectedEntityFact(
                        fact_id=str(fact["fact_id"]),
                        field_name=str(fact["field_name"]),
                        value=str(fact["canonical_value"]),
                        confidence=_safe_float(fact["confidence"]),
                    )
                    for fact in fact_rows
                )

                connected.append(
                    ConnectedEntityRow(
                        relationship_id=str(row["relationship_id"]),
                        entity_id=target_entity_id,
                        entity_name=str(row["display_name"]),
                        entity_type=str(row["entity_type"]),
                        relation_type=str(row["relation_type"]),
                        confidence=_safe_float(row["confidence"]),
                        facts=facts,
                    )
                )

            return tuple(connected)
        except Exception:
            return ()


    def clear_profile(self, entity_id: str | None) -> ProfileActionResult:
        if not entity_id:
            return ProfileActionResult(
                success=False, error="No active entity selected."
            )

        self.ensure_profile_tables()

        conn = _get_db().connection

        try:
            conn.execute(
                """
                DELETE FROM profile_fields
                WHERE entity_id = ?
                """,
                (entity_id,),
            )
            conn.commit()
            return ProfileActionResult(success=True)
        except Exception as exc:
            conn.rollback()
            return ProfileActionResult(success=False, error=str(exc))
