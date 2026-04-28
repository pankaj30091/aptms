from datetime import datetime, timezone
from app import db


class LeaveQuota(db.Model):
    __tablename__ = "leave_quotas"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    fiscal_year = db.Column(db.Integer, nullable=False)  # e.g. 2025 = Apr2025-Mar2026
    casual_total = db.Column(db.Integer, nullable=False, default=12)
    sick_total = db.Column(db.Integer, nullable=False, default=7)
    earned_total = db.Column(db.Integer, nullable=False, default=15)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User", backref="leave_quotas")
    __table_args__ = (db.UniqueConstraint("user_id", "fiscal_year", name="uq_leave_quota_user_fy"),)


class LeaveRequest(db.Model):
    __tablename__ = "leave_requests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    leave_type = db.Column(db.String(20), nullable=False)   # casual, sick, earned
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_days = db.Column(db.Numeric(4, 1), nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default="pending")  # pending,approved,rejected,cancelled
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    reviewed_at = db.Column(db.DateTime(timezone=True))
    review_note = db.Column(db.Text)
    fiscal_year = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User", foreign_keys=[user_id], backref="leave_requests")
    reviewer = db.relationship("User", foreign_keys=[reviewed_by])

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "leave_type": self.leave_type,
            "start_date": str(self.start_date),
            "end_date": str(self.end_date),
            "total_days": float(self.total_days),
            "status": self.status,
            "fiscal_year": self.fiscal_year,
        }
