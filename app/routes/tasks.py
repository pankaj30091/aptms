from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import date, datetime, timezone
from app import db
from app.models.task import TaskDefinition, TaskCompletion
from app.services.task import get_due_tasks, completion_rate
from app.services.audit import log_audit
from app.utils.decorators import admin_required, manager_or_admin_required

tasks_bp = Blueprint("tasks", __name__, url_prefix="/tasks")

FREQUENCIES = [("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly"), ("one_off", "One-off")]
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@tasks_bp.route("/")
@login_required
@manager_or_admin_required
def index():
    selected_date_str = request.args.get("date", date.today().isoformat())
    try:
        selected = date.fromisoformat(selected_date_str)
    except ValueError:
        selected = date.today()

    tasks = get_due_tasks(selected)
    rate = completion_rate(selected)
    return render_template("tasks/index.html", tasks=tasks, selected=selected, rate=rate)


@tasks_bp.route("/complete", methods=["POST"])
@login_required
@manager_or_admin_required
def complete():
    task_def_id = request.form.get("task_def_id", type=int)
    due_date_str = request.form.get("due_date")
    notes = request.form.get("notes", "").strip() or None

    try:
        due_date = date.fromisoformat(due_date_str)
    except (ValueError, TypeError):
        flash("Invalid date.", "danger")
        return redirect(url_for("tasks.index"))

    existing = TaskCompletion.query.filter_by(task_def_id=task_def_id, due_date=due_date).first()
    if existing:
        flash("Task already marked complete.", "info")
        return redirect(url_for("tasks.index", date=due_date_str))

    c = TaskCompletion(
        task_def_id=task_def_id,
        completed_by=current_user.id,
        due_date=due_date,
        notes=notes,
    )
    db.session.add(c)
    db.session.flush()
    log_audit("CREATE", "task_completions", c.id, new_values={
        "task_def_id": task_def_id, "due_date": due_date_str, "notes": notes
    })
    db.session.commit()
    flash("Task marked complete.", "success")
    return redirect(url_for("tasks.index", date=due_date_str))


# --- Task definition management (admin) ---

@tasks_bp.route("/manage")
@login_required
@admin_required
def manage():
    defs = TaskDefinition.query.filter_by(deleted_at=None).order_by(TaskDefinition.frequency, TaskDefinition.title).all()
    return render_template("tasks/manage.html", defs=defs, days=DAYS_OF_WEEK)


@tasks_bp.route("/manage/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_task():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        frequency = request.form.get("frequency")
        description = request.form.get("description", "").strip() or None
        day_of_week = request.form.get("day_of_week", type=int)
        day_of_month = request.form.get("day_of_month", type=int)

        if not title or frequency not in [f[0] for f in FREQUENCIES]:
            flash("Title and frequency are required.", "danger")
            return render_template("tasks/form.html", task=None, frequencies=FREQUENCIES, days=DAYS_OF_WEEK)

        one_off_date = None
        if frequency == "one_off":
            try:
                one_off_date = date.fromisoformat(request.form.get("one_off_date", ""))
            except ValueError:
                flash("Please provide a valid due date for one-off tasks.", "danger")
                return render_template("tasks/form.html", task=None, frequencies=FREQUENCIES, days=DAYS_OF_WEEK)

        t = TaskDefinition(
            title=title,
            description=description,
            frequency=frequency,
            day_of_week=day_of_week if frequency == "weekly" else None,
            day_of_month=day_of_month if frequency == "monthly" else None,
            one_off_date=one_off_date,
            created_by=current_user.id,
        )
        db.session.add(t)
        db.session.flush()
        log_audit("CREATE", "task_definitions", t.id, new_values=t.to_dict())
        db.session.commit()
        flash(f"Task '{title}' created.", "success")
        return redirect(url_for("tasks.manage"))

    return render_template("tasks/form.html", task=None, frequencies=FREQUENCIES, days=DAYS_OF_WEEK)


@tasks_bp.route("/manage/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_task(task_id):
    t = TaskDefinition.query.filter_by(id=task_id, deleted_at=None).first_or_404()

    if request.method == "POST":
        old = t.to_dict()
        t.title = request.form.get("title", t.title).strip()
        t.description = request.form.get("description", "").strip() or None
        freq = request.form.get("frequency", t.frequency)
        if freq in [f[0] for f in FREQUENCIES]:
            t.frequency = freq
        t.day_of_week = request.form.get("day_of_week", type=int) if t.frequency == "weekly" else None
        t.day_of_month = request.form.get("day_of_month", type=int) if t.frequency == "monthly" else None
        if t.frequency == "one_off":
            try:
                t.one_off_date = date.fromisoformat(request.form.get("one_off_date", ""))
            except ValueError:
                t.one_off_date = None
        else:
            t.one_off_date = None
        t.is_active = "is_active" in request.form
        db.session.flush()
        log_audit("UPDATE", "task_definitions", t.id, old_values=old, new_values=t.to_dict())
        db.session.commit()
        flash("Task updated.", "success")
        return redirect(url_for("tasks.manage"))

    return render_template("tasks/form.html", task=t, frequencies=FREQUENCIES, days=DAYS_OF_WEEK)


@tasks_bp.route("/manage/<int:task_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_task(task_id):
    t = TaskDefinition.query.filter_by(id=task_id, deleted_at=None).first_or_404()
    old = t.to_dict()
    t.deleted_at = datetime.now(timezone.utc)
    t.is_active = False
    log_audit("DELETE", "task_definitions", t.id, old_values=old)
    db.session.commit()
    flash(f"Task '{t.title}' deleted.", "success")
    return redirect(url_for("tasks.manage"))
