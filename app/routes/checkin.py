from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timezone, date
from app import db
from app.models.checkin import ManagerCheckin
from app.models.user import User
from app.services.geofence import is_within_geofence
from app.services.audit import log_audit
from app.utils.decorators import manager_or_admin_required

checkin_bp = Blueprint("checkin", __name__, url_prefix="/checkin")


@checkin_bp.route("/")
@login_required
@manager_or_admin_required
def index():
    today = date.today()
    # Today's events for current user
    todays_events = (
        ManagerCheckin.query
        .filter(
            ManagerCheckin.user_id == current_user.id,
            db.func.date(ManagerCheckin.recorded_at) == today,
        )
        .order_by(ManagerCheckin.recorded_at.desc())
        .all()
    )

    # Determine current status: last event type
    last_event = todays_events[0] if todays_events else None
    is_checked_in = last_event and last_event.event_type == "check_in"

    # Admin sees all managers' status today
    all_today = None
    if current_user.is_admin:
        managers = User.query.filter_by(role="manager", deleted_at=None, is_active=True).all()
        all_today = []
        for m in managers:
            last = (
                ManagerCheckin.query
                .filter(
                    ManagerCheckin.user_id == m.id,
                    db.func.date(ManagerCheckin.recorded_at) == today,
                )
                .order_by(ManagerCheckin.recorded_at.desc())
                .first()
            )
            all_today.append({
                "user": m,
                "last_event": last,
                "status": last.event_type if last else "not_checked_in",
            })

    return render_template(
        "checkin/index.html",
        todays_events=todays_events,
        is_checked_in=is_checked_in,
        all_today=all_today,
        today=today,
    )


@checkin_bp.route("/record", methods=["POST"])
@login_required
@manager_or_admin_required
def record():
    """Receives GPS coords from browser, validates geofence, records event."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400

    try:
        lat = float(data["latitude"])
        lon = float(data["longitude"])
        event_type = data.get("event_type")  # check_in or check_out
    except (KeyError, ValueError):
        return jsonify({"error": "Invalid data"}), 400

    if event_type not in ("check_in", "check_out"):
        return jsonify({"error": "Invalid event type"}), 400

    allowed, distance_m = is_within_geofence(lat, lon)
    if not allowed:
        return jsonify({
            "success": False,
            "error": f"You are {distance_m}m away from the building. Must be within 50m.",
            "distance_m": distance_m,
        }), 403

    event = ManagerCheckin(
        user_id=current_user.id,
        event_type=event_type,
        latitude=lat,
        longitude=lon,
        distance_m=distance_m,
        notes=data.get("notes"),
    )
    db.session.add(event)
    db.session.flush()
    log_audit("CREATE", "manager_checkins", event.id, new_values=event.to_dict())
    db.session.commit()

    return jsonify({
        "success": True,
        "event_type": event_type,
        "distance_m": distance_m,
        "recorded_at": event.recorded_at.strftime("%H:%M"),
    })


@checkin_bp.route("/history")
@login_required
@manager_or_admin_required
def history():
    from_date = request.args.get("from_date", date.today().replace(day=1).isoformat())
    to_date = request.args.get("to_date", date.today().isoformat())

    query = ManagerCheckin.query.filter(
        db.func.date(ManagerCheckin.recorded_at) >= from_date,
        db.func.date(ManagerCheckin.recorded_at) <= to_date,
    )
    if not current_user.is_admin:
        query = query.filter(ManagerCheckin.user_id == current_user.id)

    events = query.order_by(ManagerCheckin.recorded_at.desc()).all()
    return render_template("checkin/history.html", events=events, from_date=from_date, to_date=to_date)
