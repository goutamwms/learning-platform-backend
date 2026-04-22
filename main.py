from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.core.middleware import RateLimitMiddleware, BotProtectionMiddleware
from app.core.config import settings
import os

from app.database import engine, Base, SessionLocal
from app.models.user import User, UserRole, BlacklistedToken
from app.models.topic import Topic, TopicSection, Tag
from app.models.audit import AuditLog, RateLimitLog
from app.routers import auth, topics, admin

from app.models.category import Category, Course
from app.models.lesson import Lesson
from app.routers import categories, courses, lessons, upload


app = FastAPI(title="Learning Platform API", version="2.0.0")

origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
allowed_origins = [o.strip() for o in origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(
        RateLimitMiddleware,
        requests=settings.RATE_LIMIT_REQUESTS,
        window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    )

app.add_middleware(BotProtectionMiddleware)

app.include_router(auth.router)
app.include_router(topics.router)
app.include_router(admin.router)

app.include_router(categories.router)
app.include_router(courses.router)
app.include_router(lessons.router)
app.include_router(upload.router)

upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
os.makedirs(upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if not admin_user:
            from app.core.password import hash_password
            admin = User(
                email="admin@example.com",
                username="admin",
                hashed_password=hash_password("Admin123!"),
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True,
            )
            db.add(admin)
            db.commit()
            print("Admin user created: admin@example.com / Admin123!")
    finally:
        db.close()


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)