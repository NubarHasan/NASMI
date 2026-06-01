from __future__ import annotations

from dataclasses import dataclass

from core.guards import require
from core.identifiers import (
    is_valid_document_id,
    is_valid_entity_id,
    is_valid_package_id,
)
from core.time import is_valid_timestamp
from core.types import DocumentId, EntityId, PackageId
from output.output_format import OutputFormat
from output.output_ids import OutputDocumentId, is_valid_output_document_id
from output.output_type import OutputType

_SCHEMA_VERSION: int = 1
_PACKAGE_FORMAT_VERSION: int = 1


@dataclass(frozen=True)
class PackageOutputEntry:
    output_document_id: OutputDocumentId
    output_type: OutputType
    output_format: OutputFormat
    file_path: str
    exported_at: str
    content_hash: str

    def __post_init__(self) -> None:
        require(
            is_valid_output_document_id(self.output_document_id),
            f"invalid output_document_id: {self.output_document_id!r}",
        )
        require(
            isinstance(self.output_type, OutputType),
            "output_type must be an OutputType instance",
        )
        require(
            isinstance(self.output_format, OutputFormat),
            "output_format must be an OutputFormat instance",
        )
        require(
            isinstance(self.file_path, str) and bool(self.file_path.strip()),
            "file_path must be a non-empty string",
        )
        require(
            is_valid_timestamp(self.exported_at),
            f"invalid exported_at: {self.exported_at!r}",
        )
        require(
            isinstance(self.content_hash, str) and bool(self.content_hash.strip()),
            "content_hash must be a non-empty string",
        )


@dataclass(frozen=True)
class PackageDocumentEntry:
    document_id: DocumentId
    document_type: str
    file_name: str
    file_path: str
    content_hash: str

    def __post_init__(self) -> None:
        require(
            is_valid_document_id(self.document_id),
            f"invalid document_id: {self.document_id!r}",
        )
        require(
            isinstance(self.document_type, str) and bool(self.document_type.strip()),
            "document_type must be a non-empty string",
        )
        require(
            isinstance(self.file_name, str) and bool(self.file_name.strip()),
            "file_name must be a non-empty string",
        )
        require(
            isinstance(self.file_path, str) and bool(self.file_path.strip()),
            "file_path must be a non-empty string",
        )
        require(
            isinstance(self.content_hash, str) and bool(self.content_hash.strip()),
            "content_hash must be a non-empty string",
        )


@dataclass(frozen=True)
class ApplicationPackageManifest:
    package_id: PackageId
    subject_id: EntityId
    schema_version: int
    package_format_version: int
    created_at: str
    outputs: tuple[PackageOutputEntry, ...]
    documents: tuple[PackageDocumentEntry, ...]
    purpose: str | None = None
    target_authority: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        require(
            is_valid_package_id(self.package_id),
            f"invalid package_id: {self.package_id!r}",
        )
        require(
            is_valid_entity_id(self.subject_id),
            f"invalid subject_id: {self.subject_id!r}",
        )
        require(
            self.schema_version == _SCHEMA_VERSION,
            f"schema_version must be {_SCHEMA_VERSION}, got {self.schema_version}",
        )
        require(
            self.package_format_version == _PACKAGE_FORMAT_VERSION,
            f"package_format_version must be {_PACKAGE_FORMAT_VERSION}, "
            f"got {self.package_format_version}",
        )
        require(
            is_valid_timestamp(self.created_at),
            f"invalid created_at: {self.created_at!r}",
        )
        require(
            isinstance(self.outputs, tuple),
            "outputs must be a tuple",
        )
        require(
            all(isinstance(o, PackageOutputEntry) for o in self.outputs),
            "all outputs must be PackageOutputEntry instances",
        )
        require(
            isinstance(self.documents, tuple),
            "documents must be a tuple",
        )
        require(
            all(isinstance(d, PackageDocumentEntry) for d in self.documents),
            "all documents must be PackageDocumentEntry instances",
        )
        require(
            len(self.outputs) > 0 or len(self.documents) > 0,
            "package must contain at least one output or document",
        )
        output_ids = [o.output_document_id for o in self.outputs]
        require(
            len(output_ids) == len(set(output_ids)),
            "duplicate output_document_id detected in outputs",
        )
        document_ids = [d.document_id for d in self.documents]
        require(
            len(document_ids) == len(set(document_ids)),
            "duplicate document_id detected in documents",
        )
        require(
            self.purpose is None
            or (isinstance(self.purpose, str) and bool(self.purpose.strip())),
            "purpose must be None or a non-empty string",
        )
        require(
            self.target_authority is None
            or (
                isinstance(self.target_authority, str)
                and bool(self.target_authority.strip())
            ),
            "target_authority must be None or a non-empty string",
        )
        require(
            self.notes is None
            or (isinstance(self.notes, str) and bool(self.notes.strip())),
            "notes must be None or a non-empty string",
        )


@dataclass(frozen=True)
class PackageMetadata:
    package_id: PackageId
    manifest_hash: str
    generated_at: str
    package_hash: str | None = None

    def __post_init__(self) -> None:
        require(
            is_valid_package_id(self.package_id),
            f"invalid package_id: {self.package_id!r}",
        )
        require(
            isinstance(self.manifest_hash, str) and bool(self.manifest_hash.strip()),
            "manifest_hash must be a non-empty string",
        )
        require(
            is_valid_timestamp(self.generated_at),
            f"invalid generated_at: {self.generated_at!r}",
        )
        require(
            self.package_hash is None
            or (isinstance(self.package_hash, str) and bool(self.package_hash.strip())),
            "package_hash must be None or a non-empty string",
        )


def build_manifest(
    *,
    package_id: PackageId,
    subject_id: EntityId,
    created_at: str,
    outputs: tuple[PackageOutputEntry, ...],
    documents: tuple[PackageDocumentEntry, ...],
    purpose: str | None = None,
    target_authority: str | None = None,
    notes: str | None = None,
) -> ApplicationPackageManifest:
    require(
        is_valid_package_id(package_id),
        f"invalid package_id: {package_id!r}",
    )
    require(
        is_valid_entity_id(subject_id),
        f"invalid subject_id: {subject_id!r}",
    )
    require(
        is_valid_timestamp(created_at),
        f"invalid created_at: {created_at!r}",
    )
    require(
        isinstance(outputs, tuple),
        "outputs must be a tuple",
    )
    require(
        all(isinstance(o, PackageOutputEntry) for o in outputs),
        "all outputs must be PackageOutputEntry instances",
    )
    require(
        isinstance(documents, tuple),
        "documents must be a tuple",
    )
    require(
        all(isinstance(d, PackageDocumentEntry) for d in documents),
        "all documents must be PackageDocumentEntry instances",
    )
    return ApplicationPackageManifest(
        package_id=package_id,
        subject_id=subject_id,
        schema_version=_SCHEMA_VERSION,
        package_format_version=_PACKAGE_FORMAT_VERSION,
        created_at=created_at,
        outputs=outputs,
        documents=documents,
        purpose=purpose,
        target_authority=target_authority,
        notes=notes,
    )
