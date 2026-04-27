from flask import Blueprint, render_template
from flask_login import login_required
from datetime import datetime, timezone

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    now = datetime.now(timezone.utc)
    hour = now.hour
    if hour < 12:
        greeting = "morning"
    elif hour < 17:
        greeting = "afternoon"
    else:
        greeting = "evening"
    return render_template(
        "dashboard/index.html",
        greeting=greeting,
        today=now.strftime("%A, %d %B %Y"),
    )
