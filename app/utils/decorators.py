from functools import wraps
from flask import abort
from flask_login import current_user


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def manager_or_admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not (current_user.is_admin or current_user.is_manager):
            abort(403)
        return f(*args, **kwargs)
    return decorated
