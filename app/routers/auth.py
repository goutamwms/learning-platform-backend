from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.audit import AuditLog
from app.schemas.auth import (
    UserCreate, 
    UserLogin, 
    UserResponse, 
    TokenResponse,
    RefreshTokenRequest
)
from app.services.auth_service import auth_service
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.models.user import User
from pydantic import BaseModel


router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class CookieResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


def _set_auth_cookies(response: Response, access_token: str, expires_in: int):
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=expires_in
    )


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(user_data: UserCreate, response: Response, db: Session = Depends(get_db)):
    user = auth_service.create_user(db, user_data)
    access_token, refresh_token, expires_in = auth_service.create_tokens_for_user(user)
    
    _set_auth_cookies(response, access_token, expires_in)
    
    _log_audit(db, user.id, "signup", "user", user.id, None)
    
    return user


@router.post("/login", response_model=UserResponse)
def login(
    login_data: UserLogin, 
    response: Response, 
    db: Session = Depends(get_db)
):
    user = auth_service.authenticate_user(db, login_data)
    access_token, refresh_token, expires_in = auth_service.create_tokens_for_user(user)
    
    _set_auth_cookies(response, access_token, expires_in)
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7
    )
    
    _log_audit(db, user.id, "login", "user", user.id, None)
    
    return user


@router.post("/logout")
def logout(response: Response, current_user: User = Depends(get_current_user)):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found"
        )
    
    from app.core.jwt import jwt_service
    payload = jwt_service.decode_token(refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = int(payload.get("sub"))
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    access_token, _, expires_in = auth_service.create_tokens_for_user(user)
    
    _set_auth_cookies(response, access_token, expires_in)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return current_user


def _log_audit(db: Session, user_id: int, action: str, resource_type: str, resource_id: int, ip_address: str):
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address
    )
    db.add(audit_log)
    db.commit()