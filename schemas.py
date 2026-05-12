"""Pydantic schemas - request and response models."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- Auth ----------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    id: int
    nama: str


# ---------- Dosen ----------
class DosenBase(BaseModel):
    nama: str = Field(min_length=1, max_length=100)
    nip: str = Field(min_length=1, max_length=20)
    email: EmailStr


class DosenCreate(DosenBase):
    password: str = Field(min_length=6, max_length=128)
    role: Literal["admin", "dosen"] = "dosen"


class DosenUpdate(BaseModel):
    nama: str | None = Field(default=None, min_length=1, max_length=100)
    nip: str | None = Field(default=None, min_length=1, max_length=20)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
    role: Literal["admin", "dosen"] | None = None


class DosenRead(DosenBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    created_at: datetime


# ---------- Mahasiswa ----------
class MahasiswaBase(BaseModel):
    nama: str = Field(min_length=1, max_length=100)
    nim: str = Field(min_length=1, max_length=20)
    email: EmailStr


class MahasiswaCreate(MahasiswaBase):
    password: str = Field(min_length=6, max_length=128)
    dosen_pembimbing_id: int | None = None


class MahasiswaUpdate(BaseModel):
    nama: str | None = Field(default=None, min_length=1, max_length=100)
    nim: str | None = Field(default=None, min_length=1, max_length=20)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)


class AssignPembimbingRequest(BaseModel):
    dosen_id: int | None = None  # None = unassign


class DosenSummary(BaseModel):
    """Lightweight dosen info embedded in mahasiswa response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    nama: str
    nip: str
    email: EmailStr


class MahasiswaRead(MahasiswaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    dosen_pembimbing_id: int | None
    dosen_pembimbing: DosenSummary | None = None
    created_at: datetime


class MahasiswaSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nama: str
    nim: str
    email: EmailStr


# ---------- "Me" endpoints ----------
class DosenMe(DosenRead):
    mahasiswa_bimbingan: list[MahasiswaSummary] = []


class MahasiswaMe(MahasiswaRead):
    pass
