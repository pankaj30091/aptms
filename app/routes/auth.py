from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User
from app.services.audit import log_audit

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter_by(email=email, deleted_at=None).first()
        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html")

        if not user.is_active:
            flash("Your account has been disabled. Contact admin.", "danger")
            return render_template("auth/login.html")

        login_user(user, remember=remember)
        next_page = request.args.get("next")
        return redirect(next_page or url_for("dashboard.index"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_pw = request.form.get("current_password", "")
        new_pw = request.form.get("new_password", "")
        confirm_pw = request.form.get("confirm_password", "")

        if not current_user.check_password(current_pw):
            flash("Current password is incorrect.", "danger")
            return render_template("auth/change_password.html")

        if len(new_pw) < 8:
            flash("New password must be at least 8 characters.", "danger")
            return render_template("auth/change_password.html")

        if new_pw != confirm_pw:
            flash("Passwords do not match.", "danger")
            return render_template("auth/change_password.html")

        current_user.set_password(new_pw)
        db.session.commit()
        log_audit(
            action="UPDATE",
            table_name="users",
            record_id=current_user.id,
            new_values={"password": "changed"},
        )
        flash("Password updated successfully.", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("auth/change_password.html")
