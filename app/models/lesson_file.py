from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from app.database import Base


class LessonFile(Base):
    __tablename__ = "lesson_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lesson_id = Column(
        Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False
    )
    original_name = Column(String(255), nullable=False)
    stored_name = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    mime_type = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    lesson = relationship("Lesson", back_populates="files")
