from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User, BlacklistedToken
from app.core.password import hash_password, verify_password
from app.core.jwt import jwt_service
from app.schemas.auth import UserCreate, UserLogin
from fastapi import HTTPException, status


class AuthService:
    def create_user(self, db: Session, user_data: UserCreate) -> User:
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        existing_username = db.query(User).filter(User.username == user_data.username).first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        hashed_password = hash_password(user_data.password)
        user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password,
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def authenticate_user(self, db: Session, login_data: UserLogin) -> User:
        user = db.query(User).filter(User.email == login_data.email).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )
        
        user.last_login = datetime.utcnow()
        db.commit()
        
        return user

    def create_tokens_for_user(self, user: User) -> tuple[str, str, int]:
        access_token, _ = jwt_service.create_access_token(user.id, user.role.value)
        refresh_token, _ = jwt_service.create_refresh_token(user.id)
        expires_in = jwt_service.get_token_expiry()
        
        return access_token, refresh_token, expires_in

    def blacklist_token(self, db: Session, token: str) -> bool:
        payload = jwt_service.decode_token(token)
        if payload:
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                blacklisted = BlacklistedToken(jti=jti, expires_at=datetime.fromtimestamp(exp))
                db.add(blacklisted)
                db.commit()
                return True
        return False

    def is_token_blacklisted(self, db: Session, jti: str) -> bool:
        return db.query(BlacklistedToken).filter(BlacklistedToken.jti == jti).first() is not None


auth_service = AuthService()