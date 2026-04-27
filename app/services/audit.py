from flask import request as flask_request
from flask_login import current_user
from app import db
from app.models.audit import AuditLog


def log_audit(action, table_name, record_id, old_values=None, new_values=None):
    """Write an immutable audit record. Call before db.session.commit()."""
    user_id = current_user.id if current_user and current_user.is_authenticated else 0
    user_email = current_user.email if current_user and current_user.is_authenticated else "system"

    try:
        ip = flask_request.remote_addr
        ua = flask_request.user_agent.string
    except RuntimeError:
        ip = None
        ua = None

    entry = AuditLog(
        performed_by=user_id,
        user_email=user_email,
        action=action,
        table_name=table_name,
        record_id=record_id,
        old_values=old_values,
        new_values=new_values,
        ip_address=ip,
        user_agent=ua,
    )
    db.session.add(entry)
