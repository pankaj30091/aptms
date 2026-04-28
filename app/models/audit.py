from datetime import datetime, timezone
from app import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    performed_by = db.Column(db.Integer, nullable=False)
    user_email = db.Column(db.String(255), nullable=False)
    action = db.Column(db.String(20), nullable=False)  # CREATE, UPDATE, DELETE
    table_name = db.Column(db.String(100), nullable=False)
    record_id = db.Column(db.Integer, nullable=False)
    old_values = db.Column(db.JSON)
    new_values = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        db.Index("idx_audit_table_record", "table_name", "record_id"),
        db.Index("idx_audit_user", "performed_by", "created_at"),
    )
