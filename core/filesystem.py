from __future__ import annotations

import contextlib
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from core.constants import DEFAULT_ENCODING, MAX_FILE_SIZE, SUPPORTED_EXTENSIONS
from core.exceptions import FileSystemError, ValidationError
from core.guards import require


@dataclass(frozen=True)
class FileInfo:
    path: Path
    size: int
    extension: str
    name: str
    stem: str


def exists(path: Path) -> bool:
    require(isinstance(path, Path), "path must be a Path")
    return path.exists()


def is_file(path: Path) -> bool:
    require(isinstance(path, Path), "path must be a Path")
    return path.is_file()


def is_directory(path: Path) -> bool:
    require(isinstance(path, Path), "path must be a Path")
    return path.is_dir()


def file_size(path: Path) -> int:
    require(isinstance(path, Path), "path must be a Path")
    require(path.is_file(), f"not a file: {path}")
    return path.stat().st_size


def file_extension(path: Path) -> str:
    require(isinstance(path, Path), "path must be a Path")
    return path.suffix.lower()


def file_info(path: Path) -> FileInfo:
    require(isinstance(path, Path), "path must be a Path")
    require(path.is_file(), f"not a file: {path}")
    return FileInfo(
        path=path,
        size=path.stat().st_size,
        extension=path.suffix.lower(),
        name=path.name,
        stem=path.stem,
    )


def list_files(
    directory: Path,
    extension: str | None = None,
    recursive: bool = False,
) -> list[Path]:
    require(isinstance(directory, Path), "directory must be a Path")
    require(directory.is_dir(), f"not a directory: {directory}")
    if extension:
        pattern = f"**/*{extension}" if recursive else f"*{extension}"
    else:
        pattern = "**/*" if recursive else "*"
    return [p for p in directory.glob(pattern) if p.is_file()]


def ensure_directory(path: Path) -> None:
    require(isinstance(path, Path), "path must be a Path")
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise FileSystemError(f"failed to create directory: {path}") from exc


def read_bytes(path: Path) -> bytes:
    require(isinstance(path, Path), "path must be a Path")
    require(path.is_file(), f"not a file: {path}")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise FileSystemError(f"failed to read file: {path}") from exc


def read_text(path: Path) -> str:
    require(isinstance(path, Path), "path must be a Path")
    require(path.is_file(), f"not a file: {path}")
    try:
        return path.read_text(encoding=DEFAULT_ENCODING)
    except OSError as exc:
        raise FileSystemError(f"failed to read file: {path}") from exc


def write_bytes(path: Path, data: bytes) -> None:
    require(isinstance(path, Path), "path must be a Path")
    require(isinstance(data, bytes), "data must be bytes")
    ensure_directory(path.parent)
    try:
        path.write_bytes(data)
    except OSError as exc:
        raise FileSystemError(f"failed to write file: {path}") from exc


def write_text(path: Path, content: str) -> None:
    require(isinstance(path, Path), "path must be a Path")
    require(isinstance(content, str), "content must be a string")
    ensure_directory(path.parent)
    try:
        path.write_text(content, encoding=DEFAULT_ENCODING)
    except OSError as exc:
        raise FileSystemError(f"failed to write file: {path}") from exc


def write_atomic(path: Path, data: bytes) -> None:
    require(isinstance(path, Path), "path must be a Path")
    require(isinstance(data, bytes), "data must be bytes")
    ensure_directory(path.parent)
    fd, tmp_path_str = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, path)
    except OSError as exc:
        with contextlib.suppress(OSError):
            tmp_path.unlink(missing_ok=True)
        raise FileSystemError(f"atomic write failed: {path}") from exc


def write_atomic_text(path: Path, content: str) -> None:
    require(isinstance(path, Path), "path must be a Path")
    require(isinstance(content, str), "content must be a string")
    write_atomic(path, content.encode(DEFAULT_ENCODING))


def copy_file(source: Path, destination: Path) -> None:
    require(isinstance(source, Path), "source must be a Path")
    require(isinstance(destination, Path), "destination must be a Path")
    require(source.is_file(), f"source is not a file: {source}")
    ensure_directory(destination.parent)
    try:
        shutil.copy2(source, destination)
    except OSError as exc:
        raise FileSystemError(f"failed to copy {source} → {destination}") from exc


def move_file(source: Path, destination: Path) -> None:
    require(isinstance(source, Path), "source must be a Path")
    require(isinstance(destination, Path), "destination must be a Path")
    require(source.is_file(), f"source is not a file: {source}")
    ensure_directory(destination.parent)
    try:
        shutil.move(str(source), str(destination))
    except OSError as exc:
        raise FileSystemError(f"failed to move {source} → {destination}") from exc


def delete_file(path: Path) -> None:
    require(isinstance(path, Path), "path must be a Path")
    if not path.exists():
        return
    require(path.is_file(), f"not a file: {path}")
    try:
        path.unlink()
    except OSError as exc:
        raise FileSystemError(f"failed to delete file: {path}") from exc


def delete_directory(path: Path, recursive: bool = False) -> None:
    require(isinstance(path, Path), "path must be a Path")
    if not path.exists():
        return
    require(path.is_dir(), f"not a directory: {path}")
    try:
        if recursive:
            shutil.rmtree(path)
        else:
            path.rmdir()
    except OSError as exc:
        raise FileSystemError(f"failed to delete directory: {path}") from exc


def assert_allowed_extension(path: Path) -> None:
    require(isinstance(path, Path), "path must be a Path")
    require(path.suffix != "", "file has no extension")
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValidationError(f"unsupported file extension: {ext!r}")


def assert_allowed_size(path: Path, max_size: int = MAX_FILE_SIZE) -> None:
    require(isinstance(path, Path), "path must be a Path")
    require(path.is_file(), f"not a file: {path}")
    size = path.stat().st_size
    if size > max_size:
        raise ValidationError(
            f"file size {size} exceeds maximum allowed {max_size}: {path}"
        )
