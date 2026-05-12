"""Authentication & authorization helpers - JWT + bcrypt + role guards + blacklist."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import Dosen, Mahasiswa
from .redis_client import safe_exists, safe_set

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

BLACKLIST_KEY_PREFIX = "blacklist:jwt:"


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(*, subject_id: int, role: str, user_type: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": f"{user_type}:{subject_id}",
        "uid": subject_id,
        "role": role,
        "type": user_type,
        "jti": uuid.uuid4().hex,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Raise JWTError on invalid/expired, otherwise return claims dict."""
    return jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )


def blacklist_token(jti: str, exp_ts: int) -> bool:
    """Add a JWT's jti to the blacklist until its original expiry.

    `exp_ts` is the unix timestamp (seconds) from the token's `exp` claim.
    """
    ttl = max(int(exp_ts - datetime.now(timezone.utc).timestamp()), 1)
    return safe_set(f"{BLACKLIST_KEY_PREFIX}{jti}", "1", ex=ttl)


def is_blacklisted(jti: str) -> bool:
    return safe_exists(f"{BLACKLIST_KEY_PREFIX}{jti}")


@dataclass
class CurrentUser:
    id: int
    role: str          # "admin" | "dosen" | "mahasiswa"
    user_type: str     # "dosen" (row in dosen table) | "mahasiswa"
    entity: Dosen | Mahasiswa
    jti: str
    exp: int


_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> CurrentUser:
    try:
        payload = decode_token(token)
        uid: int | None = payload.get("uid")
        role: str | None = payload.get("role")
        user_type: str | None = payload.get("type")
        jti: str | None = payload.get("jti")
        exp: int | None = payload.get("exp")
        if (
            uid is None
            or role is None
            or user_type not in {"dosen", "mahasiswa"}
            or jti is None
            or exp is None
        ):
            raise _CREDENTIALS_EXC
    except JWTError:
        raise _CREDENTIALS_EXC

    if is_blacklisted(jti):
        raise _CREDENTIALS_EXC

    if user_type == "dosen":
        entity = db.get(Dosen, uid)
    else:
        entity = db.get(Mahasiswa, uid)
    if entity is None:
        raise _CREDENTIALS_EXC

    return CurrentUser(
        id=entity.id,
        role=entity.role,   # re-read from DB (can change)
        user_type=user_type,
        entity=entity,
        jti=jti,
        exp=int(exp),
    )


def require_roles(*allowed: str):
    allowed_set = set(allowed)

    def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role in {sorted(allowed_set)}",
            )
        return user

    return _checker


require_admin = require_roles("admin")
require_dosen = require_roles("dosen")
require_mahasiswa = require_roles("mahasiswa")
