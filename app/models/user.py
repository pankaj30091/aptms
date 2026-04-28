from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    phone = db.Column(db.String(20))
    full_name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, manager, resident
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    flat_number = db.Column(db.String(20))
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    deleted_at = db.Column(db.DateTime(timezone=True))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "phone": self.phone,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "flat_number": self.flat_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_manager(self):
        return self.role == "manager"

    def get_id(self):
        return str(self.id)


class BuildingConfig(db.Model):
    __tablename__ = "building_config"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    latitude = db.Column(db.Numeric(10, 7), nullable=False)
    longitude = db.Column(db.Numeric(10, 7), nullable=False)
    geofence_radius_m = db.Column(db.Integer, nullable=False, default=50)
    address = db.Column(db.Text)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
