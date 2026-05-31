from __future__ import annotations

from pathlib import Path
from typing import Any, NewType, TypeAlias

DocumentId = NewType("DocumentId", str)
ReviewId = NewType("ReviewId", str)
KnowledgeId = NewType("KnowledgeId", str)
PackageId = NewType("PackageId", str)
JobId = NewType("JobId", str)
UserId = NewType("UserId", str)
AuditId = NewType("AuditId", str)
FormId = NewType("FormId", str)
TemplateId = NewType("TemplateId", str)
EntityId = NewType("EntityId", str)
RecordId = NewType("RecordId", str)
ConflictId = NewType("ConflictId", str)
ArtifactId = NewType("ArtifactId", str)
FailureId = NewType("FailureId", str)
SourceId = NewType("SourceId", str)
FactId = NewType("FactId", str)
EvidenceId = NewType("EvidenceId", str)
FactEvidenceId = NewType("FactEvidenceId", str)
ProvenanceId = NewType("ProvenanceId", str)
ProfileId = NewType("ProfileId", str)
VaultId = NewType("VaultId", str)

HashValue: TypeAlias = str
HMACValue: TypeAlias = str
DocumentHash: TypeAlias = str

ConfidenceScore: TypeAlias = float
Percentage: TypeAlias = float
IsoTimestamp: TypeAlias = str
ErrorCode: TypeAlias = str
MimeType: TypeAlias = str
LanguageCode: TypeAlias = str
FieldName: TypeAlias = str
StageName: TypeAlias = str
ComponentName: TypeAlias = str
VersionNumber: TypeAlias = int
SchemaVersion: TypeAlias = str
PageNumber: TypeAlias = int
PageCount: TypeAlias = int

FilePath: TypeAlias = Path
DirectoryPath: TypeAlias = Path

FieldValue: TypeAlias = str | int | float | bool | list[str] | None
Metadata: TypeAlias = dict[str, Any]
JsonPayload: TypeAlias = dict[str, Any]
