from __future__ import annotations

from pathlib import Path
from typing import Any, NewType, TypeAlias

DocumentId = NewType("DocumentId", str)
ReviewId = NewType("ReviewId", str)
ReviewCaseId = NewType("ReviewCaseId", str)
ReviewDecisionId = NewType("ReviewDecisionId", str)
ReviewQueueId = NewType("ReviewQueueId", str)
KnowledgeId = NewType("KnowledgeId", str)
PackageId = NewType("PackageId", str)
JobId = NewType("JobId", str)
UserId = NewType("UserId", str)
AuditId = NewType("AuditId", str)
FormId = NewType("FormId", str)
EntityId = NewType("EntityId", str)
RecordId = NewType("RecordId", str)
ConflictId = NewType("ConflictId", str)
ArtifactId = NewType("ArtifactId", str)
FailureId = NewType("FailureId", str)
SourceId = NewType("SourceId", str)
FactId = NewType("FactId", str)
CandidateFactId = NewType("CandidateFactId", str)
ExtractionResultId = NewType("ExtractionResultId", str)
ExtractionRequestId = NewType("ExtractionRequestId", str)
EvidenceId = NewType("EvidenceId", str)
FactEvidenceId = NewType("FactEvidenceId", str)
ProvenanceId = NewType("ProvenanceId", str)
ProfileId = NewType("ProfileId", str)
VaultId = NewType("VaultId", str)
FormFieldId = NewType("FormFieldId", str)
FormTemplateId = NewType("FormTemplateId", str)
FormSubmissionId = NewType("FormSubmissionId", str)
OcrBlockId = NewType("OcrBlockId", str)
OcrCellId = NewType("OcrCellId", str)
OcrRowId = NewType("OcrRowId", str)
OcrTableId = NewType("OcrTableId", str)
OcrPageId = NewType("OcrPageId", str)
OcrResultId = NewType("OcrResultId", str)
OcrRequestId = NewType("OcrRequestId", str)
OcrLineId = NewType("OcrLineId", str)
OcrWordId = NewType("OcrWordId", str)

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
