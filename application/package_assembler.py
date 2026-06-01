from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from application.package_assembly_context import PackageAssemblyContext
from core.guards import require
from core.hashing import hash_file
from core.time import utcnow
from knowledge.application_package_manifest import PackageMetadata
from output.output_document import OutputDocument
from output.output_format import OutputFormat
from output.output_ids import generate_output_document_id
from output.output_type import OutputType


def _serialize_metadata(metadata: PackageMetadata) -> dict[str, Any]:
    return {
        "package_id": str(metadata.package_id),
        "manifest_hash": metadata.manifest_hash,
        "generated_at": metadata.generated_at,
        "package_hash": metadata.package_hash,
    }


class ApplicationPackageAssembler:

    def __init__(
        self,
        base_output_dir: Path,
    ) -> None:
        require(
            isinstance(base_output_dir, Path),
            "base_output_dir must be a Path instance",
        )
        require(
            base_output_dir.is_dir(),
            f"base_output_dir does not exist: {base_output_dir!r}",
        )
        self._base_output_dir = base_output_dir

    def assemble(
        self,
        context: PackageAssemblyContext,
    ) -> OutputDocument:
        require(
            isinstance(context, PackageAssemblyContext),
            "context must be a PackageAssemblyContext instance",
        )

        manifest = context.result.manifest
        metadata = context.result.metadata

        output_index: dict[str, Path] = {
            str(o.output_document_id): Path(o.file_path) for o in context.outputs
        }
        document_index: dict[str, Path] = {
            str(d.document_id): Path(d.file_path) for d in context.documents
        }

        package_dir = self._base_output_dir / str(manifest.package_id)
        require(
            not package_dir.exists(),
            f"package directory already exists: {package_dir!r}",
        )
        package_dir.mkdir(parents=True, exist_ok=False)

        manifest_data: dict[str, Any] = {
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

        manifest_path = package_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest_data, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        for entry in manifest.outputs:
            require(
                str(entry.output_document_id) in output_index,
                f"output_document_id not found in context: {entry.output_document_id!r}",
            )
            src = output_index[str(entry.output_document_id)]
            dest = package_dir / entry.file_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

        for entry in manifest.documents:
            require(
                str(entry.document_id) in document_index,
                f"document_id not found in context: {entry.document_id!r}",
            )
            src = document_index[str(entry.document_id)]
            dest = package_dir / entry.file_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

        zip_base = self._base_output_dir / str(manifest.package_id)
        shutil.make_archive(
            base_name=str(zip_base),
            format="zip",
            root_dir=package_dir,
        )
        zip_path = zip_base.with_suffix(".zip")

        package_hash = hash_file(zip_path)

        final_metadata = PackageMetadata(
            package_id=metadata.package_id,
            manifest_hash=metadata.manifest_hash,
            generated_at=metadata.generated_at,
            package_hash=package_hash,
        )

        metadata_path = package_dir / "metadata.json"
        metadata_path.write_text(
            json.dumps(
                _serialize_metadata(final_metadata),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        return OutputDocument(
            output_document_id=generate_output_document_id(),
            subject_id=manifest.subject_id,
            output_type=OutputType.APPLICATION_PACKAGE,
            output_format=OutputFormat.ZIP,
            file_path=zip_path,
            generated_at=utcnow(),
        )
