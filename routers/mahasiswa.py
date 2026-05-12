"""Mahasiswa endpoints.

Endpoints:
- GET    /mahasiswa                          (admin, dosen->auto filter)  [cached]
- POST   /mahasiswa                          (admin)
- GET    /mahasiswa/me                       (mahasiswa)
- GET    /mahasiswa/{id}                     (admin)
- PUT    /mahasiswa/{id}                     (admin)
- DELETE /mahasiswa/{id}                     (admin)
- PATCH  /mahasiswa/{id}/pembimbing          (admin)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import (
    CurrentUser,
    get_current_user,
    hash_password,
    require_admin,
    require_mahasiswa,
)
from ..cache import (
    cache_get_json,
    cache_set_json,
    invalidate_mahasiswa_all,
    mhs_list_key_for,
)
from ..database import get_db
from ..models import Dosen, Mahasiswa
from ..schemas import (
    AssignPembimbingRequest,
    MahasiswaCreate,
    MahasiswaMe,
    MahasiswaRead,
    MahasiswaUpdate,
)

router = APIRouter(prefix="/mahasiswa", tags=["mahasiswa"])


@router.get("")
def list_mahasiswa(
    response: Response,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Admin: all rows. Dosen: only his/her bimbingan. Mahasiswa: forbidden."""
    if user.role == "mahasiswa":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")

    cache_key = mhs_list_key_for(user.role, user.id)
    if cache_key:
        cached = cache_get_json(cache_key)
        if cached is not None:
            response.headers["X-Cache"] = "HIT"
            return cached

    q = db.query(Mahasiswa)
    if user.role == "dosen":
        q = q.filter(Mahasiswa.dosen_pembimbing_id == user.id)
    rows = q.order_by(Mahasiswa.id).all()
    payload = [MahasiswaRead.model_validate(m).model_dump(mode="json") for m in rows]
    if cache_key:
        cache_set_json(cache_key, payload)
    response.headers["X-Cache"] = "MISS"
    return payload


@router.post("", response_model=MahasiswaRead, status_code=status.HTTP_201_CREATED)
def create_mahasiswa(
    body: MahasiswaCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> Mahasiswa:
    if body.dosen_pembimbing_id is not None:
        if not db.get(Dosen, body.dosen_pembimbing_id):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Dosen pembimbing tidak ditemukan"
            )

    mhs = Mahasiswa(
        nama=body.nama,
        nim=body.nim,
        email=body.email,
        password=hash_password(body.password),
        dosen_pembimbing_id=body.dosen_pembimbing_id,
    )
    db.add(mhs)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "NIM atau email sudah dipakai"
        )
    db.refresh(mhs)
    invalidate_mahasiswa_all()
    return mhs


@router.get("/me", response_model=MahasiswaMe)
def mahasiswa_me(
    user: CurrentUser = Depends(require_mahasiswa),
) -> Mahasiswa:
    return user.entity  # type: ignore[return-value]


@router.get("/{mhs_id}", response_model=MahasiswaRead)
def get_mahasiswa(
    mhs_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> Mahasiswa:
    mhs = db.get(Mahasiswa, mhs_id)
    if not mhs:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mahasiswa tidak ditemukan")
    if user.role == "admin":
        return mhs
    if user.role == "dosen" and mhs.dosen_pembimbing_id == user.id:
        return mhs
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")


@router.put("/{mhs_id}", response_model=MahasiswaRead)
def update_mahasiswa(
    mhs_id: int,
    body: MahasiswaUpdate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> Mahasiswa:
    mhs = db.get(Mahasiswa, mhs_id)
    if not mhs:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mahasiswa tidak ditemukan")

    data = body.model_dump(exclude_unset=True)
    if "password" in data:
        data["password"] = hash_password(data["password"])
    for k, v in data.items():
        setattr(mhs, k, v)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "NIM atau email sudah dipakai"
        )
    db.refresh(mhs)
    invalidate_mahasiswa_all()
    return mhs


@router.delete("/{mhs_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mahasiswa(
    mhs_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> None:
    mhs = db.get(Mahasiswa, mhs_id)
    if not mhs:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mahasiswa tidak ditemukan")
    db.delete(mhs)
    db.commit()
    invalidate_mahasiswa_all()


@router.patch("/{mhs_id}/pembimbing", response_model=MahasiswaRead)
def assign_pembimbing(
    mhs_id: int,
    body: AssignPembimbingRequest,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> Mahasiswa:
    mhs = db.get(Mahasiswa, mhs_id)
    if not mhs:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mahasiswa tidak ditemukan")

    if body.dosen_id is not None:
        dosen = db.get(Dosen, body.dosen_id)
        if not dosen:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Dosen tidak ditemukan"
            )

    mhs.dosen_pembimbing_id = body.dosen_id
    db.commit()
    db.refresh(mhs)
    invalidate_mahasiswa_all()
    return mhs
