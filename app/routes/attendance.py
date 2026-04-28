from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import date, datetime, timezone
from app import db
from app.models.attendance import Staff, StaffAttendance
from app.services.audit import log_audit
from app.utils.decorators import manager_or_admin_required, admin_required

attendance_bp = Blueprint("attendance", __name__, url_prefix="/attendance")

ROLES = [
    ("security_guard", "Security Guard"),
    ("floor_cleaner", "Floor Cleaner"),
    ("other", "Other"),
]


@attendance_bp.route("/")
@login_required
@manager_or_admin_required
def index():
    selected_date = request.args.get("date", date.today().isoformat())
    try:
        selected = date.fromisoformat(selected_date)
    except ValueError:
        selected = date.today()

    staff_list = Staff.query.filter_by(deleted_at=None, is_active=True).order_by(Staff.role, Staff.full_name).all()

    # Build a lookup: staff_id -> attendance record for selected date
    records = StaffAttendance.query.filter_by(attendance_date=selected).all()
    attendance_map = {r.staff_id: r for r in records}

    return render_template(
        "attendance/index.html",
        staff_list=staff_list,
        attendance_map=attendance_map,
        selected_date=selected,
        roles=ROLES,
    )


@attendance_bp.route("/save", methods=["POST"])
@login_required
@manager_or_admin_required
def save():
    """Bulk save attendance for a given date."""
    attendance_date_str = request.form.get("attendance_date")
    try:
        attendance_date = date.fromisoformat(attendance_date_str)
    except (ValueError, TypeError):
        flash("Invalid date.", "danger")
        return redirect(url_for("attendance.index"))

    staff_list = Staff.query.filter_by(deleted_at=None, is_active=True).all()

    for staff in staff_list:
        status = request.form.get(f"status_{staff.id}")
        notes = request.form.get(f"notes_{staff.id}", "").strip() or None
        if not status:
            continue

        existing = StaffAttendance.query.filter_by(
            staff_id=staff.id, attendance_date=attendance_date
        ).first()

        if existing:
            old = {"status": existing.status, "notes": existing.notes}
            existing.status = status
            existing.notes = notes
            existing.marked_by = current_user.id
            db.session.flush()
            log_audit("UPDATE", "staff_attendance", existing.id,
                      old_values=old, new_values={"status": status, "notes": notes})
        else:
            record = StaffAttendance(
                staff_id=staff.id,
                marked_by=current_user.id,
                attendance_date=attendance_date,
                status=status,
                notes=notes,
            )
            db.session.add(record)
            db.session.flush()
            log_audit("CREATE", "staff_attendance", record.id,
                      new_values={"staff_id": staff.id, "status": status, "date": str(attendance_date)})

    db.session.commit()
    flash(f"Attendance saved for {attendance_date.strftime('%d %b %Y')}.", "success")
    return redirect(url_for("attendance.index", date=attendance_date_str))


# --- Staff CRUD (admin only) ---

@attendance_bp.route("/staff")
@login_required
@admin_required
def staff_list():
    staff = Staff.query.filter_by(deleted_at=None).order_by(Staff.role, Staff.full_name).all()
    return render_template("attendance/staff_list.html", staff=staff, roles=ROLES)


@attendance_bp.route("/staff/new", methods=["GET", "POST"])
@login_required
@admin_required
def staff_new():
    if request.method == "POST":
        name = request.form.get("full_name", "").strip()
        role = request.form.get("role", "")
        phone = request.form.get("phone", "").strip() or None

        if not name or role not in [r[0] for r in ROLES]:
            flash("Name and valid role are required.", "danger")
            return render_template("attendance/staff_form.html", staff=None, roles=ROLES)

        s = Staff(full_name=name, role=role, phone=phone)
        db.session.add(s)
        db.session.flush()
        log_audit("CREATE", "staff", s.id, new_values=s.to_dict())
        db.session.commit()
        flash(f"{name} added.", "success")
        return redirect(url_for("attendance.staff_list"))

    return render_template("attendance/staff_form.html", staff=None, roles=ROLES)


@attendance_bp.route("/staff/<int:staff_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def staff_edit(staff_id):
    s = Staff.query.filter_by(id=staff_id, deleted_at=None).first_or_404()

    if request.method == "POST":
        old = s.to_dict()
        s.full_name = request.form.get("full_name", s.full_name).strip()
        role = request.form.get("role", s.role)
        if role in [r[0] for r in ROLES]:
            s.role = role
        s.phone = request.form.get("phone", "").strip() or None
        s.is_active = "is_active" in request.form
        db.session.flush()
        log_audit("UPDATE", "staff", s.id, old_values=old, new_values=s.to_dict())
        db.session.commit()
        flash("Staff updated.", "success")
        return redirect(url_for("attendance.staff_list"))

    return render_template("attendance/staff_form.html", staff=s, roles=ROLES)


@attendance_bp.route("/staff/<int:staff_id>/delete", methods=["POST"])
@login_required
@admin_required
def staff_delete(staff_id):
    s = Staff.query.filter_by(id=staff_id, deleted_at=None).first_or_404()
    old = s.to_dict()
    s.deleted_at = datetime.now(timezone.utc)
    s.is_active = False
    log_audit("DELETE", "staff", s.id, old_values=old)
    db.session.commit()
    flash(f"{s.full_name} removed.", "success")
    return redirect(url_for("attendance.staff_list"))
