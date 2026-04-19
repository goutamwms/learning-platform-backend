from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.category import Category, Course
from app.models.lesson import Lesson as LessonModel
from app.schemas.schemas import CourseCreate, CourseUpdate, CourseResponse, LessonResponse

router = APIRouter(prefix="/api", tags=["courses"])


@router.get("/courses", response_model=dict)
def get_all_courses(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    sort_by: str = Query("title", pattern="^(title|created_at|lesson_count)$"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    query = db.query(Course)
    
    if category_id:
        query = query.filter(Course.category_id == category_id)
    
    if search:
        query = query.filter(Course.title.ilike(f"%{search}%"))
    
    total = query.count()
    
    sort_column = getattr(Course, sort_by) if sort_by != "lesson_count" else Course.id
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())
    
    courses = query.offset(skip).limit(limit).all()
    
    result = []
    for course in courses:
        lesson_count = (
            db.query(func.count(LessonModel.id))
            .filter(LessonModel.course_id == course.id)
            .scalar()
        )
        category = db.query(Category).filter(Category.id == course.category_id).first()
        
        result.append({
            "id": course.id,
            "category_id": course.category_id,
            "category_title": category.title if category else None,
            "title": course.title,
            "slug": course.slug,
            "description": course.description,
            "sort_order": course.sort_order,
            "created_at": course.created_at,
            "updated_at": course.updated_at,
            "lesson_count": lesson_count,
        })
    
    if sort_by == "lesson_count":
        result.sort(key=lambda x: x["lesson_count"], reverse=(sort_order == "desc"))
    
    return {
        "items": result,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": skip + len(courses) < total
    }


@router.get("/courses/{course_id}", response_model=CourseResponse)
def get_course_by_id(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    lessons = (
        db.query(LessonModel)
        .filter(LessonModel.course_id == course.id)
        .order_by(LessonModel.sort_order)
        .all()
    )
    
    return CourseResponse(
        id=course.id,
        category_id=course.category_id,
        title=course.title,
        slug=course.slug,
        description=course.description,
        sort_order=course.sort_order,
        created_at=course.created_at,
        updated_at=course.updated_at,
        lessons=[LessonResponse.model_validate(l) for l in lessons],
    )


@router.get("/categories/{category_id}/courses", response_model=List[CourseResponse])
def get_courses_by_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    courses = db.query(Course).filter(Course.category_id == category_id).order_by(Course.sort_order).all()
    
    result = []
    for course in courses:
        lessons = (
            db.query(LessonModel)
            .filter(LessonModel.course_id == course.id)
            .order_by(LessonModel.sort_order)
            .all()
        )
        course_data = CourseResponse(
            id=course.id,
            category_id=course.category_id,
            title=course.title,
            slug=course.slug,
            description=course.description,
            sort_order=course.sort_order,
            created_at=course.created_at,
            updated_at=course.updated_at,
            lessons=[LessonResponse.model_validate(l) for l in lessons],
        )
        result.append(course_data)
    
    return result


@router.post("/courses", response_model=CourseResponse)
def create_course(data: CourseCreate, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == data.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    existing = (
        db.query(Course)
        .filter(Course.category_id == data.category_id, Course.slug == data.slug)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Slug already exists in this category")

    course = Course(**data.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)
    
    return CourseResponse(
        id=course.id,
        category_id=course.category_id,
        title=course.title,
        slug=course.slug,
        description=course.description,
        sort_order=course.sort_order,
        created_at=course.created_at,
        updated_at=course.updated_at,
        lessons=[],
    )


@router.put("/courses/{course_id}", response_model=CourseResponse)
def update_course(course_id: int, data: CourseUpdate, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if data.slug and data.slug != course.slug:
        existing = (
            db.query(Course)
            .filter(Course.category_id == course.category_id, Course.slug == data.slug)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Slug already exists in this category")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(course, key, value)

    db.commit()
    db.refresh(course)
    
    lessons = (
        db.query(LessonModel)
        .filter(LessonModel.course_id == course.id)
        .order_by(LessonModel.sort_order)
        .all()
    )
    
    return CourseResponse(
        id=course.id,
        category_id=course.category_id,
        title=course.title,
        slug=course.slug,
        description=course.description,
        sort_order=course.sort_order,
        created_at=course.created_at,
        updated_at=course.updated_at,
        lessons=[LessonResponse.model_validate(l) for l in lessons],
    )


@router.delete("/{course_id}")
def delete_course(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    db.delete(course)
    db.commit()
    return {"message": "Course deleted"}
