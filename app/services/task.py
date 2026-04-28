from datetime import date
from app.models.task import TaskDefinition, TaskCompletion


def is_due(task: TaskDefinition, on: date) -> bool:
    if task.frequency == "daily":
        return True
    if task.frequency == "weekly":
        return task.day_of_week is not None and on.weekday() == task.day_of_week
    if task.frequency == "monthly":
        return task.day_of_month is not None and on.day == task.day_of_month
    if task.frequency == "one_off":
        return task.one_off_date == on
    return False


def get_due_tasks(on: date) -> list:
    """Return list of (TaskDefinition, TaskCompletion|None) for the given date."""
    active = TaskDefinition.query.filter_by(is_active=True, deleted_at=None).all()
    due = [t for t in active if is_due(t, on)]

    completions = {
        c.task_def_id: c
        for c in TaskCompletion.query.filter(
            TaskCompletion.task_def_id.in_([t.id for t in due]),
            TaskCompletion.due_date == on,
        ).all()
    } if due else {}

    return [(t, completions.get(t.id)) for t in due]


def completion_rate(on: date) -> dict:
    tasks = get_due_tasks(on)
    total = len(tasks)
    done = sum(1 for _, c in tasks if c is not None)
    return {"due": total, "completed": done, "rate": round(done / total * 100) if total else 0}
