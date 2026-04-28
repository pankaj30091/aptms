from datetime import datetime, timezone
from app import db


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    vendor_name = db.Column(db.String(255))
    doc_type = db.Column(db.String(50))   # contract, amc, license, insurance, other
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)         # renewal alert triggers on this
    document_url = db.Column(db.Text)
    notes = db.Column(db.Text)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    deleted_at = db.Column(db.DateTime(timezone=True))

    uploader = db.relationship("User", backref="documents")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "vendor_name": self.vendor_name,
            "doc_type": self.doc_type,
            "end_date": str(self.end_date) if self.end_date else None,
        }


class ActionItem(db.Model):
    __tablename__ = "action_items"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    priority = db.Column(db.String(20), nullable=False, default="medium")  # low, medium, high, critical
    status = db.Column(db.String(30), nullable=False, default="open")      # open, in_progress, blocked, done, cancelled
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    budget_inr = db.Column(db.Numeric(12, 2))
    target_date = db.Column(db.Date)
    closed_at = db.Column(db.DateTime(timezone=True))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    owner = db.relationship("User", foreign_keys=[owner_id], backref="owned_action_items")
    creator = db.relationship("User", foreign_keys=[created_by], backref="created_action_items")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "priority": self.priority,
            "status": self.status,
            "budget_inr": float(self.budget_inr) if self.budget_inr else None,
            "target_date": str(self.target_date) if self.target_date else None,
        }
