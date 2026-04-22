from datetime import datetime, timedelta
from typing import Optional
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.core.jwt import jwt_service
from app.models.audit import AuditLog


security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    token = None
    
    if credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")
    
    if not token:
        return None
    payload = jwt_service.decode_token(token)
    
    if not payload:
        return None
    
    jti = payload.get("jti")
    if jti:
        from app.models.user import BlacklistedToken
        if db.query(BlacklistedToken).filter(BlacklistedToken.jti == jti).first():
            return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        return None
    
    _log_request(db, request, user.id, "access_token_used")
    
    return user


async def require_current_user(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return current_user


async def require_admin(current_user: User = Depends(require_current_user)) -> User:
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def _log_request(db: Session, request: Request, user_id: Optional[int], action: str):
    try:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type="auth",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        db.add(audit_log)
        db.commit()
    except Exception:
        pass