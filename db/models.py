from db.database import Database


class DocumentModel:

    def insert(
        self,
        db: Database,
        filename: str,
        file_type: str,
        file_size: float,
        file_hash: str,
    ):
        cursor = db.execute(
            "INSERT INTO documents (filename, file_type, file_size, file_hash) VALUES (?, ?, ?, ?)",
            (filename, file_type, file_size, file_hash),
        )
        return cursor.lastrowid

    def get_by_id(self, db: Database, doc_id: int):
        return db.fetchone("SELECT * FROM documents WHERE id = ?", (doc_id,))

    def get_by_hash(self, db: Database, file_hash: str):
        return db.fetchone("SELECT * FROM documents WHERE file_hash = ?", (file_hash,))

    def get_all(self, db: Database, status: str | None = None):
        if status:
            return db.fetchall("SELECT * FROM documents WHERE status = ?", (status,))
        return db.fetchall("SELECT * FROM documents")

    def update_status(self, db: Database, doc_id: int, status: str):
        db.execute("UPDATE documents SET status = ? WHERE id = ?", (status, doc_id))


class EntityModel:

    def insert(
        self,
        db: Database,
        document_id: int,
        entity_type: str,
        entity_value: str,
        confidence: float,
        source: str,
    ):
        cursor = db.execute(
            "INSERT INTO entities (document_id, entity_type, entity_value, confidence, source) VALUES (?, ?, ?, ?, ?)",
            (document_id, entity_type, entity_value, confidence, source),
        )
        return cursor.lastrowid

    def get_by_document(self, db: Database, document_id: int):
        return db.fetchall(
            "SELECT * FROM entities WHERE document_id = ?", (document_id,)
        )

    def get_by_type(self, db: Database, entity_type: str):
        return db.fetchall(
            "SELECT * FROM entities WHERE entity_type = ?", (entity_type,)
        )


class KnowledgeModel:

    def upsert(
        self, db: Database, field: str, value: str, confidence: float, source: str
    ):
        db.execute(
            """
            INSERT INTO knowledge (field, value, confidence, source)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(field) DO UPDATE SET
                value      = excluded.value,
                confidence = excluded.confidence,
                source     = excluded.source,
                updated_at = datetime('now')
            """,
            (field, value, confidence, source),
        )

    def get_by_field(self, db: Database, field: str):
        return db.fetchone("SELECT * FROM knowledge WHERE field = ?", (field,))

    def get_all(self, db: Database):
        return db.fetchall("SELECT * FROM knowledge")

    def set_verified(self, db: Database, field: str, verified: int = 1):
        db.execute(
            "UPDATE knowledge SET verified = ? WHERE field = ?", (verified, field)
        )


class ReviewQueueModel:

    def insert(
        self, db: Database, entity_id: int, field: str, value: str, priority: int = 0
    ):
        cursor = db.execute(
            "INSERT INTO review_queue (entity_id, field, value, priority) VALUES (?, ?, ?, ?)",
            (entity_id, field, value, priority),
        )
        return cursor.lastrowid

    def get_pending(self, db: Database):
        return db.fetchall(
            "SELECT * FROM review_queue WHERE status = ? ORDER BY priority DESC",
            ("pending",),
        )

    def resolve(self, db: Database, queue_id: int, resolution: str = "approved"):
        db.execute(
            "UPDATE review_queue SET status = ?, resolved_at = datetime('now') WHERE id = ?",
            (resolution, queue_id),
        )


class ContradictionModel:

    def insert(
        self,
        db: Database,
        field: str,
        value_a: str,
        value_b: str,
        source_a: str,
        source_b: str,
    ):
        cursor = db.execute(
            "INSERT INTO contradictions (field, value_a, value_b, source_a, source_b) VALUES (?, ?, ?, ?, ?)",
            (field, value_a, value_b, source_a, source_b),
        )
        return cursor.lastrowid

    def get_open(self, db: Database):
        return db.fetchall("SELECT * FROM contradictions WHERE status = ?", ("open",))

    def resolve(self, db: Database, contradiction_id: int, resolution: str):
        db.execute(
            "UPDATE contradictions SET status = ?, resolution = ?, resolved_at = datetime('now') WHERE id = ?",
            ("resolved", resolution, contradiction_id),
        )


class IdentityModel:

    def insert(
        self,
        db: Database,
        full_name: str,
        birth_date: str,
        nationality: str,
        id_number: str,
    ):
        cursor = db.execute(
            "INSERT INTO identity_core (full_name, birth_date, nationality, id_number) VALUES (?, ?, ?, ?)",
            (full_name, birth_date, nationality, id_number),
        )
        return cursor.lastrowid

    def get_by_id_number(self, db: Database, id_number: str):
        return db.fetchone(
            "SELECT * FROM identity_core WHERE id_number = ?", (id_number,)
        )

    def get_all(self, db: Database):
        return db.fetchall("SELECT * FROM identity_core")


class AuditLogModel:

    def log(
        self,
        db: Database,
        action: str,
        table_name: str,
        record_id: int,
        performed_by: str,
        details: str = "",
    ):
        db.execute(
            "INSERT INTO audit_log (action, table_name, record_id, performed_by, details) VALUES (?, ?, ?, ?, ?)",
            (action, table_name, record_id, performed_by, details),
        )


class SystemLogModel:

    def log(self, db: Database, level: str, module: str, message: str):
        db.execute(
            "INSERT INTO system_logs (level, module, message) VALUES (?, ?, ?)",
            (level, module, message),
        )

    def get_by_level(self, db: Database, level: str):
        return db.fetchall(
            "SELECT * FROM system_logs WHERE level = ? ORDER BY created_at DESC",
            (level,),
        )


class ProcessingJobModel:

    def insert(self, db: Database, document_id: int, job_type: str):
        cursor = db.execute(
            "INSERT INTO processing_jobs (document_id, job_type) VALUES (?, ?)",
            (document_id, job_type),
        )
        return cursor.lastrowid

    def update_status(
        self, db: Database, job_id: int, status: str, error: str | None = None
    ):
        if error:
            db.execute(
                "UPDATE processing_jobs SET status = ?, error = ?, finished_at = datetime('now') WHERE id = ?",
                (status, error, job_id),
            )
        else:
            db.execute(
                "UPDATE processing_jobs SET status = ?, finished_at = datetime('now') WHERE id = ?",
                (status, job_id),
            )

    def get_by_document(self, db: Database, document_id: int):
        return db.fetchall(
            "SELECT * FROM processing_jobs WHERE document_id = ?", (document_id,)
        )


class SettingsModel:

    def set(self, db: Database, key: str, value: str):
        db.execute(
            """
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value      = excluded.value,
                updated_at = datetime('now')
            """,
            (key, value),
        )

    def get(self, db: Database, key: str):
        row = db.fetchone("SELECT value FROM settings WHERE key = ?", (key,))
        return row["value"] if row else None

    def get_all(self, db: Database):
        return db.fetchall("SELECT * FROM settings")


class ExportModel:

    def insert(self, db: Database, export_type: str, file_path: str, created_by: str):
        cursor = db.execute(
            "INSERT INTO exports (export_type, file_path, created_by) VALUES (?, ?, ?)",
            (export_type, file_path, created_by),
        )
        return cursor.lastrowid

    def update_status(self, db: Database, export_id: int, status: str):
        db.execute("UPDATE exports SET status = ? WHERE id = ?", (status, export_id))

    def get_all(self, db: Database):
        return db.fetchall("SELECT * FROM exports ORDER BY created_at DESC")


class ExpiryAlertModel:

    def insert(
        self,
        db: Database,
        document_id: int,
        field: str,
        value: str,
        expiry_date: str,
        days_remaining: int,
        severity: str = "info",
    ) -> int:
        cursor = db.execute(
            "INSERT INTO expiry_alerts "
            "(document_id, field, value, expiry_date, days_remaining, severity) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (document_id, field, value, expiry_date, days_remaining, severity),
        )
        lastrowid = cursor.lastrowid
        if lastrowid is None:
            raise ValueError("Failed to retrieve last inserted expiry alert ID")
        return lastrowid

    def get_active(self, db: Database) -> list:
        return db.fetchall(
            "SELECT * FROM expiry_alerts WHERE status = ? ORDER BY expiry_date ASC",
            ("active",),
        )

    def get_by_severity(self, db: Database, severity: str) -> list:
        return db.fetchall(
            "SELECT * FROM expiry_alerts WHERE severity = ? AND status = ?"
            " ORDER BY expiry_date ASC",
            (severity, "active"),
        )

    def mark_notified(self, db: Database, alert_id: int) -> None:
        db.execute(
            "UPDATE expiry_alerts SET notified_at = datetime('now') WHERE id = ?",
            (alert_id,),
        )

    def dismiss(self, db: Database, alert_id: int) -> None:
        db.execute(
            "UPDATE expiry_alerts SET status = ? WHERE id = ?",
            ("dismissed", alert_id),
        )

    def get_by_document(self, db: Database, document_id: int) -> list:
        return db.fetchall(
            "SELECT * FROM expiry_alerts WHERE document_id = ? ORDER BY expiry_date ASC",
            (document_id,),
        )
