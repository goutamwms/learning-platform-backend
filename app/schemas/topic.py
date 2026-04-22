from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, field_validator, HttpUrl
import re


class TagBase(BaseModel):
    name: str
    slug: Optional[str] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        slug = re.sub(r'[^a-z0-9]', '-', v.lower().strip())
        slug = re.sub(r'-+', '-', slug)
        return v

    model_config = ConfigDict(from_attributes=True)


class TagResponse(TagBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SectionBase(BaseModel):
    section_type: str
    content: Optional[str] = None
    section_metadata: Optional[Dict[str, Any]] = None
    sort_order: int = 0


class SectionCreate(SectionBase):
    pass


class SectionResponse(SectionBase):
    id: int
    topic_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TopicSectionBlock(BaseModel):
    id: Optional[int] = None
    type: str
    content: Optional[str] = None
    section_metadata: Optional[Dict[str, Any]] = None
    order: int


class TopicBase(BaseModel):
    title: str
    description: Optional[str] = None
    is_public: bool = True
    tags: Optional[List[str]] = []

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError('Title must be at least 3 characters')
        if len(v) > 500:
            raise ValueError('Title must be at most 500 characters')
        return v.strip()


class TopicCreate(TopicBase):
    sections: Optional[List[TopicSectionBlock]] = []

    @field_validator('sections')
    @classmethod
    def validate_sections(cls, v: Optional[List[TopicSectionBlock]]) -> Optional[List[TopicSectionBlock]]:
        if v:
            for i, section in enumerate(v):
                allowed_types = ['text', 'link', 'file', 'video', 'image', 'code', 'heading', 'quote', 'list', 'divider']
                if section.type not in allowed_types:
                    raise ValueError(f'Invalid section type: {section.type}. Allowed: {", ".join(allowed_types)}')
        return v


class TopicUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    tags: Optional[List[str]] = None
    sections: Optional[List[TopicSectionBlock]] = None


class TopicResponse(TopicBase):
    id: int
    slug: str
    author_id: int
    view_count: int
    is_public: bool
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TopicWithSectionsResponse(TopicResponse):
    sections: List[SectionResponse] = []
    author: Optional[Dict[str, Any]] = None
    tags: List[TagResponse] = []


class TopicListResponse(BaseModel):
    id: int
    title: str
    slug: str
    description: Optional[str] = None
    is_public: bool
    author_id: int
    author_username: str
    view_count: int
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    tag_names: List[str] = []

    model_config = ConfigDict(from_attributes=True)


class TopicFilterParams(BaseModel):
    search: Optional[str] = None
    tags: Optional[List[str]] = None
    sort_by: Optional[str] = "created_at"
    sort_order: Optional[str] = "desc"
    page: int = 1
    page_size: int = 20
    is_public: Optional[bool] = None


class TopicListResponseWrapper(BaseModel):
    items: List[TopicListResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    tags: List[str] = []


class FileUploadMetadata(BaseModel):
    original_name: str
    size: int
    mime_type: str


class ImageUploadMetadata(FileUploadMetadata):
    width: Optional[int] = None
    height: Optional[int] = None


class VideoUploadMetadata(FileUploadMetadata):
    duration: Optional[int] = None