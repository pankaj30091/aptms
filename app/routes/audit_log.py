from flask import Blueprint, render_template, request
from flask_login import login_required
from app.models.audit import AuditLog
from app.utils.decorators import admin_required

audit_log_bp = Blueprint("audit_log", __name__, url_prefix="/audit")

TABLE_LABELS = {
    "users": "Users",
    "manager_checkins": "Check-ins",
    "staff_attendance": "Attendance",
    "leave_requests": "Leave",
    "task_definitions": "Tasks",
    "task_completions": "Task Completions",
    "documents": "Documents",
    "action_items": "Action Items",
    "service_requests": "Service Requests",
    "notices": "Notices",
}


@audit_log_bp.route("/")
@login_required
@admin_required
def index():
    page = request.args.get("page", 1, type=int)
    table_filter = request.args.get("table", "")
    action_filter = request.args.get("action", "")

    query = AuditLog.query
    if table_filter:
        query = query.filter_by(table_name=table_filter)
    if action_filter:
        query = query.filter_by(action=action_filter)

    logs = query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=50, error_out=False)
    tables = sorted(TABLE_LABELS.keys())
    return render_template("audit/index.html", logs=logs, tables=tables,
                           table_labels=TABLE_LABELS, table_filter=table_filter,
                           action_filter=action_filter)
