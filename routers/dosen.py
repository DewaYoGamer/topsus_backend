"""Dosen endpoints.

Endpoints:
- GET    /dosen            (admin)  [cached]
- POST   /dosen            (admin)
- GET    /dosen/me         (dosen)
- GET    /dosen/{id}       (admin)
- PUT    /dosen/{id}       (admin)
- DELETE /dosen/{id}       (admin)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import CurrentUser, hash_password, require_admin, require_dosen
from ..cache import (
    DOSEN_LIST,
    cache_get_json,
    cache_set_json,
    invalidate_dosen_list,
)
from ..database import get_db
from ..models import Dosen
from ..schemas import DosenCreate, DosenMe, DosenRead, DosenUpdate

router = APIRouter(prefix="/dosen", tags=["dosen"])


@router.get("")
def list_dosen(
    response: Response,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
):
    cached = cache_get_json(DOSEN_LIST)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        return cached
    rows = db.query(Dosen).order_by(Dosen.id).all()
    payload = [DosenRead.model_validate(d).model_dump(mode="json") for d in rows]
    cache_set_json(DOSEN_LIST, payload)
    response.headers["X-Cache"] = "MISS"
    return payload


@router.post("", response_model=DosenRead, status_code=status.HTTP_201_CREATED)
def create_dosen(
    body: DosenCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> Dosen:
    dosen = Dosen(
        nama=body.nama,
        nip=body.nip,
        email=body.email,
        password=hash_password(body.password),
        role=body.role,
    )
    db.add(dosen)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="NIP atau email sudah dipakai",
        )
    db.refresh(dosen)
    invalidate_dosen_list()
    return dosen


@router.get("/me", response_model=DosenMe)
def dosen_me(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_dosen),
) -> Dosen:
    return user.entity  # type: ignore[return-value]


@router.get("/{dosen_id}", response_model=DosenRead)
def get_dosen(
    dosen_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> Dosen:
    dosen = db.get(Dosen, dosen_id)
    if not dosen:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dosen tidak ditemukan")
    return dosen


@router.put("/{dosen_id}", response_model=DosenRead)
def update_dosen(
    dosen_id: int,
    body: DosenUpdate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> Dosen:
    dosen = db.get(Dosen, dosen_id)
    if not dosen:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dosen tidak ditemukan")

    data = body.model_dump(exclude_unset=True)
    if "password" in data:
        data["password"] = hash_password(data["password"])
    for k, v in data.items():
        setattr(dosen, k, v)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "NIP atau email sudah dipakai"
        )
    db.refresh(dosen)
    invalidate_dosen_list()
    return dosen


@router.delete("/{dosen_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dosen(
    dosen_id: int,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_admin),
) -> None:
    if dosen_id == current.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Tidak bisa menghapus akun sendiri"
        )
    dosen = db.get(Dosen, dosen_id)
    if not dosen:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dosen tidak ditemukan")
    db.delete(dosen)
    db.commit()
    invalidate_dosen_list()
