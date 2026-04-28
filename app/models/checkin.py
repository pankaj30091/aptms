from datetime import datetime, timezone
from app import db


class ManagerCheckin(db.Model):
    __tablename__ = "manager_checkins"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_type = db.Column(db.String(10), nullable=False)  # check_in, check_out
    latitude = db.Column(db.Numeric(10, 7), nullable=False)
    longitude = db.Column(db.Numeric(10, 7), nullable=False)
    distance_m = db.Column(db.Numeric(8, 2), nullable=False)
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    notes = db.Column(db.Text)

    user = db.relationship("User", backref="checkins")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "event_type": self.event_type,
            "latitude": float(self.latitude),
            "longitude": float(self.longitude),
            "distance_m": float(self.distance_m),
            "recorded_at": self.recorded_at.isoformat(),
            "notes": self.notes,
        }
