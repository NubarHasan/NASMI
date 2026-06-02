from __future__ import annotations

from dataclasses import dataclass

from core.guards import require
from knowledge.application_package_manifest import PackageMetadata
from output.output_document import OutputDocument


@dataclass(frozen=True)
class AssemblyResult:
    output_document: OutputDocument
    metadata: PackageMetadata

    def __post_init__(self) -> None:
        require(
            self.metadata.package_hash is not None,
            "AssemblyResult.metadata.package_hash must not be None",
        )
