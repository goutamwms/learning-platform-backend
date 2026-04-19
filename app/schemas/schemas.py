from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class CategoryBase(BaseModel):
    title: str
    slug: str
    description: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None


class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    lesson_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class LessonBase(BaseModel):
    title: str
    slug: str
    content: Optional[str] = None


class LessonResponse(LessonBase):
    id: int
    category_id: int
    course_id: Optional[int] = None
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CourseBase(BaseModel):
    title: str
    slug: str
    description: Optional[str] = None


class CourseCreate(CourseBase):
    category_id: int


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None


class CourseResponse(CourseBase):
    id: int
    category_id: int
    sort_order: int
    created_at: datetime
    updated_at: datetime
    lessons: List[LessonResponse] = []

    model_config = ConfigDict(from_attributes=True)


class CourseWithLessonsResponse(CourseResponse):
    lessons: List[LessonResponse] = []


class CategoryWithContentResponse(CategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    courses: List[CourseWithLessonsResponse] = []
    direct_lessons: List[LessonResponse] = []

    model_config = ConfigDict(from_attributes=True)


class UploadResponse(BaseModel):
    url: str
