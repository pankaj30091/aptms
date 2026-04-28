from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.services.audit import log_audit

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_profile":
            full_name = request.form.get("full_name", "").strip()
            phone = request.form.get("phone", "").strip()
            if not full_name:
                flash("Name is required.", "danger")
                return redirect(url_for("profile.index"))
            old = {"full_name": current_user.full_name, "phone": current_user.phone}
            current_user.full_name = full_name
            current_user.phone = phone or None
            log_audit("UPDATE", "users", current_user.id, old_values=old,
                      new_values={"full_name": full_name, "phone": phone})
            db.session.commit()
            flash("Profile updated.", "success")

        elif action == "change_password":
            current_pw = request.form.get("current_password", "")
            new_pw = request.form.get("new_password", "")
            confirm_pw = request.form.get("confirm_password", "")
            if not current_user.check_password(current_pw):
                flash("Current password is incorrect.", "danger")
            elif len(new_pw) < 8:
                flash("New password must be at least 8 characters.", "danger")
            elif new_pw != confirm_pw:
                flash("Passwords do not match.", "danger")
            else:
                current_user.set_password(new_pw)
                log_audit("UPDATE", "users", current_user.id,
                          new_values={"password": "changed"})
                db.session.commit()
                flash("Password changed successfully.", "success")

        return redirect(url_for("profile.index"))

    return render_template("profile/index.html")
