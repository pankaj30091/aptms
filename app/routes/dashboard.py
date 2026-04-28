from flask import Blueprint, render_template
from flask_login import login_required, current_user
from datetime import datetime, timezone, date
from app import db
from app.models.checkin import ManagerCheckin
from app.models.leave import LeaveRequest
from app.services.leave import fiscal_year_for
from app.services.task import completion_rate

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    now = datetime.now(timezone.utc)
    today = date.today()
    hour = now.hour
    greeting = "morning" if hour < 12 else ("afternoon" if hour < 17 else "evening")

    # Check-in status for current user
    last_checkin = (
        ManagerCheckin.query
        .filter(
            ManagerCheckin.user_id == current_user.id,
            db.func.date(ManagerCheckin.recorded_at) == today,
        )
        .order_by(ManagerCheckin.recorded_at.desc())
        .first()
    )
    checkin_status = None
    if last_checkin:
        checkin_status = "in" if last_checkin.event_type == "check_in" else "out"

    # Pending leaves (admin sees all, manager sees own)
    leave_query = LeaveRequest.query.filter_by(status="pending")
    if not current_user.is_admin:
        leave_query = leave_query.filter_by(user_id=current_user.id)
    pending_leaves = leave_query.count()

    # Task completion today
    rate = completion_rate(today)

    return render_template(
        "dashboard/index.html",
        greeting=greeting,
        today=now.strftime("%A, %d %B %Y"),
        checkin_status=checkin_status,
        pending_leaves=pending_leaves,
        task_rate=rate,
    )
