from datetime import date
from sqlalchemy import func
from app import db
from app.models.leave import LeaveQuota, LeaveRequest


def fiscal_year_for(d: date) -> int:
    """April–March fiscal year. Apr 2025 → 2025, Mar 2026 → 2025."""
    return d.year if d.month >= 4 else d.year - 1


def get_or_create_quota(user_id: int, fiscal_year: int) -> LeaveQuota:
    quota = LeaveQuota.query.filter_by(user_id=user_id, fiscal_year=fiscal_year).first()
    if not quota:
        quota = LeaveQuota(user_id=user_id, fiscal_year=fiscal_year)
        db.session.add(quota)
        db.session.flush()
    return quota


def get_balance(user_id: int, fiscal_year: int) -> dict:
    quota = get_or_create_quota(user_id, fiscal_year)

    used = (
        db.session.query(LeaveRequest.leave_type, func.sum(LeaveRequest.total_days))
        .filter(
            LeaveRequest.user_id == user_id,
            LeaveRequest.fiscal_year == fiscal_year,
            LeaveRequest.status == "approved",
        )
        .group_by(LeaveRequest.leave_type)
        .all()
    )
    used_map = {lt: float(days) for lt, days in used}

    return {
        "casual":  {"total": quota.casual_total,  "used": used_map.get("casual", 0),  "remaining": quota.casual_total  - used_map.get("casual", 0)},
        "sick":    {"total": quota.sick_total,    "used": used_map.get("sick", 0),    "remaining": quota.sick_total    - used_map.get("sick", 0)},
        "earned":  {"total": quota.earned_total,  "used": used_map.get("earned", 0),  "remaining": quota.earned_total  - used_map.get("earned", 0)},
        "fiscal_year": fiscal_year,
    }


def count_leave_days(start: date, end: date) -> float:
    """Count calendar days (weekends included — adjust here if needed)."""
    return float((end - start).days + 1)
