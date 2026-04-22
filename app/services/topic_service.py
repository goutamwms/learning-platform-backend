from datetime import datetime
from typing import Optional, List
import re
import json
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session, joinedload, selectinload
from app.models.topic import Topic, TopicSection, Tag
from app.models.user import User
from app.schemas.topic import (
    TopicCreate,
    TopicUpdate,
    TopicResponse,
    TopicWithSectionsResponse,
    TopicListResponse,
    TopicListResponseWrapper,
    TopicSectionBlock,
)
from app.core.dependencies import get_current_user
from app.models.user import User as UserModel
from fastapi import HTTPException, status, Query


class TopicService:
    def _generate_slug(self, title: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower().strip())
        slug = re.sub(r"-+", "-", slug).strip("-")
        return slug

    def _get_or_create_tags(self, db: Session, tag_names: List[str]) -> List[Tag]:
        tags = []
        for name in tag_names:
            name = name.strip()
            if not name:
                continue
            slug = re.sub(r"[^a-z0-9]+", "-", name.lower().strip())

            tag = db.query(Tag).filter(Tag.slug == slug).first()
            if not tag:
                tag = Tag(name=name, slug=slug)
                db.add(tag)
            tags.append(tag)

        db.commit()
        for tag in tags:
            db.refresh(tag)
        return tags

    def create_topic(
        self, db: Session, topic_data: TopicCreate, current_user: UserModel
    ) -> Topic:
        slug = self._generate_slug(topic_data.title)

        existing = db.query(Topic).filter(Topic.slug == slug).first()
        if existing:
            slug = f"{slug}-{datetime.utcnow().timestamp()}"

        topic = Topic(
            title=topic_data.title,
            slug=slug,
            description=topic_data.description,
            is_public=topic_data.is_public,
            author_id=current_user.id,
        )

        if topic_data.tags:
            topic.tags = self._get_or_create_tags(db, topic_data.tags)

        db.add(topic)
        db.flush()

        if topic_data.sections:
            for section_data in topic_data.sections:
                section = TopicSection(
                    topic_id=topic.id,
                    section_type=section_data.type,
                    content=section_data.content,
                    section_metadata=(
                        json.dumps(section_data.section_metadata)
                        if section_data.section_metadata
                        else None
                    ),
                    sort_order=section_data.order,
                )
                db.add(section)

        db.commit()

        from sqlalchemy.orm import joinedload

        topic = (
            db.query(Topic)
            .options(joinedload(Topic.author))
            .filter(Topic.id == topic.id)
            .first()
        )
        return topic

    def update_topic(
        self,
        db: Session,
        topic_id: int,
        topic_data: TopicUpdate,
        current_user: UserModel,
    ) -> Topic:
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        if topic.author_id != current_user.id and current_user.role.value != "admin":
            raise HTTPException(
                status_code=403, detail="Not authorized to update this topic"
            )

        if topic_data.title is not None:
            topic.title = topic_data.title
            topic.slug = self._generate_slug(topic_data.title)

        if topic_data.description is not None:
            topic.description = topic_data.description

        if topic_data.is_public is not None:
            topic.is_public = topic_data.is_public
            if topic_data.is_public and not topic.published_at:
                topic.published_at = datetime.utcnow()

        if topic_data.tags is not None:
            topic.tags = self._get_or_create_tags(db, topic_data.tags)

        if topic_data.sections is not None:
            db.query(TopicSection).filter(TopicSection.topic_id == topic_id).delete()

            for section_data in topic_data.sections:
                section = TopicSection(
                    topic_id=topic.id,
                    section_type=section_data.type,
                    content=section_data.content,
                    section_metadata=(
                        json.dumps(section_data.section_metadata)
                        if section_data.section_metadata
                        else None
                    ),
                    sort_order=section_data.order,
                )
                db.add(section)

        db.commit()

        topic = (
            db.query(Topic)
            .options(joinedload(Topic.author))
            .filter(Topic.id == topic_id)
            .first()
        )
        return topic

    def delete_topic(self, db: Session, topic_id: int, current_user: UserModel) -> dict:
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        if topic.author_id != current_user.id and current_user.role.value != "admin":
            raise HTTPException(
                status_code=403, detail="Not authorized to delete this topic"
            )

        db.delete(topic)
        db.commit()
        return {"message": "Topic deleted"}

    def get_topic(
        self, db: Session, topic_id: int, current_user: Optional[UserModel] = None
    ) -> Topic:
        topic = (
            db.query(Topic)
            .options(joinedload(Topic.author))
            .filter(Topic.id == topic_id)
            .first()
        )
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        if not topic.is_public:
            if not current_user or (
                current_user.id != topic.author_id
                and current_user.role.value != "admin"
            ):
                raise HTTPException(status_code=403, detail="Access denied")

        topic.view_count += 1
        db.commit()

        return topic

    def get_topics(
        self,
        db: Session,
        search: Optional[str] = None,
        starts_with: Optional[str] = None,
        tags: Optional[List[str]] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
        current_user: Optional[UserModel] = None,
    ) -> TopicListResponseWrapper:
        query = db.query(Topic).options(selectinload(Topic.author))

        if current_user:
            if current_user.role.value == "admin":
                pass
            else:
                query = query.filter(
                    or_(Topic.is_public == True, Topic.author_id == current_user.id)
                )
        else:
            query = query.filter(Topic.is_public == True)

        if search or starts_with:
            if search and starts_with:
                starts_filter = f"{starts_with}%"
                search_filter = f"%{search}%"
                query = (
                    query.outerjoin(Topic.sections)
                    .filter(
                        and_(
                            Topic.title.ilike(starts_filter),
                            or_(
                                Topic.title.ilike(search_filter),
                                Topic.description.ilike(search_filter),
                                TopicSection.content.ilike(search_filter),
                            )
                        )
                    )
                    .distinct()
                )
            elif starts_with:
                search_filter = f"{starts_with}%"
                query = query.filter(Topic.title.ilike(search_filter))
            elif search:
                search_filter = f"%{search}%"
                query = (
                    query.outerjoin(Topic.sections)
                    .filter(
                        or_(
                            Topic.title.ilike(search_filter),
                            Topic.description.ilike(search_filter),
                            TopicSection.content.ilike(search_filter),
                        )
                    )
                    .distinct()
                )

        if tags:
            for tag in tags:
                # Use any() to filter topics that have at least one matching tag
                query = query.filter(Topic.tags.any(Tag.slug == tag))
                # query = query.join(Topic.tags).filter(Tag.slug.in_(tags))

        allowed_sort_fields = {
            "created_at": Topic.created_at,
            "updated_at": Topic.updated_at,
            "title": Topic.title,
            "view_count": Topic.view_count,
        }

        sort_column = allowed_sort_fields.get(sort_by, Topic.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        total = query.count()
        total_pages = (total + page_size - 1) // page_size

        topics = query.offset((page - 1) * page_size).limit(page_size).all()

        all_tags = db.query(Tag).all()

        items = []
        for topic in topics:
            items.append(
                TopicListResponse(
                    id=topic.id,
                    title=topic.title,
                    slug=topic.slug,
                    description=topic.description,
                    is_public=topic.is_public,
                    author_id=topic.author_id,
                    author_username=(
                        topic.author.username if topic.author else "Unknown"
                    ),
                    view_count=topic.view_count,
                    created_at=topic.created_at,
                    updated_at=topic.updated_at,
                    published_at=topic.published_at,
                    tag_names=[t.name for t in topic.tags],
                )
            )

        return TopicListResponseWrapper(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            tags=[t.name for t in all_tags],
        )

    def get_user_topics(
        self, db: Session, user_id: int, current_user: UserModel
    ) -> List[Topic]:
        if current_user.id != user_id and current_user.role.value != "admin":
            raise HTTPException(status_code=403, detail="Not authorized")

        return (
            db.query(Topic)
            .filter(Topic.author_id == user_id)
            .order_by(Topic.created_at.desc())
            .all()
        )


topic_service = TopicService()
