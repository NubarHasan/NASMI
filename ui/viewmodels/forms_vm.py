from __future__ import annotations

import contextlib
import io
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import fitz
from pypdf import PdfReader, PdfWriter

from ui.services.api_client import _get_db
from ui.viewmodels.profile_vm import ProfileVM


@dataclass(frozen=True)
class DynamicFormTemplate:
    template_id: str
    name: str
    description: str
    form_type: str
    source_file_path: str
    status: str
    metadata: dict[str, Any]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class DynamicFormField:
    field_id: str
    template_id: str
    field_name: str
    label: str
    field_type: str
    page: int
    x: float
    y: float
    width: float
    height: float
    required: bool
    profile_field_name: str
    extraction_source: str
    confidence: float
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class DynamicFormPreviewField:
    field_id: str
    field_name: str
    label: str
    field_type: str
    required: bool
    profile_field_name: str
    value: str
    is_missing: bool
    page: int
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class DynamicFormReadiness:
    template_id: str
    template_name: str
    is_ready: bool
    total_required: int
    filled_required: int
    missing_required: tuple[str, ...]
    completeness: float


@dataclass(frozen=True)
class DynamicFormPreview:
    template: DynamicFormTemplate
    fields: tuple[DynamicFormPreviewField, ...]
    readiness: DynamicFormReadiness


@dataclass(frozen=True)
class VMResult:
    success: bool
    message: str = ""
    error: str = ""


@dataclass(frozen=True)
class PdfAnalyzeResult:
    success: bool
    message: str = ""
    error: str = ""
    field_count: int = 0
    created_count: int = 0
    skipped_count: int = 0
    pdf_type: str = "unknown"


@dataclass(frozen=True)
class PdfFillResult:
    success: bool
    output_path: str = ""
    message: str = ""
    error: str = ""
    filled_count: int = 0
    missing_count: int = 0


@dataclass(frozen=True)
class SmartPrepareResult:
    success: bool
    message: str = ""
    error: str = ""
    total_fields: int = 0
    recognized_fields: int = 0
    auto_mapped_fields: int = 0
    review_fields: int = 0
    hidden_fields: int = 0


@dataclass(frozen=True)
class SmartFieldView:
    field: DynamicFormField
    display_name: str
    group: str
    status: str
    is_visible: bool
    needs_review: bool
    position_text: str


class FormsVM:
    def __init__(self) -> None:
        self.profile_vm = ProfileVM()
        self.forms_dir = Path("data/forms/templates")
        self.filled_dir = Path("data/forms/filled")
        self.forms_dir.mkdir(parents=True, exist_ok=True)
        self.filled_dir.mkdir(parents=True, exist_ok=True)
        self.ensure_tables()

    def ensure_tables(self) -> None:
        conn = _get_db().connection

        conn.execute("""
            CREATE TABLE IF NOT EXISTS dynamic_form_templates (
                template_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                form_type TEXT NOT NULL DEFAULT 'custom',
                source_file_path TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'draft',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS dynamic_form_fields (
                field_id TEXT PRIMARY KEY,
                template_id TEXT NOT NULL,
                field_name TEXT NOT NULL,
                label TEXT NOT NULL,
                field_type TEXT NOT NULL DEFAULT 'text',
                page INTEGER NOT NULL DEFAULT 1,
                x REAL NOT NULL DEFAULT 0,
                y REAL NOT NULL DEFAULT 0,
                width REAL NOT NULL DEFAULT 0,
                height REAL NOT NULL DEFAULT 0,
                required INTEGER NOT NULL DEFAULT 0,
                profile_field_name TEXT NOT NULL DEFAULT '',
                extraction_source TEXT NOT NULL DEFAULT 'manual',
                confidence REAL NOT NULL DEFAULT 1.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(template_id) REFERENCES dynamic_form_templates(template_id)
            )
            """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_dynamic_form_fields_template
            ON dynamic_form_fields(template_id)
            """)

        conn.commit()

    def _now(self) -> str:
        return datetime.utcnow().isoformat(timespec="seconds")

    def _template_from_row(self, row: Any) -> DynamicFormTemplate:
        metadata_raw = str(row["metadata"] or "{}")
        try:
            metadata = json.loads(metadata_raw)
        except json.JSONDecodeError:
            metadata = {}

        return DynamicFormTemplate(
            template_id=str(row["template_id"]),
            name=str(row["name"]),
            description=str(row["description"] or ""),
            form_type=str(row["form_type"] or "custom"),
            source_file_path=str(row["source_file_path"] or ""),
            status=str(row["status"] or "draft"),
            metadata=metadata,
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def _field_from_row(self, row: Any) -> DynamicFormField:
        return DynamicFormField(
            field_id=str(row["field_id"]),
            template_id=str(row["template_id"]),
            field_name=str(row["field_name"]),
            label=str(row["label"]),
            field_type=str(row["field_type"] or "text"),
            page=int(row["page"] or 1),
            x=float(row["x"] or 0),
            y=float(row["y"] or 0),
            width=float(row["width"] or 0),
            height=float(row["height"] or 0),
            required=bool(row["required"]),
            profile_field_name=str(row["profile_field_name"] or ""),
            extraction_source=str(row["extraction_source"] or "manual"),
            confidence=float(row["confidence"] or 0),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def create_template(
        self,
        name: str,
        description: str = "",
        form_type: str = "custom",
        source_file_path: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> DynamicFormTemplate:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Template name is required.")

        template_id = f"form_{uuid4().hex}"
        now = self._now()
        final_source_path = ""

        if source_file_path:
            source = Path(source_file_path)
            if source.exists():
                suffix = source.suffix or ".pdf"
                destination = self.forms_dir / f"{template_id}{suffix}"
                shutil.copyfile(source, destination)
                final_source_path = str(destination)

        conn = _get_db().connection
        conn.execute(
            """
            INSERT INTO dynamic_form_templates (
                template_id,
                name,
                description,
                form_type,
                source_file_path,
                status,
                metadata,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                template_id,
                clean_name,
                description.strip(),
                form_type.strip() or "custom",
                final_source_path,
                "draft",
                json.dumps(metadata or {}, ensure_ascii=False),
                now,
                now,
            ),
        )
        conn.commit()

        template = self.get_template(template_id)
        if template is None:
            raise RuntimeError("Template was not created.")
        return template

    def list_templates(self) -> tuple[DynamicFormTemplate, ...]:
        conn = _get_db().connection
        rows = conn.execute("""
            SELECT *
            FROM dynamic_form_templates
            ORDER BY updated_at DESC
            """).fetchall()

        return tuple(self._template_from_row(row) for row in rows)

    def get_template(self, template_id: str | None) -> DynamicFormTemplate | None:
        if not template_id:
            return None

        conn = _get_db().connection
        row = conn.execute(
            """
            SELECT *
            FROM dynamic_form_templates
            WHERE template_id = ?
            """,
            (template_id,),
        ).fetchone()

        if row is None:
            return None

        return self._template_from_row(row)

    def delete_template(self, template_id: str) -> VMResult:
        template = self.get_template(template_id)
        if template is None:
            return VMResult(success=False, error="Template not found.")

        conn = _get_db().connection
        conn.execute(
            "DELETE FROM dynamic_form_fields WHERE template_id = ?", (template_id,)
        )
        conn.execute(
            "DELETE FROM dynamic_form_templates WHERE template_id = ?", (template_id,)
        )
        conn.commit()

        if template.source_file_path:
            path = Path(template.source_file_path)
            if path.exists():
                path.unlink()

        return VMResult(success=True, message="Template deleted.")

    def update_template(
        self,
        template_id: str,
        name: str,
        description: str,
        form_type: str,
        status: str,
    ) -> VMResult:
        if not name.strip():
            return VMResult(success=False, error="Template name is required.")

        conn = _get_db().connection
        conn.execute(
            """
            UPDATE dynamic_form_templates
            SET name = ?,
                description = ?,
                form_type = ?,
                status = ?,
                updated_at = ?
            WHERE template_id = ?
            """,
            (
                name.strip(),
                description.strip(),
                form_type.strip() or "custom",
                status.strip() or "draft",
                self._now(),
                template_id,
            ),
        )
        conn.commit()

        return VMResult(success=True, message="Template updated.")

    def add_field(
        self,
        template_id: str,
        field_name: str,
        label: str,
        field_type: str = "text",
        page: int = 1,
        x: float = 0,
        y: float = 0,
        width: float = 0,
        height: float = 0,
        required: bool = False,
        profile_field_name: str = "",
        extraction_source: str = "manual",
        confidence: float = 1.0,
    ) -> DynamicFormField:
        template = self.get_template(template_id)
        if template is None:
            raise ValueError("Template not found.")

        clean_field_name = field_name.strip()
        clean_label = label.strip()

        if not clean_field_name:
            raise ValueError("Field name is required.")

        if not clean_label:
            clean_label = self.readable_field_label(clean_field_name)

        field_id = f"field_{uuid4().hex}"
        now = self._now()

        conn = _get_db().connection
        conn.execute(
            """
            INSERT INTO dynamic_form_fields (
                field_id,
                template_id,
                field_name,
                label,
                field_type,
                page,
                x,
                y,
                width,
                height,
                required,
                profile_field_name,
                extraction_source,
                confidence,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                field_id,
                template_id,
                clean_field_name,
                clean_label,
                field_type.strip() or "text",
                max(1, int(page)),
                float(x),
                float(y),
                float(width),
                float(height),
                1 if required else 0,
                profile_field_name.strip(),
                extraction_source.strip() or "manual",
                float(confidence),
                now,
                now,
            ),
        )

        conn.execute(
            "UPDATE dynamic_form_templates SET updated_at = ? WHERE template_id = ?",
            (now, template_id),
        )

        conn.commit()

        field = self.get_field(field_id)
        if field is None:
            raise RuntimeError("Field was not created.")
        return field

    def get_field(self, field_id: str | None) -> DynamicFormField | None:
        if not field_id:
            return None

        conn = _get_db().connection
        row = conn.execute(
            "SELECT * FROM dynamic_form_fields WHERE field_id = ?",
            (field_id,),
        ).fetchone()

        if row is None:
            return None

        return self._field_from_row(row)

    def list_fields(self, template_id: str | None) -> tuple[DynamicFormField, ...]:
        if not template_id:
            return tuple()

        conn = _get_db().connection
        rows = conn.execute(
            """
            SELECT *
            FROM dynamic_form_fields
            WHERE template_id = ?
            ORDER BY page ASC, y ASC, x ASC, created_at ASC
            """,
            (template_id,),
        ).fetchall()

        return tuple(self._field_from_row(row) for row in rows)

    def _field_exists(self, template_id: str, field_name: str) -> bool:
        conn = _get_db().connection
        row = conn.execute(
            """
            SELECT field_id
            FROM dynamic_form_fields
            WHERE template_id = ? AND field_name = ?
            LIMIT 1
            """,
            (template_id, field_name),
        ).fetchone()
        return row is not None

    def update_field(
        self,
        field_id: str,
        field_name: str,
        label: str,
        field_type: str,
        page: int,
        x: float,
        y: float,
        width: float,
        height: float,
        required: bool,
        profile_field_name: str,
    ) -> VMResult:
        field = self.get_field(field_id)
        if field is None:
            return VMResult(success=False, error="Field not found.")

        if not field_name.strip():
            return VMResult(success=False, error="Field name is required.")

        now = self._now()
        conn = _get_db().connection
        conn.execute(
            """
            UPDATE dynamic_form_fields
            SET field_name = ?,
                label = ?,
                field_type = ?,
                page = ?,
                x = ?,
                y = ?,
                width = ?,
                height = ?,
                required = ?,
                profile_field_name = ?,
                updated_at = ?
            WHERE field_id = ?
            """,
            (
                field_name.strip(),
                label.strip() or self.readable_field_label(field_name),
                field_type.strip() or "text",
                max(1, int(page)),
                float(x),
                float(y),
                float(width),
                float(height),
                1 if required else 0,
                profile_field_name.strip(),
                now,
                field_id,
            ),
        )

        conn.execute(
            "UPDATE dynamic_form_templates SET updated_at = ? WHERE template_id = ?",
            (now, field.template_id),
        )

        conn.commit()

        return VMResult(success=True, message="Field updated.")

    def delete_field(self, field_id: str) -> VMResult:
        field = self.get_field(field_id)
        if field is None:
            return VMResult(success=False, error="Field not found.")

        now = self._now()
        conn = _get_db().connection
        conn.execute("DELETE FROM dynamic_form_fields WHERE field_id = ?", (field_id,))
        conn.execute(
            "UPDATE dynamic_form_templates SET updated_at = ? WHERE template_id = ?",
            (now, field.template_id),
        )
        conn.commit()

        return VMResult(success=True, message="Field deleted.")

    def delete_fields_for_template(self, template_id: str) -> VMResult:
        template = self.get_template(template_id)
        if template is None:
            return VMResult(success=False, error="Template not found.")

        now = self._now()
        conn = _get_db().connection
        conn.execute(
            "DELETE FROM dynamic_form_fields WHERE template_id = ?", (template_id,)
        )
        conn.execute(
            "UPDATE dynamic_form_templates SET updated_at = ? WHERE template_id = ?",
            (now, template_id),
        )
        conn.commit()

        return VMResult(success=True, message="Fields cleared.")

    def _profile_values(self, entity_id: str | None) -> dict[str, str]:
        if not entity_id:
            return {}

        snapshot = self.profile_vm.load_profile(entity_id)
        if snapshot is None:
            return {}

        result: dict[str, str] = {}

        for field in snapshot.fields:
            value = str(field.value or "").strip()
            if field.field_name and value:
                result[field.field_name] = value

        return result

    def profile_field_options(self, entity_id: str | None) -> tuple[str, ...]:
        if not entity_id:
            return tuple()

        snapshot = self.profile_vm.load_profile(entity_id)
        if snapshot is None:
            return tuple()

        names = sorted(
            {field.field_name for field in snapshot.fields if field.field_name.strip()}
        )
        return tuple(names)

    def build_preview(
        self,
        template_id: str | None,
        entity_id: str | None,
    ) -> DynamicFormPreview | None:
        template = self.get_template(template_id)
        if template is None:
            return None

        form_fields = self.list_smart_visible_fields(template.template_id)
        profile_values = self._profile_values(entity_id)

        preview_fields: list[DynamicFormPreviewField] = []

        for smart_field in form_fields:
            field = smart_field.field
            mapped_name = field.profile_field_name.strip()
            value = profile_values.get(mapped_name, "") if mapped_name else ""
            is_missing = field.required and not value.strip()

            preview_fields.append(
                DynamicFormPreviewField(
                    field_id=field.field_id,
                    field_name=field.field_name,
                    label=field.label,
                    field_type=field.field_type,
                    required=field.required,
                    profile_field_name=mapped_name,
                    value=value,
                    is_missing=is_missing,
                    page=field.page,
                    x=field.x,
                    y=field.y,
                    width=field.width,
                    height=field.height,
                )
            )

        required_fields = [field for field in preview_fields if field.required]
        missing = tuple(field.label for field in required_fields if field.is_missing)

        total_required = len(required_fields)
        filled_required = total_required - len(missing)
        completeness = (
            round(filled_required / total_required, 2) if total_required > 0 else 1.0
        )

        readiness = DynamicFormReadiness(
            template_id=template.template_id,
            template_name=template.name,
            is_ready=len(missing) == 0,
            total_required=total_required,
            filled_required=filled_required,
            missing_required=missing,
            completeness=completeness,
        )

        return DynamicFormPreview(
            template=template,
            fields=tuple(preview_fields),
            readiness=readiness,
        )

    def missing_required_fields(
        self,
        template_id: str | None,
        entity_id: str | None,
    ) -> tuple[str, ...]:
        preview = self.build_preview(template_id, entity_id)
        if preview is None:
            return tuple()
        return preview.readiness.missing_required

    def preview_as_dict(
        self,
        template_id: str | None,
        entity_id: str | None,
    ) -> dict[str, str]:
        preview = self.build_preview(template_id, entity_id)
        if preview is None:
            return {}
        return {field.field_name: field.value for field in preview.fields}

    def suggest_mapping_for_label(self, label: str) -> str:
        text = label.lower().strip()
        normalized = (
            text.replace("_", " ")
            .replace("-", " ")
            .replace(".", " ")
            .replace("ä", "ae")
            .replace("ö", "oe")
            .replace("ü", "ue")
            .replace("ß", "ss")
        )

        rules = {
            "surname": (
                "surname",
                "family name",
                "last name",
                "familienname",
                "nachname",
            ),
            "given_names": (
                "given",
                "given names",
                "first name",
                "vorname",
                "vornamen",
            ),
            "date_of_birth": (
                "birth date",
                "date of birth",
                "geburtsdatum",
                "geburtstag",
            ),
            "place_of_birth": ("birth place", "place of birth", "geburtsort"),
            "nationality": (
                "nationality",
                "staatsangehoerigkeit",
                "staatsangehörigkeit",
            ),
            "passport_number": (
                "passport",
                "passnummer",
                "ausweisnummer",
                "seriennummer",
            ),
            "address": ("address", "anschrift", "adresse", "strasse", "straße"),
            "new_address": ("new address", "neue wohnung", "neue adresse", "wohnung"),
            "email": ("email", "e-mail", "mail"),
            "phone": ("phone", "telefon", "mobile", "handy", "rufnummer"),
            "move_in_date": ("move in", "einzug", "einzugsdatum"),
            "sex": ("sex", "gender", "geschlecht"),
            "marital_status": ("marital", "familienstand"),
        }

        for profile_field, keywords in rules.items():
            if any(keyword in normalized for keyword in keywords):
                return profile_field

        return ""

    def add_suggested_field(
        self,
        template_id: str,
        field_name: str,
        label: str,
        page: int = 1,
        x: float = 0,
        y: float = 0,
        width: float = 0,
        height: float = 0,
        required: bool = False,
    ) -> DynamicFormField:
        suggested_mapping = self.suggest_mapping_for_label(label)

        return self.add_field(
            template_id=template_id,
            field_name=field_name,
            label=label,
            field_type="text",
            page=page,
            x=x,
            y=y,
            width=width,
            height=height,
            required=required,
            profile_field_name=suggested_mapping,
            extraction_source="suggested",
            confidence=0.7 if suggested_mapping else 0.3,
        )

    def parse_pdf_field_position(self, field_name: str) -> dict[str, float | int]:
        pattern = r"\.p(?P<page>\d+)\.x(?P<x>-?\d+(?:\.\d+)?)\.y(?P<y>-?\d+(?:\.\d+)?)"
        match = re.search(pattern, field_name)

        if not match:
            return {"page": 1, "x": 0.0, "y": 0.0}

        return {
            "page": int(match.group("page")) + 1,
            "x": float(match.group("x")),
            "y": float(match.group("y")),
        }

    def readable_field_label(self, field_name: str) -> str:
        position = self.parse_pdf_field_position(field_name)
        page = int(position["page"])
        x = float(position["x"])
        y = float(position["y"])

        if x or y:
            return f"Unknown field · Page {page} · x{int(x)} y{int(y)}"

        clean = (
            field_name.replace("_", " ")
            .replace("-", " ")
            .replace(".", " ")
            .replace("/", " ")
            .strip()
        )

        while "  " in clean:
            clean = clean.replace("  ", " ")

        return clean.title() if clean else field_name

    def readable_field_title(self, field: DynamicFormField) -> str:
        position = self.parse_pdf_field_position(field.field_name)
        page = int(position["page"])
        x = int(float(position["x"]))
        y = int(float(position["y"]))
        label = field.label.strip() or "Unknown field"
        return f"{label} · Page {page} · x{x} y{y}"

    def _pdf_field_type(self, field_data: Any, field_name: str = "") -> str:
        upper_name = field_name.upper()

        if "CHECKBOX" in upper_name:
            return "checkbox"

        if "TEXTAREA" in upper_name:
            return "textarea"

        field_type = str(
            field_data.get("/FT", "") if isinstance(field_data, dict) else ""
        )

        if field_type == "/Btn":
            return "checkbox"

        if field_type == "/Tx":
            return "text"

        if field_type == "/Ch":
            return "text"

        return "text"

    def _make_label_from_pdf_field(self, field_name: str) -> str:
        smart = self._known_anmeldung_field(field_name)
        if smart:
            return str(smart["label"])
        return self.readable_field_label(field_name)

    def analyze_pdf_form(
        self,
        template_id: str,
        clear_existing: bool = False,
    ) -> PdfAnalyzeResult:
        template = self.get_template(template_id)
        if template is None:
            return PdfAnalyzeResult(success=False, error="Template not found.")

        if not template.source_file_path:
            return PdfAnalyzeResult(success=False, error="Template has no PDF file.")

        pdf_path = Path(template.source_file_path)
        if not pdf_path.exists():
            return PdfAnalyzeResult(success=False, error="PDF file not found.")

        try:
            reader = PdfReader(str(pdf_path))
            fields = reader.get_fields() or {}
        except Exception as exc:
            return PdfAnalyzeResult(
                success=False, error=f"Could not read PDF fields: {exc}"
            )

        if not fields:
            return PdfAnalyzeResult(
                success=False,
                error="No fillable PDF fields found. This PDF is probably flat or scanned.",
                field_count=0,
                pdf_type="flat_or_scanned",
            )

        if clear_existing:
            self.delete_fields_for_template(template_id)

        created_count = 0
        skipped_count = 0

        for pdf_field_name, field_data in fields.items():
            clean_name = str(pdf_field_name or "").strip()
            if not clean_name:
                skipped_count += 1
                continue

            if self._field_exists(template_id, clean_name):
                skipped_count += 1
                continue

            position = self.parse_pdf_field_position(clean_name)
            smart = self._known_anmeldung_field(clean_name)

            if smart:
                label = str(smart["label"])
                profile_field_name = str(smart["profile_field_name"])
                required = bool(smart["required"])
                confidence = 0.92
                extraction_source = "pdf_acroform_smart_anmeldung"
            else:
                label = self._make_label_from_pdf_field(clean_name)
                profile_field_name = self.suggest_mapping_for_label(label)
                required = False
                confidence = 0.65 if profile_field_name else 0.25
                extraction_source = "pdf_acroform"

            field_type = self._pdf_field_type(field_data, clean_name)

            self.add_field(
                template_id=template_id,
                field_name=clean_name,
                label=label,
                field_type=field_type,
                page=int(position["page"]),
                x=float(position["x"]),
                y=float(position["y"]),
                width=8 if field_type == "checkbox" else 35,
                height=8 if field_type == "checkbox" else 7,
                required=required,
                profile_field_name=profile_field_name,
                extraction_source=extraction_source,
                confidence=confidence,
            )
            created_count += 1

        now = self._now()
        metadata = dict(template.metadata)
        metadata["pdf_type"] = "fillable"
        metadata["last_analyzed_at"] = now
        metadata["pdf_field_count"] = len(fields)

        conn = _get_db().connection
        conn.execute(
            """
            UPDATE dynamic_form_templates
            SET metadata = ?,
                updated_at = ?
            WHERE template_id = ?
            """,
            (
                json.dumps(metadata, ensure_ascii=False),
                now,
                template_id,
            ),
        )
        conn.commit()

        return PdfAnalyzeResult(
            success=True,
            message=f"PDF analyzed. {created_count} fields created.",
            field_count=len(fields),
            created_count=created_count,
            skipped_count=skipped_count,
            pdf_type="fillable",
        )

    def _known_anmeldung_field(self, field_name: str) -> dict[str, Any] | None:
        position = self.parse_pdf_field_position(field_name)
        page = int(position["page"])
        x = int(round(float(position["x"])))
        y = int(round(float(position["y"])))

        known: dict[tuple[int, int, int], dict[str, Any]] = {
            (1, 22, 85): {
                "label": "Surname",
                "profile_field_name": "surname",
                "required": True,
                "group": "person",
            },
            (1, 112, 85): {
                "label": "Given names",
                "profile_field_name": "given_names",
                "required": True,
                "group": "person",
            },
            (1, 22, 103): {
                "label": "Date of birth",
                "profile_field_name": "date_of_birth",
                "required": True,
                "group": "person",
            },
            (1, 112, 103): {
                "label": "Place of birth",
                "profile_field_name": "place_of_birth",
                "required": False,
                "group": "person",
            },
            (1, 174, 103): {
                "label": "Nationality",
                "profile_field_name": "nationality",
                "required": True,
                "group": "person",
            },
            (1, 32, 243): {
                "label": "Current street and house number",
                "profile_field_name": "address",
                "required": False,
                "group": "address",
            },
            (1, 116, 243): {
                "label": "Move-in date",
                "profile_field_name": "move_in_date",
                "required": False,
                "group": "address",
            },
            (1, 32, 251): {
                "label": "Postal code",
                "profile_field_name": "postal_code",
                "required": False,
                "group": "address",
            },
            (1, 32, 259): {
                "label": "City",
                "profile_field_name": "city",
                "required": False,
                "group": "address",
            },
            (1, 32, 267): {
                "label": "New address",
                "profile_field_name": "new_address",
                "required": False,
                "group": "address",
            },
            (2, 22, 148): {
                "label": "Signature place/date",
                "profile_field_name": "current_date",
                "required": False,
                "group": "signature",
            },
        }

        return known.get((page, x, y))

    def _is_system_or_helper_field(self, field: DynamicFormField) -> bool:
        name = field.field_name.upper()

        if "SYSTEM" in name:
            return True

        if "DUMMY" in name:
            return True

        if name.startswith("ES100.GEMEINDE"):
            return True

        return bool(
            field.field_type == "checkbox"
            and not field.profile_field_name
            and field.confidence < 0.5
        )

    def smart_field_view(self, field: DynamicFormField) -> SmartFieldView:
        smart = self._known_anmeldung_field(field.field_name)
        hidden = self._is_system_or_helper_field(field)

        if smart:
            group = str(smart.get("group", "core"))
            is_visible = True
        elif field.profile_field_name:
            group = "mapped"
            is_visible = True
        elif hidden:
            group = "hidden"
            is_visible = False
        elif field.confidence >= 0.65:
            group = "suggested"
            is_visible = True
        else:
            group = "unknown"
            is_visible = False

        if field.profile_field_name:
            status = "mapped"
            needs_review = False
        elif is_visible:
            status = "needs_review"
            needs_review = True
        else:
            status = "hidden"
            needs_review = False

        position = self.parse_pdf_field_position(field.field_name)
        position_text = f"Page {int(position['page'])} · x{int(float(position['x']))} y{int(float(position['y']))}"

        return SmartFieldView(
            field=field,
            display_name=self.readable_field_title(field),
            group=group,
            status=status,
            is_visible=is_visible,
            needs_review=needs_review,
            position_text=position_text,
        )

    def list_smart_fields(self, template_id: str | None) -> tuple[SmartFieldView, ...]:
        fields = self.list_fields(template_id)
        return tuple(self.smart_field_view(field) for field in fields)

    def list_smart_visible_fields(
        self, template_id: str | None
    ) -> tuple[SmartFieldView, ...]:
        smart_fields = self.list_smart_fields(template_id)
        return tuple(field for field in smart_fields if field.is_visible)

    def list_review_fields(self, template_id: str | None) -> tuple[SmartFieldView, ...]:
        smart_fields = self.list_smart_fields(template_id)
        return tuple(field for field in smart_fields if field.needs_review)

    def smart_prepare_template(self, template_id: str) -> SmartPrepareResult:
        template = self.get_template(template_id)
        if template is None:
            return SmartPrepareResult(success=False, error="Template not found.")

        fields = self.list_fields(template_id)

        if not fields:
            analyze = self.analyze_pdf_form(template_id, clear_existing=False)
            if not analyze.success:
                return SmartPrepareResult(success=False, error=analyze.error)
            fields = self.list_fields(template_id)

        recognized = 0
        auto_mapped = 0

        for field in fields:
            smart = self._known_anmeldung_field(field.field_name)
            if smart:
                recognized += 1
                mapped_name = str(smart["profile_field_name"])
                label = str(smart["label"])
                required = bool(smart["required"])

                result = self.update_field(
                    field_id=field.field_id,
                    field_name=field.field_name,
                    label=label,
                    field_type=field.field_type,
                    page=field.page,
                    x=field.x,
                    y=field.y,
                    width=field.width,
                    height=field.height,
                    required=required,
                    profile_field_name=mapped_name,
                )

                if result.success and mapped_name:
                    auto_mapped += 1
            elif field.profile_field_name:
                auto_mapped += 1

        smart_fields = self.list_smart_fields(template_id)
        review_fields = len([item for item in smart_fields if item.needs_review])
        hidden_fields = len([item for item in smart_fields if not item.is_visible])

        now = self._now()
        metadata = dict(template.metadata)
        metadata["smart_prepared_at"] = now
        metadata["smart_prepare_version"] = "5.4"
        metadata["recognized_fields"] = recognized
        metadata["auto_mapped_fields"] = auto_mapped
        metadata["review_fields"] = review_fields
        metadata["hidden_fields"] = hidden_fields

        conn = _get_db().connection
        conn.execute(
            """
            UPDATE dynamic_form_templates
            SET metadata = ?,
                updated_at = ?
            WHERE template_id = ?
            """,
            (
                json.dumps(metadata, ensure_ascii=False),
                now,
                template_id,
            ),
        )
        conn.commit()

        return SmartPrepareResult(
            success=True,
            message="Form prepared automatically.",
            total_fields=len(fields),
            recognized_fields=recognized,
            auto_mapped_fields=auto_mapped,
            review_fields=review_fields,
            hidden_fields=hidden_fields,
        )

    def get_pdf_page_count(self, template_id: str) -> int:
        template = self.get_template(template_id)
        if template is None or not template.source_file_path:
            return 0

        path = Path(template.source_file_path)
        if not path.exists():
            return 0

        try:
            doc = fitz.open(str(path))
            count = int(doc.page_count)
            doc.close()
            return count
        except Exception:
            return 0

    def render_pdf_page_with_highlight(
        self,
        template_id: str,
        page: int = 1,
        field_id: str | None = None,
        zoom: float = 2.0,
    ) -> bytes:
        template = self.get_template(template_id)
        if template is None or not template.source_file_path:
            return b""

        path = Path(template.source_file_path)
        if not path.exists():
            return b""

        doc = fitz.open(str(path))
        page_index = max(0, int(page) - 1)

        if page_index >= doc.page_count:
            doc.close()
            return b""

        pdf_page = doc.load_page(page_index)
        matrix = fitz.Matrix(float(zoom), float(zoom))
        pix = pdf_page.get_pixmap(matrix=matrix, alpha=False)

        selected_field = self.get_field(field_id) if field_id else None

        if selected_field is not None:
            position = self.parse_pdf_field_position(selected_field.field_name)
            field_page = int(position["page"])

            if field_page == page:
                page_rect = pdf_page.rect
                page_width = float(page_rect.width)
                page_height = float(page_rect.height)

                x_mm = float(position["x"])
                y_mm = float(position["y"])

                x_pdf = x_mm / 210.0 * page_width
                y_pdf = y_mm / 297.0 * page_height

                box_width = selected_field.width if selected_field.width > 0 else 35
                box_height = selected_field.height if selected_field.height > 0 else 8

                w_pdf = box_width / 210.0 * page_width
                h_pdf = box_height / 297.0 * page_height

                shape = pdf_page.new_shape()
                rect = fitz.Rect(x_pdf, y_pdf, x_pdf + w_pdf, y_pdf + h_pdf)
                shape.draw_rect(rect)
                shape.finish(color=(1, 0, 0), fill=None, width=2)
                shape.commit()

                pix = pdf_page.get_pixmap(matrix=matrix, alpha=False)

        png_bytes = pix.tobytes("png")
        doc.close()
        return png_bytes

    def generate_filled_pdf(
        self,
        template_id: str,
        entity_id: str | None,
    ) -> PdfFillResult:
        template = self.get_template(template_id)
        if template is None:
            return PdfFillResult(success=False, error="Template not found.")

        if not template.source_file_path:
            return PdfFillResult(success=False, error="Template has no PDF file.")

        source_path = Path(template.source_file_path)
        if not source_path.exists():
            return PdfFillResult(success=False, error="PDF file not found.")

        smart_fields = self.list_smart_visible_fields(template.template_id)
        fields = [item.field for item in smart_fields]

        if not fields:
            return PdfFillResult(
                success=False,
                error="No usable fields available. Prepare the form first.",
            )

        profile_values = self._profile_values(entity_id)

        values_by_pdf_field: dict[str, str] = {}
        missing_count = 0

        for field in fields:
            mapped_name = field.profile_field_name.strip()
            if not mapped_name:
                if field.required:
                    missing_count += 1
                continue

            value = profile_values.get(mapped_name, "").strip()
            if value:
                values_by_pdf_field[field.field_name] = value
            elif field.required:
                missing_count += 1

        if not values_by_pdf_field:
            return PdfFillResult(
                success=False,
                error="No values found to fill. Check profile mappings and Trusted Profile data.",
                missing_count=missing_count,
            )

        try:
            reader = PdfReader(str(source_path))
            writer = PdfWriter()

            for page in reader.pages:
                writer.add_page(page)

            if "/AcroForm" in reader.trailer["/Root"]:
                writer._root_object.update(
                    {"/AcroForm": reader.trailer["/Root"]["/AcroForm"]}
                )

            for page in writer.pages:
                writer.update_page_form_field_values(page, values_by_pdf_field)

            with contextlib.suppress(Exception):
                writer.set_need_appearances_writer(True)

            output_path = (
                self.filled_dir / f"{template.template_id}_filled_{uuid4().hex[:8]}.pdf"
            )

            with open(output_path, "wb") as output_file:
                writer.write(output_file)

        except Exception as exc:
            return PdfFillResult(
                success=False, error=f"Could not generate filled PDF: {exc}"
            )

        return PdfFillResult(
            success=True,
            output_path=str(output_path),
            message="Filled PDF generated.",
            filled_count=len(values_by_pdf_field),
            missing_count=missing_count,
        )
