from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.entities import User, UserRole
from app.schemas.auth import Token, UserLogin, UserRead, UserSignup
from app.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


@router.post("/signup", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def signup(payload: UserSignup, request: Request, db: Session = Depends(get_db)):
    role = UserRole.INVESTIGATOR.value
    if payload.username.lower().startswith("admin") or payload.email.lower().startswith("admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator accounts cannot self-register. Contact system administrator.",
        )

    existing = db.scalar(
        select(User).where(
            (User.username == payload.username)
            | (User.email == payload.email)
            | (User.badge_number == payload.badge_number)
        )
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username, email, or badge already registered")

    hashed = hash_password(payload.password)
    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hashed,
        badge_number=payload.badge_number,
        role=role,
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username, email, or badge already registered")

    write_audit(
        db,
        action_type="USER_SIGNUP",
        user_id=user.id,
        metadata={"username": user.username, "role": user.role},
        ip_address=_client_ip(request),
    )
    return user


@router.post("/login", response_model=Token)
def login(payload: UserLogin, request: Request, db: Session = Depends(get_db)):
    identifier = payload.username_or_email.strip()
    user = db.scalar(
        select(User).where((User.username == identifier) | (User.email == identifier))
    )
    if user is None or not verify_password(payload.password, user.hashed_password):
        write_audit(
            db,
            action_type="LOGIN_FAILED",
            user_id=user.id if user else None,
            metadata={"identifier": identifier},
            ip_address=_client_ip(request),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    token = create_access_token(subject=str(user.id), role=user.role)
    write_audit(
        db,
        action_type="LOGIN_SUCCESS",
        user_id=user.id,
        metadata={"username": user.username, "role": user.role},
        ip_address=_client_ip(request),
    )
    return Token(access_token=token)


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)):
    return current_user