from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import date, datetime, timezone
from app import db
from app.models.document import ActionItem
from app.models.user import User
from app.services.audit import log_audit
from app.utils.decorators import manager_or_admin_required

action_items_bp = Blueprint("action_items", __name__, url_prefix="/action-items")

PRIORITIES = [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")]
STATUSES = [("open", "Open"), ("in_progress", "In Progress"), ("blocked", "Blocked"), ("done", "Done"), ("cancelled", "Cancelled")]


@action_items_bp.route("/")
@login_required
@manager_or_admin_required
def index():
    status_filter = request.args.get("status", "open")
    priority_filter = request.args.get("priority", "")

    query = ActionItem.query
    if status_filter != "all":
        query = query.filter_by(status=status_filter)
    if priority_filter:
        query = query.filter_by(priority=priority_filter)

    items = query.order_by(
        db.case({"critical": 0, "high": 1, "medium": 2, "low": 3}, value=ActionItem.priority),
        ActionItem.target_date.asc().nullslast(),
    ).all()

    managers = User.query.filter(User.role.in_(["admin", "manager"]), User.deleted_at.is_(None)).all()
    return render_template("action_items/index.html", items=items, priorities=PRIORITIES,
                           statuses=STATUSES, status_filter=status_filter,
                           priority_filter=priority_filter, managers=managers)


@action_items_bp.route("/new", methods=["GET", "POST"])
@login_required
@manager_or_admin_required
def new_item():
    managers = User.query.filter(User.role.in_(["admin", "manager"]), User.deleted_at.is_(None)).all()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Title is required.", "danger")
            return render_template("action_items/form.html", item=None, priorities=PRIORITIES, managers=managers)

        budget = None
        target_date = None
        try:
            if request.form.get("budget_inr"):
                budget = float(request.form["budget_inr"])
            if request.form.get("target_date"):
                target_date = date.fromisoformat(request.form["target_date"])
        except ValueError:
            flash("Invalid budget or date.", "danger")
            return render_template("action_items/form.html", item=None, priorities=PRIORITIES, managers=managers)

        item = ActionItem(
            title=title,
            description=request.form.get("description", "").strip() or None,
            priority=request.form.get("priority", "medium"),
            owner_id=request.form.get("owner_id", type=int) or None,
            budget_inr=budget,
            target_date=target_date,
            created_by=current_user.id,
        )
        db.session.add(item)
        db.session.flush()
        log_audit("CREATE", "action_items", item.id, new_values=item.to_dict())
        db.session.commit()
        flash(f"Action item '{title}' created.", "success")
        return redirect(url_for("action_items.index"))

    return render_template("action_items/form.html", item=None, priorities=PRIORITIES, managers=managers)


@action_items_bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
@manager_or_admin_required
def edit_item(item_id):
    item = ActionItem.query.get_or_404(item_id)
    managers = User.query.filter(User.role.in_(["admin", "manager"]), User.deleted_at.is_(None)).all()

    if request.method == "POST":
        old = item.to_dict()
        item.title = request.form.get("title", item.title).strip()
        item.description = request.form.get("description", "").strip() or None
        item.priority = request.form.get("priority", item.priority)
        item.status = request.form.get("status", item.status)
        item.owner_id = request.form.get("owner_id", type=int) or None
        try:
            item.budget_inr = float(request.form["budget_inr"]) if request.form.get("budget_inr") else None
            item.target_date = date.fromisoformat(request.form["target_date"]) if request.form.get("target_date") else None
        except ValueError:
            flash("Invalid budget or date.", "danger")
            return render_template("action_items/form.html", item=item, priorities=PRIORITIES, managers=managers)

        if item.status in ("done", "cancelled") and not item.closed_at:
            item.closed_at = datetime.now(timezone.utc)

        db.session.flush()
        log_audit("UPDATE", "action_items", item.id, old_values=old, new_values=item.to_dict())
        db.session.commit()
        flash("Action item updated.", "success")
        return redirect(url_for("action_items.index"))

    return render_template("action_items/form.html", item=item, priorities=PRIORITIES, managers=managers)
