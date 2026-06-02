from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from application.assembly_result import AssemblyResult
from application.package_assembly_context import PackageAssemblyContext
from application.package_generator import serialize_manifest
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
    }


class ApplicationPackageAssembler:

    def __init__(self, base_output_dir: Path) -> None:
        require(
            isinstance(base_output_dir, Path),
            "base_output_dir must be a Path instance",
        )
        require(
            base_output_dir.is_dir(),
            f"base_output_dir does not exist: {base_output_dir!r}",
        )
        self._base_output_dir = base_output_dir

    def assemble(self, context: PackageAssemblyContext) -> AssemblyResult:
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

        for entry in manifest.outputs:
            require(
                str(entry.output_document_id) in output_index,
                f"output_document_id not found in context: {entry.output_document_id!r}",
            )
            require(
                output_index[str(entry.output_document_id)].exists(),
                f"output file not found on disk: {output_index[str(entry.output_document_id)]!r}",
            )

        for entry in manifest.documents:
            require(
                str(entry.document_id) in document_index,
                f"document_id not found in context: {entry.document_id!r}",
            )
            require(
                document_index[str(entry.document_id)].exists(),
                f"document file not found on disk: {document_index[str(entry.document_id)]!r}",
            )

        package_dir = self._base_output_dir / str(manifest.package_id)
        require(
            not package_dir.exists(),
            f"package directory already exists: {package_dir!r}",
        )

        try:
            package_dir.mkdir(parents=True, exist_ok=False)

            (package_dir / "manifest.json").write_text(
                json.dumps(
                    serialize_manifest(manifest),
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )

            (package_dir / "metadata.json").write_text(
                json.dumps(
                    _serialize_metadata(metadata),
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )

            for entry in manifest.outputs:
                src = output_index[str(entry.output_document_id)]
                dest = package_dir / entry.file_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)

            for entry in manifest.documents:
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

        except Exception:
            if package_dir.exists():
                shutil.rmtree(package_dir, ignore_errors=True)
            raise

        final_metadata = PackageMetadata(
            package_id=metadata.package_id,
            manifest_hash=metadata.manifest_hash,
            generated_at=metadata.generated_at,
            package_hash=hash_file(zip_path),
        )

        return AssemblyResult(
            output_document=OutputDocument(
                output_document_id=generate_output_document_id(),
                subject_id=manifest.subject_id,
                output_type=OutputType.APPLICATION_PACKAGE,
                output_format=OutputFormat.ZIP,
                file_path=zip_path,
                generated_at=utcnow(),
            ),
            metadata=final_metadata,
        )
