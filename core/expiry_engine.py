from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional

from db.database import Database
from db.models import ExpiryAlertModel, SystemLogModel, AuditLogModel
from core.event_bus import EventBus
from core.events import Event, EventType

EXPIRY_FIELDS = {
    "expiry_date",
    "valid_until",
    "passport_expiry",
    "visa_expiry",
    "license_expiry",
    "contract_end",
    "insurance_expiry",
}

SEVERITY_LEVELS = {
    "critical": 30,
    "warning": 90,
    "info": 180,
}


@dataclass
class ExpiryResult:
    field: str
    value: str
    expiry_date: date
    days_remaining: int
    severity: str
    document_id: Optional[int] = None


class ExpiryEngine:

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.alert_model = ExpiryAlertModel()
        self.log_model = SystemLogModel()
        self.audit_model = AuditLogModel()

    def _parse_date(self, value: str) -> Optional[date]:
        formats = ["%d.%m.%Y", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]
        for fmt in formats:
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def _get_severity(self, days: int) -> str:
        if days <= SEVERITY_LEVELS["critical"]:
            return "critical"
        if days <= SEVERITY_LEVELS["warning"]:
            return "warning"
        if days <= SEVERITY_LEVELS["info"]:
            return "info"
        return "none"

    def check_field(
        self,
        field: str,
        value: str,
        document_id: Optional[int] = None,
    ) -> Optional[ExpiryResult]:
        if field not in EXPIRY_FIELDS:
            return None

        parsed = self._parse_date(value)
        if not parsed:
            return None

        today = date.today()
        days_remaining = (parsed - today).days
        severity = self._get_severity(days_remaining)

        if severity == "none":
            return None

        return ExpiryResult(
            field=field,
            value=value,
            expiry_date=parsed,
            days_remaining=days_remaining,
            severity=severity,
            document_id=document_id,
        )

    def process(
        self,
        fields: dict[str, str],
        document_id: Optional[int] = None,
    ) -> list[ExpiryResult]:
        results = []
        for field, value in fields.items():
            result = self.check_field(field, value, document_id)
            if result:
                results.append(result)
        return results

    def save_and_notify(
        self,
        results: list[ExpiryResult],
        db: Database,
    ) -> None:
        for result in results:
            alert_id = self.alert_model.insert(
                db=db,
                document_id=result.document_id or 0,
                field=result.field,
                value=result.value,
                expiry_date=result.expiry_date.isoformat(),
                days_remaining=result.days_remaining,
                severity=result.severity,
            )

            self.audit_model.log(
                db=db,
                action="EXPIRY_ALERT_CREATED",
                table_name="expiry_alerts",
                record_id=alert_id,
                performed_by="expiry_engine",
                details=f"{result.field} expires in {result.days_remaining} days",
            )

            self.log_model.log(
                db=db,
                level=result.severity.upper(),
                module="expiry_engine",
                message=f"{result.field} = {result.value} | {result.days_remaining} days remaining",
            )

            self.event_bus.publish(
                Event(
                    event_type=EventType.DOCUMENT_EXPIRED,
                    payload={
                        "alert_id": alert_id,
                        "field": result.field,
                        "value": result.value,
                        "days_remaining": result.days_remaining,
                        "severity": result.severity,
                        "document_id": result.document_id,
                    },
                    source="expiry_engine",
                )
            )

    def run(
        self,
        fields: dict[str, str],
        db: Database,
        document_id: Optional[int] = None,
    ) -> list[ExpiryResult]:
        results = self.process(fields, document_id)
        if results:
            self.save_and_notify(results, db)
        return results
