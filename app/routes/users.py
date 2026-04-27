from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.services.audit import log_audit
from app.utils.decorators import admin_required
from datetime import datetime, timezone

users_bp = Blueprint("users", __name__, url_prefix="/admin/users")


@users_bp.route("/")
@login_required
@admin_required
def list_users():
    users = User.query.filter_by(deleted_at=None).order_by(User.full_name).all()
    return render_template("users/list.html", users=users)


@users_bp.route("/new", methods=["GET", "POST"])
@login_required
@admin_required
def create_user():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        full_name = request.form.get("full_name", "").strip()
        role = request.form.get("role", "")
        phone = request.form.get("phone", "").strip()
        flat_number = request.form.get("flat_number", "").strip()
        password = request.form.get("password", "")

        if not all([email, full_name, role, password]):
            flash("Email, name, role, and password are required.", "danger")
            return render_template("users/form.html", user=None)

        if role not in ("admin", "manager", "resident"):
            flash("Invalid role.", "danger")
            return render_template("users/form.html", user=None)

        if User.query.filter_by(email=email).first():
            flash("Email already in use.", "danger")
            return render_template("users/form.html", user=None)

        user = User(
            email=email,
            full_name=full_name,
            role=role,
            phone=phone or None,
            flat_number=flat_number or None,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        log_audit("CREATE", "users", user.id, new_values=user.to_dict())
        db.session.commit()
        flash(f"User {full_name} created.", "success")
        return redirect(url_for("users.list_users"))

    return render_template("users/form.html", user=None)


@users_bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.filter_by(id=user_id, deleted_at=None).first_or_404()

    if request.method == "POST":
        old = user.to_dict()
        user.full_name = request.form.get("full_name", user.full_name).strip()
        user.phone = request.form.get("phone", "").strip() or None
        user.flat_number = request.form.get("flat_number", "").strip() or None
        role = request.form.get("role", user.role)
        if role in ("admin", "manager", "resident"):
            user.role = role
        user.is_active = "is_active" in request.form

        new_pw = request.form.get("new_password", "")
        if new_pw:
            if len(new_pw) < 8:
                flash("Password must be at least 8 characters.", "danger")
                return render_template("users/form.html", user=user)
            user.set_password(new_pw)

        db.session.flush()
        log_audit("UPDATE", "users", user.id, old_values=old, new_values=user.to_dict())
        db.session.commit()
        flash("User updated.", "success")
        return redirect(url_for("users.list_users"))

    return render_template("users/form.html", user=user)


@users_bp.route("/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.filter_by(id=user_id, deleted_at=None).first_or_404()
    if user.id == current_user.id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("users.list_users"))
    old = user.to_dict()
    user.deleted_at = datetime.now(timezone.utc)
    user.is_active = False
    log_audit("DELETE", "users", user.id, old_values=old)
    db.session.commit()
    flash(f"User {user.full_name} deleted.", "success")
    return redirect(url_for("users.list_users"))
