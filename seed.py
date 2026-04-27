"""Run once to create the initial admin user and building config."""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from app import create_app, db
from app.models.user import User, BuildingConfig


def seed():
    app = create_app()
    with app.app_context():
        # Admin user
        email = os.environ.get("SEED_ADMIN_EMAIL", "admin@aptms.local")
        password = os.environ.get("SEED_ADMIN_PASSWORD", "changeme123")

        if User.query.filter_by(email=email).first():
            print(f"Admin {email} already exists, skipping.")
        else:
            admin = User(
                email=email,
                full_name="Admin",
                role="admin",
                is_active=True,
            )
            admin.set_password(password)
            db.session.add(admin)
            print(f"Created admin: {email} / {password}")

        # Building config
        if not BuildingConfig.query.first():
            config = BuildingConfig(
                name=os.environ.get("BUILDING_NAME", "My Apartment Complex"),
                latitude=float(os.environ.get("BUILDING_LATITUDE", 0)),
                longitude=float(os.environ.get("BUILDING_LONGITUDE", 0)),
                geofence_radius_m=int(os.environ.get("GEOFENCE_RADIUS_M", 50)),
            )
            db.session.add(config)
            print("Created building config.")

        db.session.commit()
        print("Seed complete.")


if __name__ == "__main__":
    seed()
