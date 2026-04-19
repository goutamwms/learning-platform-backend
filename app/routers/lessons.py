from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.category import Category, Course
from app.models.lesson import Lesson
from app.schemas.schemas import LessonResponse

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


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
        if value is not None and key in ["title", "slug", "content", "category_id", "course_id"]:
            setattr(lesson, key, value)

    db.commit()
    db.refresh(lesson)
    return lesson
