from datetime import datetime, timezone
from app import db


class Notice(db.Model):
    __tablename__ = "notices"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))  # general, maintenance, event, urgent
    pinned = db.Column(db.Boolean, nullable=False, default=False)
    posted_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    deleted_at = db.Column(db.DateTime(timezone=True))

    author = db.relationship("User", foreign_keys=[posted_by], backref="notices")

    def is_active(self):
        if self.deleted_at:
            return False
        if self.expires_at and self.expires_at < datetime.now(timezone.utc):
            return False
        return True

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "pinned": self.pinned,
            "posted_by": self.posted_by,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
