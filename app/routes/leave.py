from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import date, datetime, timezone
from app import db
from app.models.leave import LeaveRequest
from app.models.user import User
from app.services.leave import fiscal_year_for, get_balance, count_leave_days, get_or_create_quota
from app.services.audit import log_audit
from app.utils.decorators import admin_required, manager_or_admin_required

leave_bp = Blueprint("leave", __name__, url_prefix="/leave")

LEAVE_TYPES = [("casual", "Casual"), ("sick", "Sick"), ("earned", "Earned")]


@leave_bp.route("/")
@login_required
@manager_or_admin_required
def index():
    fy = fiscal_year_for(date.today())
    balance = get_balance(current_user.id, fy)
    db.session.commit()  # flush quota creation if new

    requests = (
        LeaveRequest.query
        .filter_by(user_id=current_user.id)
        .order_by(LeaveRequest.created_at.desc())
        .limit(20).all()
    )
    return render_template("leave/index.html", balance=balance, requests=requests, leave_types=LEAVE_TYPES)


@leave_bp.route("/apply", methods=["GET", "POST"])
@login_required
@manager_or_admin_required
def apply():
    if request.method == "POST":
        leave_type = request.form.get("leave_type")
        start_str = request.form.get("start_date")
        end_str = request.form.get("end_date")
        reason = request.form.get("reason", "").strip()

        if leave_type not in [t[0] for t in LEAVE_TYPES]:
            flash("Invalid leave type.", "danger")
            return render_template("leave/apply.html", leave_types=LEAVE_TYPES)

        try:
            start = date.fromisoformat(start_str)
            end = date.fromisoformat(end_str)
        except (ValueError, TypeError):
            flash("Invalid dates.", "danger")
            return render_template("leave/apply.html", leave_types=LEAVE_TYPES)

        if end < start:
            flash("End date must be on or after start date.", "danger")
            return render_template("leave/apply.html", leave_types=LEAVE_TYPES)

        fy = fiscal_year_for(start)
        total_days = count_leave_days(start, end)
        balance = get_balance(current_user.id, fy)

        if total_days > balance[leave_type]["remaining"]:
            flash(f"Insufficient {leave_type} leave balance. Remaining: {balance[leave_type]['remaining']} days.", "danger")
            return render_template("leave/apply.html", leave_types=LEAVE_TYPES)

        lr = LeaveRequest(
            user_id=current_user.id,
            leave_type=leave_type,
            start_date=start,
            end_date=end,
            total_days=total_days,
            reason=reason,
            fiscal_year=fy,
        )
        db.session.add(lr)
        db.session.flush()
        log_audit("CREATE", "leave_requests", lr.id, new_values=lr.to_dict())
        db.session.commit()
        flash(f"Leave application submitted for {total_days:.0f} day(s).", "success")
        return redirect(url_for("leave.index"))

    return render_template("leave/apply.html", leave_types=LEAVE_TYPES)


@leave_bp.route("/<int:leave_id>/cancel", methods=["POST"])
@login_required
def cancel(leave_id):
    lr = LeaveRequest.query.filter_by(id=leave_id, user_id=current_user.id, status="pending").first_or_404()
    old = lr.to_dict()
    lr.status = "cancelled"
    log_audit("UPDATE", "leave_requests", lr.id, old_values=old, new_values={"status": "cancelled"})
    db.session.commit()
    flash("Leave request cancelled.", "info")
    return redirect(url_for("leave.index"))


# --- Admin views ---

@leave_bp.route("/admin")
@login_required
@admin_required
def admin_list():
    status_filter = request.args.get("status", "pending")
    query = LeaveRequest.query.order_by(LeaveRequest.created_at.desc())
    if status_filter != "all":
        query = query.filter_by(status=status_filter)
    requests = query.limit(50).all()
    return render_template("leave/admin_list.html", requests=requests, status_filter=status_filter)


@leave_bp.route("/<int:leave_id>/approve", methods=["POST"])
@login_required
@admin_required
def approve(leave_id):
    lr = LeaveRequest.query.filter_by(id=leave_id, status="pending").first_or_404()
    old = lr.to_dict()
    lr.status = "approved"
    lr.reviewed_by = current_user.id
    lr.reviewed_at = datetime.now(timezone.utc)
    lr.review_note = request.form.get("review_note", "").strip() or None
    log_audit("UPDATE", "leave_requests", lr.id, old_values=old, new_values={"status": "approved"})
    db.session.commit()
    flash(f"Leave approved for {lr.user.full_name}.", "success")
    return redirect(url_for("leave.admin_list"))


@leave_bp.route("/<int:leave_id>/reject", methods=["POST"])
@login_required
@admin_required
def reject(leave_id):
    lr = LeaveRequest.query.filter_by(id=leave_id, status="pending").first_or_404()
    old = lr.to_dict()
    lr.status = "rejected"
    lr.reviewed_by = current_user.id
    lr.reviewed_at = datetime.now(timezone.utc)
    lr.review_note = request.form.get("review_note", "").strip() or None
    log_audit("UPDATE", "leave_requests", lr.id, old_values=old, new_values={"status": "rejected"})
    db.session.commit()
    flash(f"Leave rejected for {lr.user.full_name}.", "info")
    return redirect(url_for("leave.admin_list"))


@leave_bp.route("/admin/quota/<int:user_id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_quota(user_id):
    user = User.query.filter_by(id=user_id, deleted_at=None).first_or_404()
    fy = int(request.args.get("fy", fiscal_year_for(date.today())))
    quota = get_or_create_quota(user_id, fy)
    db.session.commit()

    if request.method == "POST":
        quota.casual_total = int(request.form.get("casual_total", quota.casual_total))
        quota.sick_total = int(request.form.get("sick_total", quota.sick_total))
        quota.earned_total = int(request.form.get("earned_total", quota.earned_total))
        log_audit("UPDATE", "leave_quotas", quota.id, new_values={
            "casual": quota.casual_total, "sick": quota.sick_total, "earned": quota.earned_total
        })
        db.session.commit()
        flash("Quota updated.", "success")
        return redirect(url_for("leave.admin_list"))

    return render_template("leave/edit_quota.html", user=user, quota=quota, fy=fy)
