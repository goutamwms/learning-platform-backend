from typing import List, Optional
import json
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.topic import (
    TopicCreate, TopicUpdate, TopicResponse,
    TopicWithSectionsResponse, TopicListResponseWrapper,
    TopicListResponse, TagResponse
)
from app.services.topic_service import topic_service
from app.core.dependencies import get_current_user, require_admin
from app.models.user import User
from app.models.topic import Tag


router = APIRouter(prefix="/api/topics", tags=["Topics"])


def parse_section_metadata(metadata):
    if metadata is None:
        return None
    if isinstance(metadata, dict):
        return metadata
    if isinstance(metadata, str):
        try:
            return json.loads(metadata)
        except:
            return None
    return None


@router.get("", response_model=TopicListResponseWrapper)
def get_topics(
    search: Optional[str] = Query(None),
    starts_with: Optional[str] = Query(None, description="Filter by first letter of title"),
    tags: Optional[List[str]] = Query(None),
    sort_by: str = Query("created_at", pattern="^(created_at|updated_at|title|view_count)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return topic_service.get_topics(
        db=db,
        search=search,
        starts_with=starts_with,
        tags=tags,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
        current_user=current_user
    )


@router.get("/tags", response_model=List[TagResponse])
def get_all_tags(db: Session = Depends(get_db)):
    tags = db.query(Tag).all()
    return tags


@router.get("/my-topics", response_model=List[TopicListResponse])
def get_my_topics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    topics = topic_service.get_user_topics(db, current_user.id, current_user)
    return [
        TopicListResponse(
            id=t.id,
            title=t.title,
            slug=t.slug,
            description=t.description,
            is_public=t.is_public,
            author_id=t.author_id,
            author_username=t.author.username,
            view_count=t.view_count,
            created_at=t.created_at,
            updated_at=t.updated_at,
            published_at=t.published_at,
            tag_names=[tag.name for tag in t.tags]
        )
        for t in topics
    ]


@router.get("/{topic_id}", response_model=TopicWithSectionsResponse)
def get_topic(
    topic_id: int,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    topic = topic_service.get_topic(db, topic_id, current_user)
    
    from app.schemas.topic import SectionResponse, TagResponse as TagResp
    
    return TopicWithSectionsResponse(
        id=topic.id,
        title=topic.title,
        slug=topic.slug,
        description=topic.description,
        is_public=topic.is_public,
        author_id=topic.author_id,
        view_count=topic.view_count,
        created_at=topic.created_at,
        updated_at=topic.updated_at,
        published_at=topic.published_at,
        tags=[TagResp(id=t.id, name=t.name, slug=t.slug, created_at=t.created_at) for t in topic.tags],
        sections=[
            SectionResponse(
                id=s.id,
                topic_id=s.topic_id,
                section_type=s.section_type,
                content=s.content,
                section_metadata=parse_section_metadata(s.section_metadata),
                sort_order=s.sort_order,
                created_at=s.created_at,
                updated_at=s.updated_at
            )
            for s in topic.sections
        ],
        author={
            "id": topic.author.id,
            "username": topic.author.username,
            "email": topic.author.email
        }
    )


@router.post("", response_model=TopicWithSectionsResponse, status_code=status.HTTP_201_CREATED)
def create_topic(
    topic_data: TopicCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    topic = topic_service.create_topic(db, topic_data, current_user)
    
    from app.schemas.topic import SectionResponse, TagResponse as TagResp
    
    return TopicWithSectionsResponse(
        id=topic.id,
        title=topic.title,
        slug=topic.slug,
        description=topic.description,
        is_public=topic.is_public,
        author_id=topic.author_id,
        view_count=topic.view_count,
        created_at=topic.created_at,
        updated_at=topic.updated_at,
        published_at=topic.published_at,
        tags=[TagResp(id=t.id, name=t.name, slug=t.slug, created_at=t.created_at) for t in topic.tags],
        sections=[
            SectionResponse(
                id=s.id,
                topic_id=s.topic_id,
                section_type=s.section_type,
                content=s.content,
                section_metadata=parse_section_metadata(s.section_metadata),
                sort_order=s.sort_order,
                created_at=s.created_at,
                updated_at=s.updated_at
            )
            for s in topic.sections
        ],
        author={
            "id": topic.author.id,
            "username": topic.author.username,
            "email": topic.author.email
        }
    )


@router.put("/{topic_id}", response_model=TopicWithSectionsResponse)
def update_topic(
    topic_id: int,
    topic_data: TopicUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    topic = topic_service.update_topic(db, topic_id, topic_data, current_user)
    
    from app.schemas.topic import SectionResponse, TagResponse as TagResp
    
    return TopicWithSectionsResponse(
        id=topic.id,
        title=topic.title,
        slug=topic.slug,
        description=topic.description,
        is_public=topic.is_public,
        author_id=topic.author_id,
        view_count=topic.view_count,
        created_at=topic.created_at,
        updated_at=topic.updated_at,
        published_at=topic.published_at,
        tags=[TagResp(id=t.id, name=t.name, slug=t.slug, created_at=t.created_at) for t in topic.tags],
        sections=[
            SectionResponse(
                id=s.id,
                topic_id=s.topic_id,
                section_type=s.section_type,
                content=s.content,
                section_metadata=parse_section_metadata(s.section_metadata),
                sort_order=s.sort_order,
                created_at=s.created_at,
                updated_at=s.updated_at
            )
            for s in topic.sections
        ],
        author={
            "id": topic.author.id,
            "username": topic.author.username,
            "email": topic.author.email
        }
    )


@router.delete("/{topic_id}")
def delete_topic(
    topic_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return topic_service.delete_topic(db, topic_id, current_user)