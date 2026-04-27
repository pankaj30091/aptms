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

    app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
    # Render provides postgres:// but SQLAlchemy requires postgresql://
    db_url = os.environ["DATABASE_URL"].replace("postgres://", "postgresql://", 1)
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
    from app.models import user, audit  # noqa: F401

    from app.routes.auth import auth_bp
    from app.routes.users import users_bp
    from app.routes.dashboard import dashboard_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(dashboard_bp)

    @app.errorhandler(403)
    def forbidden(e):
        from flask import render_template
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template("errors/404.html"), 404

    return app
