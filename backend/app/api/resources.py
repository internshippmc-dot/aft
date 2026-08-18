from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.audit import record_audit
from app.auth.deps import get_current_user, require_ops
from app.db import get_db
from app.models.resource import Resource
from app.models.user import User
from app.schemas.resource import ResourceCreate, ResourceOut, ResourceUpdate

router = APIRouter(prefix="/resources", tags=["resources"])


def _out(r: Resource) -> ResourceOut:
    return ResourceOut(
        id=r.id, type=r.type, title=r.title, category=r.category, url=r.url,
        description=r.description, process_text=r.process_text, updated_at=r.updated_at,
    )


@router.get("", response_model=list[ResourceOut])
def list_resources(_user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    rows = db.scalars(select(Resource).order_by(Resource.updated_at.desc()))
    return [_out(r) for r in rows]


@router.post("", response_model=ResourceOut, status_code=status.HTTP_201_CREATED)
def create_resource(body: ResourceCreate, request: Request, user: User = Depends(require_ops), db: DbSession = Depends(get_db)):
    resource = Resource(
        type=body.type, title=body.title, category=body.category, url=body.url,
        description=body.description, process_text=body.process_text, created_by=user.id,
    )
    db.add(resource)
    db.flush()
    record_audit(db, request, user, "resource.create", "resource", str(resource.id), after={"title": body.title})
    db.commit()
    db.refresh(resource)
    return _out(resource)


@router.patch("/{resource_id}", response_model=ResourceOut)
def update_resource(
    resource_id: int, body: ResourceUpdate, request: Request,
    user: User = Depends(require_ops), db: DbSession = Depends(get_db),
):
    resource = db.get(Resource, resource_id)
    if resource is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No such resource.")
    before = {"title": resource.title, "url": resource.url}
    for field in ("title", "category", "url", "description", "process_text"):
        value = getattr(body, field)
        if value is not None:
            setattr(resource, field, value)
    db.flush()
    record_audit(db, request, user, "resource.update", "resource", str(resource.id), before=before, after={"title": resource.title})
    db.commit()
    db.refresh(resource)
    return _out(resource)


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(resource_id: int, request: Request, user: User = Depends(require_ops), db: DbSession = Depends(get_db)):
    resource = db.get(Resource, resource_id)
    if resource is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No such resource.")
    record_audit(db, request, user, "resource.delete", "resource", str(resource.id), before={"title": resource.title})
    db.delete(resource)
    db.commit()
