from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timezone
from app import db
from app.models.service_request import ServiceRequest, ServiceRequestUpdate
from app.models.user import User
from app.services.audit import log_audit
from app.utils.decorators import manager_or_admin_required

service_requests_bp = Blueprint("service_requests", __name__, url_prefix="/service-requests")

CATEGORIES = [
    ("plumbing", "Plumbing"),
    ("electrical", "Electrical"),
    ("housekeeping", "Housekeeping"),
    ("lift", "Lift"),
    ("security", "Security"),
    ("intercom", "Intercom"),
    ("other", "Other"),
]
PRIORITIES = [("low", "Low"), ("normal", "Normal"), ("high", "High"), ("urgent", "Urgent")]
STATUSES = [("open", "Open"), ("in_progress", "In Progress"), ("resolved", "Resolved"), ("closed", "Closed"), ("cancelled", "Cancelled")]


@service_requests_bp.route("/")
@login_required
@manager_or_admin_required
def index():
    status_filter = request.args.get("status", "open")
    category_filter = request.args.get("category", "")

    query = ServiceRequest.query
    if status_filter != "all":
        query = query.filter_by(status=status_filter)
    if category_filter:
        query = query.filter_by(category=category_filter)

    requests_list = query.order_by(
        db.case({"urgent": 0, "high": 1, "normal": 2, "low": 3}, value=ServiceRequest.priority),
        ServiceRequest.created_at.desc(),
    ).all()

    return render_template("service_requests/index.html", requests=requests_list,
                           categories=CATEGORIES, priorities=PRIORITIES, statuses=STATUSES,
                           status_filter=status_filter, category_filter=category_filter)


@service_requests_bp.route("/new", methods=["GET", "POST"])
@login_required
@manager_or_admin_required
def new_request():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Title is required.", "danger")
            return render_template("service_requests/form.html", sr=None,
                                   categories=CATEGORIES, priorities=PRIORITIES)

        sr = ServiceRequest(
            title=title,
            description=request.form.get("description", "").strip() or None,
            flat_number=request.form.get("flat_number", "").strip() or None,
            resident_name=request.form.get("resident_name", "").strip() or None,
            resident_phone=request.form.get("resident_phone", "").strip() or None,
            category=request.form.get("category") or None,
            priority=request.form.get("priority", "normal"),
            logged_by=current_user.id,
        )
        db.session.add(sr)
        db.session.flush()
        log_audit("CREATE", "service_requests", sr.id, new_values=sr.to_dict())
        db.session.commit()
        flash("Service request logged.", "success")
        return redirect(url_for("service_requests.index"))

    return render_template("service_requests/form.html", sr=None,
                           categories=CATEGORIES, priorities=PRIORITIES)


@service_requests_bp.route("/<int:sr_id>")
@login_required
@manager_or_admin_required
def detail(sr_id):
    sr = ServiceRequest.query.get_or_404(sr_id)
    managers = User.query.filter(User.role.in_(["admin", "manager"]), User.deleted_at.is_(None)).all()
    return render_template("service_requests/detail.html", sr=sr,
                           statuses=STATUSES, managers=managers)


@service_requests_bp.route("/<int:sr_id>/update", methods=["POST"])
@login_required
@manager_or_admin_required
def add_update(sr_id):
    sr = ServiceRequest.query.get_or_404(sr_id)
    old_status = sr.status
    new_status = request.form.get("new_status", sr.status)
    note = request.form.get("note", "").strip() or None
    assigned_to = request.form.get("assigned_to", type=int) or None

    sr.status = new_status
    sr.assigned_to = assigned_to

    if new_status == "resolved" and not sr.resolved_at:
        sr.resolved_at = datetime.now(timezone.utc)
        sr.resolution_note = note

    update = ServiceRequestUpdate(
        request_id=sr.id,
        updated_by=current_user.id,
        old_status=old_status,
        new_status=new_status,
        note=note,
    )
    db.session.add(update)
    db.session.flush()
    log_audit("UPDATE", "service_requests", sr.id,
              old_values={"status": old_status},
              new_values={"status": new_status, "note": note})
    db.session.commit()
    flash("Request updated.", "success")
    return redirect(url_for("service_requests.detail", sr_id=sr_id))


@service_requests_bp.route("/<int:sr_id>/edit", methods=["GET", "POST"])
@login_required
@manager_or_admin_required
def edit_request(sr_id):
    sr = ServiceRequest.query.get_or_404(sr_id)
    if request.method == "POST":
        old = sr.to_dict()
        sr.title = request.form.get("title", sr.title).strip()
        sr.description = request.form.get("description", "").strip() or None
        sr.flat_number = request.form.get("flat_number", "").strip() or None
        sr.resident_name = request.form.get("resident_name", "").strip() or None
        sr.resident_phone = request.form.get("resident_phone", "").strip() or None
        sr.category = request.form.get("category") or None
        sr.priority = request.form.get("priority", sr.priority)
        db.session.flush()
        log_audit("UPDATE", "service_requests", sr.id, old_values=old, new_values=sr.to_dict())
        db.session.commit()
        flash("Request updated.", "success")
        return redirect(url_for("service_requests.detail", sr_id=sr_id))

    return render_template("service_requests/form.html", sr=sr,
                           categories=CATEGORIES, priorities=PRIORITIES)
