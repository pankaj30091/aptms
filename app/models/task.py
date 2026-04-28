from datetime import datetime, timezone
from app import db


class TaskDefinition(db.Model):
    __tablename__ = "task_definitions"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    frequency = db.Column(db.String(20), nullable=False)   # daily, weekly, monthly, one_off
    day_of_week = db.Column(db.SmallInteger)               # 0=Mon…6=Sun for weekly
    day_of_month = db.Column(db.SmallInteger)              # 1-31 for monthly
    one_off_date = db.Column(db.Date)                      # due date for one_off tasks
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    deleted_at = db.Column(db.DateTime(timezone=True))

    creator = db.relationship("User", backref="task_definitions")
    completions = db.relationship("TaskCompletion", backref="definition", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "frequency": self.frequency,
            "day_of_week": self.day_of_week,
            "day_of_month": self.day_of_month,
            "one_off_date": str(self.one_off_date) if self.one_off_date else None,
            "is_active": self.is_active,
        }


class TaskCompletion(db.Model):
    __tablename__ = "task_completions"

    id = db.Column(db.Integer, primary_key=True)
    task_def_id = db.Column(db.Integer, db.ForeignKey("task_definitions.id"), nullable=False)
    completed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    notes = db.Column(db.Text)

    completer = db.relationship("User", backref="task_completions")
    __table_args__ = (db.UniqueConstraint("task_def_id", "due_date", name="uq_task_completion_date"),)
