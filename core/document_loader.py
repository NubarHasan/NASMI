import hashlib
from pathlib import Path
from dataclasses import dataclass, field


SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".docx"}


@dataclass
class LoadedDocument:
    filename: str
    file_type: str
    file_size: float
    file_hash: str
    file_path: Path
    raw_bytes: bytes
    metadata: dict = field(default_factory=dict)


class DocumentLoader:

    def load(self, file_path: str | Path) -> LoadedDocument:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {path.suffix}")

        raw_bytes = path.read_bytes()

        return LoadedDocument(
            filename=path.name,
            file_type=path.suffix.lower().lstrip("."),
            file_size=round(len(raw_bytes) / 1024, 2),
            file_hash=self._hash(raw_bytes),
            file_path=path,
            raw_bytes=raw_bytes,
        )

    def load_from_bytes(self, raw_bytes: bytes, filename: str) -> LoadedDocument:
        suffix = Path(filename).suffix.lower()

        if suffix not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {suffix}")

        return LoadedDocument(
            filename=filename,
            file_type=suffix.lstrip("."),
            file_size=round(len(raw_bytes) / 1024, 2),
            file_hash=self._hash(raw_bytes),
            file_path=Path(filename),
            raw_bytes=raw_bytes,
        )

    def _hash(self, raw_bytes: bytes) -> str:
        return hashlib.sha256(raw_bytes).hexdigest()
