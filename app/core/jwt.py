from datetime import datetime, timedelta
from typing import Optional
import uuid
import jwt
from app.core.config import settings


class JWTService:
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7

    def create_access_token(self, user_id: int, role: str) -> tuple[str, datetime]:
        jti = str(uuid.uuid4())
        now = datetime.utcnow()
        expires = now + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "sub": str(user_id),
            "role": role,
            "type": "access",
            "jti": jti,
            "iat": now,
            "exp": expires,
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, expires

    def create_refresh_token(self, user_id: int) -> tuple[str, datetime]:
        jti = str(uuid.uuid4())
        now = datetime.utcnow()
        expires = now + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "jti": jti,
            "iat": now,
            "exp": expires,
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, expires

    def decode_token(self, token: str) -> Optional[dict]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def get_token_expiry(self) -> int:
        return self.access_token_expire_minutes * 60


jwt_service = JWTService()