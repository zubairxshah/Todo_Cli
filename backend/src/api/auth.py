from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response
from sqlmodel import Session, select, func
from datetime import timedelta
try:
    # Try relative import first
    from ..auth.jwt_handler import create_access_token, get_current_user
    from ..database import get_session
    from ..models.user import User, UserCreate, hash_password, verify_password, UserLogin
except ImportError:
    # Fall back to direct import within src
    try:
        from auth.jwt_handler import create_access_token, get_current_user
        from database import get_session
        from models.user import User, UserCreate, hash_password, verify_password, UserLogin
    except ImportError:
        # Last resort - assume running from project root
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
        from backend.src.auth.jwt_handler import create_access_token, get_current_user
        from backend.src.database import get_session
        from backend.src.models.user import User, UserCreate, hash_password, verify_password, UserLogin
from pydantic import BaseModel
import uuid

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Using HTTPBearer for token validation
security = HTTPBearer()


@router.options("/login")
@router.options("/signup")
@router.options("/logout")
async def auth_options():
    """Handle preflight OPTIONS requests for auth routes"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "Origin, X-Requested-With, Content-Type, Accept, Authorization",
        }
    )


# Using the UserLogin model instead of custom classes
LoginRequest = UserLogin
RegisterRequest = UserCreate


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int = 3600  # 1 hour in seconds


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _find_user_by_email(session: Session, email: str):
    # Case-insensitive: phones often capitalise the first letter of an email
    return session.exec(
        select(User).where(func.lower(User.email) == _normalize_email(email))
    ).first()


@router.post("/login", response_model=TokenResponse)
def login(login_request: LoginRequest, session: Session = Depends(get_session)):
    user = _find_user_by_email(session, login_request.email)

    # Check if user exists and password is correct
    if not user or not verify_password(login_request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer", "expires_in": 3600}


@router.post("/signup", response_model=TokenResponse)
def signup(register_request: RegisterRequest, session: Session = Depends(get_session)):
    # Check if user with email already exists
    existing_user = _find_user_by_email(session, register_request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Hash the password
    hashed_password = hash_password(register_request.password)

    # Create new user
    user = User(
        email=_normalize_email(register_request.email),
        hashed_password=hashed_password
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    # Create access token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer", "expires_in": 3600}


@router.post("/logout")
def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # In a real implementation, this would invalidate the token
    # For now, we'll just return a success message
    return {"message": "Successfully logged out"}