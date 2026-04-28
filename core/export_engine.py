import json
import csv
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum
import config
from core.events import Event, EventType
from core.event_bus import bus


class ExportFormat(Enum):
    PDF = "pdf"
    JSON = "json"
    CSV = "csv"
    TXT = "txt"


@dataclass
class ExportResult:
    success: bool
    path: str
    format: ExportFormat
    size_bytes: int
    exported_at: str

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "path": self.path,
            "format": self.format.value,
            "size_bytes": self.size_bytes,
            "exported_at": self.exported_at,
        }


class ExportEngine:

    def __init__(self) -> None:
        self._output_dir = config.OUTPUT_DIR
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    def _resolve_path(self, filename: str) -> Path:
        return self._output_dir / filename

    def _publish(self, path: str, format: ExportFormat) -> None:
        bus.publish(
            Event(
                event_type=EventType.EXPORT_GENERATED,
                payload={"path": path, "format": format.value},
                source="export_engine",
            )
        )

    def export_json(
        self, data: dict | list, filename: str | None = None
    ) -> ExportResult:
        filename = filename or f"export_{self._timestamp()}.json"
        path = self._resolve_path(filename)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        result = ExportResult(
            success=True,
            path=str(path),
            format=ExportFormat.JSON,
            size_bytes=path.stat().st_size,
            exported_at=datetime.now(timezone.utc).isoformat(),
        )
        self._publish(str(path), ExportFormat.JSON)
        return result

    def export_csv(self, rows: list[dict], filename: str | None = None) -> ExportResult:
        filename = filename or f"export_{self._timestamp()}.csv"
        path = self._resolve_path(filename)

        if not rows:
            path.write_text("", encoding="utf-8")
        else:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

        result = ExportResult(
            success=True,
            path=str(path),
            format=ExportFormat.CSV,
            size_bytes=path.stat().st_size,
            exported_at=datetime.now(timezone.utc).isoformat(),
        )
        self._publish(str(path), ExportFormat.CSV)
        return result

    def export_audit_log(
        self, events: list[dict], filename: str | None = None
    ) -> ExportResult:
        filename = filename or f"audit_log_{self._timestamp()}.json"
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_events": len(events),
            "events": events,
        }
        return self.export_json(payload, filename)

    def export_knowledge_report(
        self, report: dict, filename: str | None = None
    ) -> ExportResult:
        filename = filename or f"knowledge_report_{self._timestamp()}.json"
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "system": config.APP["name"],
            "version": config.APP["version"],
            "report": report,
        }
        return self.export_json(payload, filename)

    def export_identity_summary(
        self, identity: dict, filename: str | None = None
    ) -> ExportResult:
        filename = filename or f"identity_summary_{self._timestamp()}.json"
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "identity": identity,
        }
        return self.export_json(payload, filename)

    def export_txt(self, content: str, filename: str | None = None) -> ExportResult:
        filename = filename or f"export_{self._timestamp()}.txt"
        path = self._resolve_path(filename)
        path.write_text(content, encoding="utf-8")

        result = ExportResult(
            success=True,
            path=str(path),
            format=ExportFormat.TXT,
            size_bytes=path.stat().st_size,
            exported_at=datetime.now(timezone.utc).isoformat(),
        )
        self._publish(str(path), ExportFormat.TXT)
        return result


export_engine = ExportEngine()
