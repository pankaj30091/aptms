from datetime import datetime, timezone
from app import db


class ServiceRequest(db.Model):
    __tablename__ = "service_requests"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    flat_number = db.Column(db.String(20))
    resident_name = db.Column(db.String(255))
    resident_phone = db.Column(db.String(20))
    category = db.Column(db.String(50))  # plumbing, electrical, housekeeping, lift, security, other
    priority = db.Column(db.String(20), nullable=False, default="normal")  # low, normal, high, urgent
    status = db.Column(db.String(30), nullable=False, default="open")      # open, in_progress, resolved, closed, cancelled
    logged_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"))
    resolution_note = db.Column(db.Text)
    resolved_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    logger = db.relationship("User", foreign_keys=[logged_by], backref="logged_requests")
    assignee = db.relationship("User", foreign_keys=[assigned_to], backref="assigned_requests")
    updates = db.relationship("ServiceRequestUpdate", backref="request", lazy="dynamic",
                              order_by="ServiceRequestUpdate.created_at")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "flat_number": self.flat_number,
            "category": self.category,
            "priority": self.priority,
            "status": self.status,
        }


class ServiceRequestUpdate(db.Model):
    __tablename__ = "service_request_updates"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("service_requests.id"), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    old_status = db.Column(db.String(30))
    new_status = db.Column(db.String(30))
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    updater = db.relationship("User", backref="sr_updates")
