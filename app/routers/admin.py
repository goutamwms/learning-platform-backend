from fastapi import APIRouter, Depends, status
from app.services.analytics_service import analytics_service
from app.core.dependencies import require_admin
from app.models.user import User
from pydantic import BaseModel


router = APIRouter(prefix="/api/admin", tags=["Admin"])


class DashboardStats(BaseModel):
    total_users: int
    total_topics: int
    public_topics: int
    private_topics: int
    total_views: int
    recent_users: list
    recent_topics: list


class ActivityStats(BaseModel):
    days: int
    logins: int
    signups: int
    topics_created: int


class RateLimitStats(BaseModel):
    total_requests: int
    unique_ips: int
    top_ips: list


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(
    current_user: User = Depends(require_admin)
):
    return analytics_service.get_dashboard_stats()


@router.get("/activity", response_model=ActivityStats)
def get_activity_stats(
    days: int = 7,
    current_user: User = Depends(require_admin)
):
    return analytics_service.get_activity_stats(days)


@router.get("/rate-limits", response_model=RateLimitStats)
def get_rate_limit_stats(
    current_user: User = Depends(require_admin)
):
    return analytics_service.get_rate_limit_stats()