from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from core.guards import require
from core.identifiers import (
    generate_ocr_request_id,
    is_valid_ocr_request_id,
    is_valid_source_id,
)
from core.types import (
    FilePath,
    LanguageCode,
    Metadata,
    MimeType,
    OcrRequestId,
    SourceId,
)


class OcrInputMode(StrEnum):
    FILE = "file"
    CONTENT = "content"
    HYBRID = "hybrid"


@dataclass(frozen=True)
class OcrRequest:
    ocr_request_id: OcrRequestId
    source_id: SourceId
    file_path: FilePath | None
    content: bytes | None
    mime_type: MimeType | None
    languages: tuple[LanguageCode, ...]
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        require(isinstance(self.ocr_request_id, str), "ocr_request_id must be a str")
        require(
            is_valid_ocr_request_id(self.ocr_request_id),
            "ocr_request_id must be a valid OcrRequestId",
        )
        require(isinstance(self.source_id, str), "source_id must be a str")
        require(
            is_valid_source_id(self.source_id), "source_id must be a valid SourceId"
        )
        require(
            self.file_path is not None or self.content is not None,
            "file_path or content must be provided",
        )
        require(
            self.file_path is None or isinstance(self.file_path, Path),
            "file_path must be a Path or None",
        )
        require(
            self.file_path is None or bool(str(self.file_path).strip()),
            "file_path must not be empty",
        )
        require(
            self.content is None or isinstance(self.content, bytes),
            "content must be bytes or None",
        )
        require(
            self.content is None or len(self.content) > 0,
            "content must not be empty",
        )
        require(
            self.mime_type is None or isinstance(self.mime_type, str),
            "mime_type must be a str or None",
        )
        require(
            self.mime_type is None or bool(self.mime_type.strip()),
            "mime_type must not be empty",
        )
        require(isinstance(self.languages, tuple), "languages must be a tuple")
        require(
            all(isinstance(lang, str) for lang in self.languages),
            "every element of languages must be a str",
        )
        require(
            all(bool(lang.strip()) for lang in self.languages),
            "languages must not contain empty strings",
        )
        require(
            len({lang.strip().lower() for lang in self.languages})
            == len(self.languages),
            "languages must not contain duplicates",
        )
        require(isinstance(self.metadata, dict), "metadata must be a dict")

    @classmethod
    def from_file(
        cls,
        source_id: SourceId,
        file_path: FilePath,
        languages: list[LanguageCode] | tuple[LanguageCode, ...] | None = None,
        mime_type: MimeType | None = None,
        metadata: Metadata | None = None,
    ) -> OcrRequest:
        return cls(
            ocr_request_id=generate_ocr_request_id(),
            source_id=source_id,
            file_path=file_path,
            content=None,
            mime_type=mime_type,
            languages=tuple(languages) if languages is not None else (),
            metadata=dict(metadata) if metadata is not None else {},
        )

    @classmethod
    def from_bytes(
        cls,
        source_id: SourceId,
        content: bytes,
        mime_type: MimeType,
        languages: list[LanguageCode] | tuple[LanguageCode, ...] | None = None,
        metadata: Metadata | None = None,
    ) -> OcrRequest:
        return cls(
            ocr_request_id=generate_ocr_request_id(),
            source_id=source_id,
            file_path=None,
            content=content,
            mime_type=mime_type,
            languages=tuple(languages) if languages is not None else (),
            metadata=dict(metadata) if metadata is not None else {},
        )

    @classmethod
    def from_existing(
        cls,
        ocr_request_id: OcrRequestId,
        source_id: SourceId,
        file_path: FilePath | None,
        content: bytes | None,
        mime_type: MimeType | None,
        languages: list[LanguageCode] | tuple[LanguageCode, ...],
        metadata: Metadata | None = None,
    ) -> OcrRequest:
        return cls(
            ocr_request_id=ocr_request_id,
            source_id=source_id,
            file_path=file_path,
            content=content,
            mime_type=mime_type,
            languages=tuple(languages),
            metadata=dict(metadata) if metadata is not None else {},
        )

    @property
    def has_file(self) -> bool:
        return self.file_path is not None

    @property
    def has_content(self) -> bool:
        return self.content is not None

    @property
    def has_languages(self) -> bool:
        return len(self.languages) > 0

    @property
    def has_mime_type(self) -> bool:
        return self.mime_type is not None

    @property
    def input_mode(self) -> OcrInputMode:
        if self.has_file and self.has_content:
            return OcrInputMode.HYBRID
        if self.has_file:
            return OcrInputMode.FILE
        return OcrInputMode.CONTENT

    @property
    def primary_language(self) -> LanguageCode | None:
        return self.languages[0] if self.has_languages else None
