import os
from typing import List

class Settings:
    database_url: str = "sqlite:///./learning_platform.db"
    upload_dir: str = "./uploads"
    
    JWT_SECRET_KEY: str = "your-super-secret-key-change-in-production-very-long"
    JWT_REFRESH_SECRET_KEY: str = "your-super-secret-refresh-key-change-in-production-very-long"
    
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    
    MAX_FILE_SIZE_MB: int = 10

    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", self.database_url)
        self.upload_dir = os.getenv("UPLOAD_DIR", self.upload_dir)
        self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", self.JWT_SECRET_KEY)
        self.JWT_REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY", self.JWT_REFRESH_SECRET_KEY)
        self.ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", self.ALLOWED_ORIGINS)
        self.RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
        self.RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
        self.RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))


settings = Settings()