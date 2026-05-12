"""SQLAlchemy ORM models - Dosen & Mahasiswa."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class DosenRole(str, Enum):
    ADMIN = "admin"
    DOSEN = "dosen"


class MahasiswaRole(str, Enum):
    MAHASISWA = "mahasiswa"


class Dosen(Base):
    __tablename__ = "dosen"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nama: Mapped[str] = mapped_column(String(100), nullable=False)
    nip: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(16), nullable=False, default=DosenRole.DOSEN.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    mahasiswa_bimbingan: Mapped[list["Mahasiswa"]] = relationship(
        back_populates="dosen_pembimbing",
        foreign_keys="Mahasiswa.dosen_pembimbing_id",
    )


class Mahasiswa(Base):
    __tablename__ = "mahasiswa"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nama: Mapped[str] = mapped_column(String(100), nullable=False)
    nim: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(16), nullable=False, default=MahasiswaRole.MAHASISWA.value
    )
    dosen_pembimbing_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("dosen.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    dosen_pembimbing: Mapped["Dosen | None"] = relationship(
        back_populates="mahasiswa_bimbingan",
        foreign_keys=[dosen_pembimbing_id],
    )
