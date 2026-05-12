"""Seed an initial admin user and some demo data.

Run from repo root:
    python -m backend.seed

Default credentials:
    admin@kampus.ac.id / admin123
    budi@kampus.ac.id  / dosen123
    ani@kampus.ac.id   / mhs123
    chandra@kampus.ac.id / mhs123
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from .auth import hash_password
from .database import Base, SessionLocal, engine
from .models import Dosen, Mahasiswa


def seed() -> None:
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:  # type: Session
        # --- Admin ---
        if not db.query(Dosen).filter(Dosen.email == "admin@kampus.ac.id").first():
            db.add(
                Dosen(
                    nama="Administrator",
                    nip="0000000000",
                    email="admin@kampus.ac.id",
                    password=hash_password("admin123"),
                    role="admin",
                )
            )
            print("+ created admin@kampus.ac.id / admin123")

        # --- Demo dosen ---
        if not db.query(Dosen).filter(Dosen.email == "budi@kampus.ac.id").first():
            db.add(
                Dosen(
                    nama="Dr. Budi Santoso",
                    nip="1987654321",
                    email="budi@kampus.ac.id",
                    password=hash_password("dosen123"),
                    role="dosen",
                )
            )
            print("+ created budi@kampus.ac.id / dosen123")

        db.commit()

        dosen_budi = (
            db.query(Dosen).filter(Dosen.email == "budi@kampus.ac.id").first()
        )

        # --- Demo mahasiswa ---
        if not db.query(Mahasiswa).filter(Mahasiswa.email == "ani@kampus.ac.id").first():
            db.add(
                Mahasiswa(
                    nama="Ani Wijaya",
                    nim="2021001",
                    email="ani@kampus.ac.id",
                    password=hash_password("mhs123"),
                    dosen_pembimbing_id=dosen_budi.id if dosen_budi else None,
                )
            )
            print("+ created ani@kampus.ac.id / mhs123 (bimbingan Budi)")

        if not db.query(Mahasiswa).filter(Mahasiswa.email == "chandra@kampus.ac.id").first():
            db.add(
                Mahasiswa(
                    nama="Chandra Pratama",
                    nim="2021002",
                    email="chandra@kampus.ac.id",
                    password=hash_password("mhs123"),
                    dosen_pembimbing_id=None,
                )
            )
            print("+ created chandra@kampus.ac.id / mhs123 (belum ada pembimbing)")

        db.commit()
        print("seed done.")


if __name__ == "__main__":
    seed()
