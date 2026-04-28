from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    # SQLite for local dev, PostgreSQL for VPS (Render provides postgres:// prefix)
    db_url = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(os.path.dirname(os.path.dirname(__file__)), "aptms.db"),
    ).replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["BUILDING_LATITUDE"] = float(os.environ.get("BUILDING_LATITUDE", 0))
    app.config["BUILDING_LONGITUDE"] = float(os.environ.get("BUILDING_LONGITUDE", 0))
    app.config["GEOFENCE_RADIUS_M"] = int(os.environ.get("GEOFENCE_RADIUS_M", 50))

    db.init_app(app)
    migrate.init_app(app, db)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    # Import models so Flask-Migrate can detect them
    from app.models import user, audit, checkin, attendance, leave, task  # noqa: F401

    from app.routes.auth import auth_bp
    from app.routes.users import users_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.checkin import checkin_bp
    from app.routes.attendance import attendance_bp
    from app.routes.leave import leave_bp
    from app.routes.tasks import tasks_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(checkin_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(leave_bp)
    app.register_blueprint(tasks_bp)

    app.jinja_env.globals["enumerate"] = enumerate
    app.jinja_env.globals["min"] = min

    @app.errorhandler(403)
    def forbidden(e):
        from flask import render_template
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template("errors/404.html"), 404

    return app
