from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import date, datetime, timezone, timedelta
from app import db
from app.models.document import Document
from app.services.audit import log_audit
from app.utils.decorators import admin_required, manager_or_admin_required

documents_bp = Blueprint("documents", __name__, url_prefix="/documents")

DOC_TYPES = [
    ("contract", "Contract"),
    ("amc", "AMC"),
    ("license", "License"),
    ("insurance", "Insurance"),
    ("agreement", "Agreement"),
    ("other", "Other"),
]

RENEWAL_WARN_DAYS = 30


def renewal_status(end_date):
    if not end_date:
        return None
    days_left = (end_date - date.today()).days
    if days_left < 0:
        return "expired"
    if days_left <= 7:
        return "critical"
    if days_left <= RENEWAL_WARN_DAYS:
        return "warning"
    return "ok"


@documents_bp.route("/")
@login_required
@manager_or_admin_required
def index():
    doc_type = request.args.get("type", "")
    query = Document.query.filter_by(deleted_at=None)
    if doc_type:
        query = query.filter_by(doc_type=doc_type)
    docs = query.order_by(Document.end_date.asc().nullslast()).all()
    return render_template("documents/index.html", docs=docs, doc_types=DOC_TYPES,
                           selected_type=doc_type, renewal_status=renewal_status)


@documents_bp.route("/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_document():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Title is required.", "danger")
            return render_template("documents/form.html", doc=None, doc_types=DOC_TYPES)

        end_date = None
        start_date = None
        try:
            if request.form.get("start_date"):
                start_date = date.fromisoformat(request.form["start_date"])
            if request.form.get("end_date"):
                end_date = date.fromisoformat(request.form["end_date"])
        except ValueError:
            flash("Invalid date format.", "danger")
            return render_template("documents/form.html", doc=None, doc_types=DOC_TYPES)

        doc = Document(
            title=title,
            vendor_name=request.form.get("vendor_name", "").strip() or None,
            doc_type=request.form.get("doc_type") or None,
            start_date=start_date,
            end_date=end_date,
            document_url=request.form.get("document_url", "").strip() or None,
            notes=request.form.get("notes", "").strip() or None,
            uploaded_by=current_user.id,
        )
        db.session.add(doc)
        db.session.flush()
        log_audit("CREATE", "documents", doc.id, new_values=doc.to_dict())
        db.session.commit()
        flash(f"Document '{title}' added.", "success")
        return redirect(url_for("documents.index"))

    return render_template("documents/form.html", doc=None, doc_types=DOC_TYPES)


@documents_bp.route("/<int:doc_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_document(doc_id):
    doc = Document.query.filter_by(id=doc_id, deleted_at=None).first_or_404()

    if request.method == "POST":
        old = doc.to_dict()
        doc.title = request.form.get("title", doc.title).strip()
        doc.vendor_name = request.form.get("vendor_name", "").strip() or None
        doc.doc_type = request.form.get("doc_type") or None
        doc.document_url = request.form.get("document_url", "").strip() or None
        doc.notes = request.form.get("notes", "").strip() or None
        try:
            doc.start_date = date.fromisoformat(request.form["start_date"]) if request.form.get("start_date") else None
            doc.end_date = date.fromisoformat(request.form["end_date"]) if request.form.get("end_date") else None
        except ValueError:
            flash("Invalid date format.", "danger")
            return render_template("documents/form.html", doc=doc, doc_types=DOC_TYPES)

        db.session.flush()
        log_audit("UPDATE", "documents", doc.id, old_values=old, new_values=doc.to_dict())
        db.session.commit()
        flash("Document updated.", "success")
        return redirect(url_for("documents.index"))

    return render_template("documents/form.html", doc=doc, doc_types=DOC_TYPES)


@documents_bp.route("/<int:doc_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_document(doc_id):
    doc = Document.query.filter_by(id=doc_id, deleted_at=None).first_or_404()
    old = doc.to_dict()
    doc.deleted_at = datetime.now(timezone.utc)
    log_audit("DELETE", "documents", doc.id, old_values=old)
    db.session.commit()
    flash("Document deleted.", "success")
    return redirect(url_for("documents.index"))
