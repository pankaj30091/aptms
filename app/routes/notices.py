from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timezone
from app import db
from app.models.notice import Notice
from app.services.audit import log_audit
from app.utils.decorators import manager_or_admin_required

notices_bp = Blueprint("notices", __name__, url_prefix="/notices")

CATEGORIES = [
    ("general", "General"),
    ("maintenance", "Maintenance"),
    ("event", "Event"),
    ("urgent", "Urgent"),
]


@notices_bp.route("/")
@login_required
def index():
    notices = (
        Notice.query
        .filter(Notice.deleted_at.is_(None))
        .order_by(Notice.pinned.desc(), Notice.created_at.desc())
        .all()
    )
    return render_template("notices/index.html", notices=notices, categories=CATEGORIES)


@notices_bp.route("/new", methods=["GET", "POST"])
@login_required
@manager_or_admin_required
def new_notice():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        if not title or not body:
            flash("Title and body are required.", "danger")
            return render_template("notices/form.html", notice=None, categories=CATEGORIES)

        expires_raw = request.form.get("expires_at", "").strip()
        expires_at = None
        if expires_raw:
            try:
                expires_at = datetime.strptime(expires_raw, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                pass

        notice = Notice(
            title=title,
            body=body,
            category=request.form.get("category") or None,
            pinned=bool(request.form.get("pinned")),
            posted_by=current_user.id,
            expires_at=expires_at,
        )
        db.session.add(notice)
        db.session.flush()
        log_audit("CREATE", "notices", notice.id, new_values=notice.to_dict())
        db.session.commit()
        flash("Notice posted.", "success")
        return redirect(url_for("notices.index"))

    return render_template("notices/form.html", notice=None, categories=CATEGORIES)


@notices_bp.route("/<int:notice_id>/edit", methods=["GET", "POST"])
@login_required
@manager_or_admin_required
def edit_notice(notice_id):
    notice = Notice.query.get_or_404(notice_id)
    if request.method == "POST":
        old = notice.to_dict()
        notice.title = request.form.get("title", notice.title).strip()
        notice.body = request.form.get("body", notice.body).strip()
        notice.category = request.form.get("category") or None
        notice.pinned = bool(request.form.get("pinned"))

        expires_raw = request.form.get("expires_at", "").strip()
        if expires_raw:
            try:
                notice.expires_at = datetime.strptime(expires_raw, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                pass
        else:
            notice.expires_at = None

        db.session.flush()
        log_audit("UPDATE", "notices", notice.id, old_values=old, new_values=notice.to_dict())
        db.session.commit()
        flash("Notice updated.", "success")
        return redirect(url_for("notices.index"))

    return render_template("notices/form.html", notice=notice, categories=CATEGORIES)


@notices_bp.route("/<int:notice_id>/delete", methods=["POST"])
@login_required
@manager_or_admin_required
def delete_notice(notice_id):
    notice = Notice.query.get_or_404(notice_id)
    notice.deleted_at = datetime.now(timezone.utc)
    log_audit("DELETE", "notices", notice.id)
    db.session.commit()
    flash("Notice removed.", "success")
    return redirect(url_for("notices.index"))
