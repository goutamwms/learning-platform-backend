import os
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, UploadFile, File as FastAPIFile
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.category import Category, Course
from app.models.lesson import Lesson
from app.models.lesson_file import LessonFile
from app.schemas.schemas import LessonResponse

router = APIRouter(prefix="/api/lessons", tags=["lessons"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
LESSON_FILES_DIR = os.path.join(UPLOAD_DIR, "lessons")


class LessonFileResponse(BaseModel):
    id: int
    lesson_id: int
    original_name: str
    file_size: int
    mime_type: str
    file_url: str
    created_at: datetime

    model_config = {"from_attributes": True}


def ensure_lesson_upload_dir():
    os.makedirs(LESSON_FILES_DIR, exist_ok=True)


@router.get("/{lesson_id}/files", response_model=List[LessonFileResponse])
def list_lesson_files(
    lesson_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    records = (
        db.query(LessonFile)
        .filter(LessonFile.lesson_id == lesson_id)
        .order_by(LessonFile.created_at.desc())
        .all()
    )
    return [
        LessonFileResponse(
            id=f.id,
            lesson_id=f.lesson_id,
            original_name=f.original_name,
            file_size=f.file_size,
            mime_type=f.mime_type,
            file_url=f"/uploads/lessons/{f.stored_name}",
            created_at=f.created_at,
        )
        for f in records
    ]


@router.post("/{lesson_id}/files", response_model=LessonFileResponse)
async def upload_lesson_file(
    lesson_id: int = Path(..., ge=1),
    file: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db),
):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    ensure_lesson_upload_dir()

    ext = os.path.splitext(file.filename or "file")[1] or ""
    stored_name = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(LESSON_FILES_DIR, stored_name)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    record = LessonFile(
        lesson_id=lesson_id,
        original_name=file.filename or "untitled",
        stored_name=stored_name,
        file_size=len(content),
        mime_type=file.content_type or "application/octet-stream",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return LessonFileResponse(
        id=record.id,
        lesson_id=record.lesson_id,
        original_name=record.original_name,
        file_size=record.file_size,
        mime_type=record.mime_type,
        file_url=f"/uploads/lessons/{record.stored_name}",
        created_at=record.created_at,
    )


@router.delete("/{lesson_id}/files/{file_id}")
def delete_lesson_file(
    lesson_id: int = Path(..., ge=1),
    file_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    record = (
        db.query(LessonFile)
        .filter(LessonFile.id == file_id, LessonFile.lesson_id == lesson_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = os.path.join(LESSON_FILES_DIR, record.stored_name)
    if os.path.exists(file_path):
        os.remove(file_path)

    db.delete(record)
    db.commit()
    return {"message": "File deleted"}


@router.delete("/{lesson_id}")
def delete_lesson(lesson_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    print(f"DELETE request for lesson_id: {lesson_id}")
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    db.delete(lesson)
    db.commit()
    return {"message": "Lesson deleted"}


@router.get("/{lesson_id}", response_model=LessonResponse)
def get_lesson_by_id(lesson_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    print(f"GET lesson by ID: {lesson_id}")
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


@router.get("/{category_slug}/{lesson_slug}", response_model=LessonResponse)
def get_lesson_direct(category_slug: str, lesson_slug: str, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.slug == category_slug).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    lesson = (
        db.query(Lesson)
        .filter(
            Lesson.category_id == category.id,
            Lesson.slug == lesson_slug,
            Lesson.course_id.is_(None),
        )
        .first()
    )
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    return lesson


@router.get("/{category_slug}/{course_slug}/{lesson_slug}", response_model=LessonResponse)
def get_lesson_via_course(
    category_slug: str, course_slug: str, lesson_slug: str, db: Session = Depends(get_db)
):
    category = db.query(Category).filter(Category.slug == category_slug).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    course = (
        db.query(Course)
        .filter(Course.category_id == category.id, Course.slug == course_slug)
        .first()
    )
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    lesson = (
        db.query(Lesson)
        .filter(
            Lesson.category_id == category.id,
            Lesson.course_id == course.id,
            Lesson.slug == lesson_slug,
        )
        .first()
    )
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    return lesson


@router.post("", response_model=LessonResponse)
def create_lesson(
    data: dict,
    db: Session = Depends(get_db),
):
    category_id = data.get("category_id")
    course_id = data.get("course_id")
    title = data.get("title")
    slug = data.get("slug")
    content = data.get("content")

    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if course_id:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        
        existing = (
            db.query(Lesson)
            .filter(Lesson.course_id == course_id, Lesson.slug == slug)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Slug already exists in this course")
    else:
        existing = (
            db.query(Lesson)
            .filter(
                Lesson.category_id == category_id,
                Lesson.course_id.is_(None),
                Lesson.slug == slug,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Slug already exists in this category")

    lesson = Lesson(
        category_id=category_id,
        course_id=course_id,
        title=title,
        slug=slug,
        content=content,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


@router.put("/{lesson_id}", response_model=LessonResponse)
def update_lesson(lesson_id: int = Path(..., ge=1), data: dict = None, db: Session = Depends(get_db)):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    for key, value in data.items():
        if value is not None and key in ["title", "slug", "content", "example_content", "category_id", "course_id"]:
            setattr(lesson, key, value)

    db.commit()
    db.refresh(lesson)
    return lesson
