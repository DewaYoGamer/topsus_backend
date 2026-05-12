"""Authentication router - /auth/login, /auth/logout, /auth/me."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from ..auth import (
    CurrentUser,
    blacklist_token,
    create_access_token,
    get_current_user,
    verify_password,
)
from ..config import get_settings
from ..database import get_db
from ..models import Dosen, Mahasiswa
from ..rate_limit import check_rate_limit
from ..schemas import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

_settings = get_settings()


def _client_ip(request: Request) -> str:
    # Trust X-Forwarded-For first hop (set by Railway/Vercel/reverse proxies).
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Check dosen table first, then mahasiswa table.

    Rate-limited per client IP (default 5 requests / 60s).
    """
    ip = _client_ip(request)
    rl = check_rate_limit(
        f"rl:login:{ip}",
        limit=_settings.login_rate_limit,
        window_seconds=_settings.login_rate_window_seconds,
    )
    response.headers["X-RateLimit-Limit"] = str(_settings.login_rate_limit)
    response.headers["X-RateLimit-Remaining"] = str(rl.remaining)
    if not rl.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Terlalu banyak percobaan login, coba lagi sebentar.",
            headers={"Retry-After": str(rl.retry_after)},
        )

    dosen = db.query(Dosen).filter(Dosen.email == body.email).one_or_none()
    if dosen and verify_password(body.password, dosen.password):
        token = create_access_token(
            subject_id=dosen.id, role=dosen.role, user_type="dosen"
        )
        return TokenResponse(
            access_token=token, role=dosen.role, id=dosen.id, nama=dosen.nama
        )

    mhs = db.query(Mahasiswa).filter(Mahasiswa.email == body.email).one_or_none()
    if mhs and verify_password(body.password, mhs.password):
        token = create_access_token(
            subject_id=mhs.id, role=mhs.role, user_type="mahasiswa"
        )
        return TokenResponse(
            access_token=token, role=mhs.role, id=mhs.id, nama=mhs.nama
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Email atau password salah",
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(user: CurrentUser = Depends(get_current_user)) -> None:
    """Add the current JWT's jti to the blacklist until its original expiry."""
    blacklist_token(user.jti, user.exp)


@router.get("/me")
def me(user: CurrentUser = Depends(get_current_user)) -> dict:
    return {
        "id": user.id,
        "role": user.role,
        "user_type": user.user_type,
        "nama": user.entity.nama,
        "email": user.entity.email,
    }
