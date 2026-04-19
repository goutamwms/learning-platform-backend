from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.category import Category, Course
from app.models.lesson import Lesson as LessonModel
from app.schemas.schemas import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryWithContentResponse,
)

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.delete("/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    db.delete(category)
    db.commit()
    return {"message": "Category deleted"}


@router.get("", response_model=List[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).all()
    result = []
    for cat in categories:
        lesson_count = (
            db.query(func.count(LessonModel.id))
            .filter(LessonModel.category_id == cat.id)
            .scalar()
        )
        cat_dict = {
            "id": cat.id,
            "title": cat.title,
            "slug": cat.slug,
            "description": cat.description,
            "created_at": cat.created_at,
            "updated_at": cat.updated_at,
            "lesson_count": lesson_count,
        }
        result.append(CategoryResponse(**cat_dict))
    return result


@router.get("/by-id/{category_id}", response_model=CategoryResponse)
def get_category_by_id(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.get("/{slug}", response_model=CategoryWithContentResponse)
def get_category(slug: str, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.slug == slug).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    courses = db.query(Course).filter(Course.category_id == category.id).order_by(Course.sort_order).all()
    
    courses_with_lessons = []
    for course in courses:
        lessons = (
            db.query(LessonModel)
            .filter(LessonModel.course_id == course.id)
            .order_by(LessonModel.sort_order)
            .all()
        )
        courses_with_lessons.append({
            **course.__dict__,
            "lessons": lessons,
        })

    direct_lessons = (
        db.query(LessonModel)
        .filter(LessonModel.category_id == category.id, LessonModel.course_id.is_(None))
        .order_by(LessonModel.sort_order)
        .all()
    )

    return CategoryWithContentResponse(
        id=category.id,
        title=category.title,
        slug=category.slug,
        description=category.description,
        created_at=category.created_at,
        updated_at=category.updated_at,
        courses=courses_with_lessons,
        direct_lessons=direct_lessons,
    )


@router.post("", response_model=CategoryResponse)
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    existing = db.query(Category).filter(Category.slug == data.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Slug already exists")

    category = Category(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(category_id: int, data: CategoryUpdate, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if data.slug and data.slug != category.slug:
        existing = db.query(Category).filter(Category.slug == data.slug).first()
        if existing:
            raise HTTPException(status_code=400, detail="Slug already exists")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(category, key, value)

    db.commit()
    db.refresh(category)
    return category
