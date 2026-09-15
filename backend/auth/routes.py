from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database.connection import SessionLocal
from backend.database.models import User

from .security import (
    create_access_token,
    verify_password,
    get_password_hash,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# ============================================================
# DATABASE
# ============================================================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ============================================================
# REGISTER REQUEST
# ============================================================

class RegisterRequest(BaseModel):
    username: str
    password: str


# ============================================================
# LOGIN
# ============================================================

@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(
            User.username == form_data.username
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    if not verify_password(
        form_data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    access_token = create_access_token(
        data={
            "sub": str(user.user_id),
            "username": user.username,
            "role": user.role,
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role,
        },
    }


# ============================================================
# REGISTER NEW USER
# ============================================================

@router.post("/register")
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    username = request.username.strip()
    password = request.password

    # --------------------------------------------------------
    # BASIC VALIDATION
    # --------------------------------------------------------

    if not username:
        raise HTTPException(
            status_code=400,
            detail="Username is required.",
        )

    if not password:
        raise HTTPException(
            status_code=400,
            detail="Password is required.",
        )

    if len(username) < 3:
        raise HTTPException(
            status_code=400,
            detail="Username must contain at least 3 characters.",
        )

    if len(password) < 4:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 4 characters.",
        )

    # --------------------------------------------------------
    # CHECK DUPLICATE USERNAME
    # --------------------------------------------------------

    existing_user = (
        db.query(User)
        .filter(
            User.username == username
        )
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Username '{username}' "
                "already exists."
            ),
        )

    # --------------------------------------------------------
    # CREATE USER
    # --------------------------------------------------------

    new_user = User(
        username=username,
        password_hash=get_password_hash(password),
        role="ADMIN",
        is_active=True,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User created successfully.",
        "user": {
            "user_id": new_user.user_id,
            "username": new_user.username,
            "role": new_user.role,
            "is_active": new_user.is_active,
        },
    }