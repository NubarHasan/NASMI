from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from application.ports.archive_document_query import ArchiveDocumentQueryService
from application.ports.output_document_query import OutputDocumentQueryService
from archive.document import Document
from core.guards import require
from core.hashing import hash_file, hash_json
from core.identifiers import generate_package_id, is_valid_entity_id
from core.time import format_timestamp, utcnow
from core.types import EntityId
from knowledge.application_package_manifest import (
    ApplicationPackageManifest,
    PackageDocumentEntry,
    PackageMetadata,
    PackageOutputEntry,
    build_manifest,
)
from output.output_document import OutputDocument


@dataclass(frozen=True)
class PackageResult:
    manifest: ApplicationPackageManifest
    metadata: PackageMetadata


def _build_output_path(output: OutputDocument) -> str:
    return f"outputs/{output.output_type.value}/{output.output_document_id}.{output.output_format.value}"


def _build_document_path(document: Document) -> str:
    file_name = Path(document.file_path).name
    return f"documents/{document.document_id}_{file_name}"


def _serialize_manifest(manifest: ApplicationPackageManifest) -> dict[str, Any]:
    return {
        "package_id": str(manifest.package_id),
        "subject_id": str(manifest.subject_id),
        "schema_version": manifest.schema_version,
        "package_format_version": manifest.package_format_version,
        "created_at": manifest.created_at,
        "purpose": manifest.purpose,
        "target_authority": manifest.target_authority,
        "notes": manifest.notes,
        "outputs": [
            {
                "output_document_id": str(e.output_document_id),
                "output_type": e.output_type.value,
                "output_format": e.output_format.value,
                "file_path": e.file_path,
                "exported_at": e.exported_at,
                "content_hash": e.content_hash,
            }
            for e in manifest.outputs
        ],
        "documents": [
            {
                "document_id": str(e.document_id),
                "document_type": e.document_type,
                "file_name": e.file_name,
                "file_path": e.file_path,
                "content_hash": e.content_hash,
            }
            for e in manifest.documents
        ],
    }


class ApplicationPackageGenerator:

    def __init__(
        self,
        output_query: OutputDocumentQueryService,
        document_query: ArchiveDocumentQueryService,
    ) -> None:
        require(
            isinstance(output_query, OutputDocumentQueryService),
            "output_query must implement OutputDocumentQueryService",
        )
        require(
            isinstance(document_query, ArchiveDocumentQueryService),
            "document_query must implement ArchiveDocumentQueryService",
        )
        self._output_query = output_query
        self._document_query = document_query

    def generate(
        self,
        subject_id: EntityId,
        *,
        purpose: str | None = None,
        target_authority: str | None = None,
        notes: str | None = None,
    ) -> PackageResult:
        require(
            is_valid_entity_id(subject_id),
            f"invalid subject_id: {subject_id!r}",
        )

        outputs = self._output_query.list_by_subject(subject_id)
        documents = self._document_query.list_by_subject(subject_id)

        require(
            isinstance(outputs, tuple),
            "OutputDocumentQueryService.list_by_subject must return a tuple",
        )
        require(
            all(isinstance(o, OutputDocument) for o in outputs),
            "all outputs must be OutputDocument instances",
        )
        require(
            isinstance(documents, tuple),
            "ArchiveDocumentQueryService.list_by_subject must return a tuple",
        )
        require(
            all(isinstance(d, Document) for d in documents),
            "all documents must be Document instances",
        )
        require(
            len(outputs) > 0 or len(documents) > 0,
            f"no outputs or documents found for subject: {subject_id!r}",
        )

        output_entries = tuple(
            PackageOutputEntry(
                output_document_id=o.output_document_id,
                output_type=o.output_type,
                output_format=o.output_format,
                file_path=_build_output_path(o),
                exported_at=format_timestamp(o.generated_at),
                content_hash=hash_file(o.file_path),
            )
            for o in outputs
        )

        document_entries = tuple(
            PackageDocumentEntry(
                document_id=d.document_id,
                document_type=d.doc_type,
                file_name=Path(d.file_path).name,
                file_path=_build_document_path(d),
                content_hash=d.file_hash,
            )
            for d in documents
        )

        package_id = generate_package_id()
        created_at = format_timestamp(utcnow())

        manifest = build_manifest(
            package_id=package_id,
            subject_id=subject_id,
            created_at=created_at,
            outputs=output_entries,
            documents=document_entries,
            purpose=purpose,
            target_authority=target_authority,
            notes=notes,
        )

        manifest_hash = hash_json(_serialize_manifest(manifest))

        metadata = PackageMetadata(
            package_id=package_id,
            manifest_hash=manifest_hash,
            generated_at=created_at,
        )

        return PackageResult(manifest=manifest, metadata=metadata)
