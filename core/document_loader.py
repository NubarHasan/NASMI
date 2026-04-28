import os
from pathlib import Path
from config import EXTRACTION


class DocumentLoader:

    def __init__(self):
        self.supported_formats = EXTRACTION["supported_formats"]
        self.max_size_mb = EXTRACTION["max_file_size_mb"]

    def validate(self, file_path: str) -> dict:
        path = Path(file_path)

        if not path.exists():
            return {"valid": False, "error": "File not found"}

        ext = path.suffix.lower()
        if ext not in self.supported_formats:
            return {"valid": False, "error": f"Unsupported format: {ext}"}

        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > self.max_size_mb:
            return {"valid": False, "error": f"File too large: {size_mb:.1f}MB"}

        return {"valid": True, "error": None}

    def load(self, file_path: str) -> dict:
        validation = self.validate(file_path)
        if not validation["valid"]:
            return {"success": False, "error": validation["error"], "data": None}

        path = Path(file_path)

        return {
            "success": True,
            "error": None,
            "data": {
                "filename": path.name,
                "file_type": path.suffix.lower(),
                "file_size": round(path.stat().st_size / (1024 * 1024), 3),
                "full_path": str(path.resolve()),
            },
        }

    def load_many(self, file_paths: list) -> list:
        return [self.load(fp) for fp in file_paths]
