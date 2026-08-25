import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.audit import record_audit
from app.auth.deps import get_current_user, require_ops
from app.db import get_db
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _out(t: Task) -> TaskOut:
    return TaskOut(
        id=t.id, title=t.title, priority=t.priority, entity_type=t.entity_type, entity_id=t.entity_id,
        due_on=t.due_on, status=t.status, notes=t.notes, created_at=t.created_at, completed_at=t.completed_at,
    )


@router.get("", response_model=list[TaskOut])
def list_tasks(
    status_filter: str | None = None,
    _user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    query = select(Task).order_by(Task.due_on.asc().nulls_last(), Task.created_at.desc())
    if status_filter:
        query = query.where(Task.status == status_filter)
    return [_out(t) for t in db.scalars(query)]


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(body: TaskCreate, request: Request, user: User = Depends(require_ops), db: DbSession = Depends(get_db)):
    task = Task(
        title=body.title, priority=body.priority, entity_type=body.entity_type, entity_id=body.entity_id,
        due_on=body.due_on, notes=body.notes, created_by=user.id,
    )
    db.add(task)
    db.flush()
    record_audit(db, request, user, "task.create", "task", str(task.id), after={"title": body.title})
    db.commit()
    db.refresh(task)
    return _out(task)


@router.patch("/{task_id}/complete", response_model=TaskOut)
def complete_task(
    task_id: int, request: Request,
    user: User = Depends(require_ops), db: DbSession = Depends(get_db),
):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No such task.")
    before = {"status": task.status}
    task.status = "Done"
    task.completed_at = datetime.datetime.now(datetime.timezone.utc)
    db.flush()
    record_audit(db, request, user, "task.complete", "task", str(task.id), before=before, after={"status": "Done"})
    db.commit()
    db.refresh(task)
    return _out(task)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int, body: TaskUpdate, request: Request,
    user: User = Depends(require_ops), db: DbSession = Depends(get_db),
):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No such task.")
    before = {"title": task.title, "priority": task.priority, "due_on": str(task.due_on), "notes": task.notes}
    for field in ("title", "priority", "due_on", "notes"):
        if field in body.model_fields_set:
            setattr(task, field, getattr(body, field))
    db.flush()
    record_audit(
        db, request, user, "task.update", "task", str(task.id),
        before=before, after={"title": task.title, "priority": task.priority, "due_on": str(task.due_on), "notes": task.notes},
    )
    db.commit()
    db.refresh(task)
    return _out(task)


@router.patch("/{task_id}/reopen", response_model=TaskOut)
def reopen_task(
    task_id: int, request: Request, user: User = Depends(require_ops), db: DbSession = Depends(get_db)
):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No such task.")
    before = {"status": task.status}
    task.status = "Open"
    task.completed_at = None
    db.flush()
    record_audit(db, request, user, "task.reopen", "task", str(task.id), before=before, after={"status": "Open"})
    db.commit()
    db.refresh(task)
    return _out(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int, request: Request, user: User = Depends(require_ops), db: DbSession = Depends(get_db)
):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No such task.")
    record_audit(db, request, user, "task.delete", "task", str(task.id), before={"title": task.title, "status": task.status})
    db.delete(task)
    db.commit()
