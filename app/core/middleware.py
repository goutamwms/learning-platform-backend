from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.audit import RateLimitLog
from app.core.config import settings
from collections import defaultdict
from datetime import datetime, timedelta
import time


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.requests = requests
        self.window_seconds = window_seconds
        self.request_history = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_ip = self._get_client_ip(request)
        path = request.url.path
        
        if self._is_exempt_path(path):
            return await call_next(request)
        
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds
        
        self.request_history[client_ip] = [
            timestamp for timestamp in self.request_history[client_ip]
            if timestamp > cutoff_time
        ]
        
        if len(self.request_history[client_ip]) >= self.requests:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Please try again later."}
            )
        
        self.request_history[client_ip].append(current_time)
        
        self._log_request(client_ip, path)
        
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests)
        response.headers["X-RateLimit-Remaining"] = str(self.requests - len(self.request_history[client_ip]))
        
        return response

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _is_exempt_path(self, path: str) -> bool:
        exempt_paths = ["/health", "/docs", "/openapi.json", "/redoc"]
        return path in exempt_paths

    def _log_request(self, client_ip: str, path: str):
        try:
            db = SessionLocal()
            log = RateLimitLog(ip_address=client_ip, endpoint=path)
            db.add(log)
            db.commit()
            db.close()
        except Exception:
            pass


class BotProtectionMiddleware(BaseHTTPMiddleware):
    SUSPICIOUS_PATTERNS = [
        "bot", "crawler", "spider", "slurp", "bingbot", "googlebot"
    ]
    
    async def dispatch(self, request: Request, call_next):
        user_agent = request.headers.get("user-agent", "").lower()
        
        if self._is_suspicious_bot(request):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Access denied"}
            )
        
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response

    def _is_suspicious_bot(self, request: Request) -> bool:
        user_agent = request.headers.get("user-agent", "").lower()
        if not user_agent:
            return False
        return any(pattern in user_agent for pattern in self.SUSPICIOUS_PATTERNS)