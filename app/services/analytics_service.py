from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models.topic import Topic
from app.models.user import User
from app.models.audit import AuditLog, RateLimitLog
from app.models.audit import RateLimitLog as RateLimitModel


class AnalyticsService:
    def get_dashboard_stats(self) -> dict:
        db = SessionLocal()
        try:
            total_users = db.query(User).count()
            total_topics = db.query(Topic).count()
            public_topics = db.query(Topic).filter(Topic.is_public == True).count()
            private_topics = db.query(Topic).filter(Topic.is_public == False).count()
            total_views = db.query(func.sum(Topic.view_count)).scalar() or 0
            
            recent_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
            recent_topics = db.query(Topic).order_by(Topic.created_at.desc()).limit(5).all()
            
            return {
                "total_users": total_users,
                "total_topics": total_topics,
                "public_topics": public_topics,
                "private_topics": private_topics,
                "total_views": total_views,
                "recent_users": [
                    {"id": u.id, "username": u.username, "email": u.email, "role": u.role.value, "created_at": u.created_at}
                    for u in recent_users
                ],
                "recent_topics": [
                    {"id": t.id, "title": t.title, "author": t.author.username, "is_public": t.is_public, "view_count": t.view_count}
                    for t in recent_topics
                ]
            }
        finally:
            db.close()

    def get_activity_stats(self, days: int = 7) -> dict:
        db = SessionLocal()
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            logins = db.query(AuditLog).filter(
                AuditLog.action == "login",
                AuditLog.timestamp >= start_date
            ).count()
            
            signups = db.query(AuditLog).filter(
                AuditLog.action == "signup",
                AuditLog.timestamp >= start_date
            ).count()
            
            topics_created = db.query(Topic).filter(
                Topic.created_at >= start_date
            ).count()
            
            return {
                "days": days,
                "logins": logins,
                "signups": signups,
                "topics_created": topics_created
            }
        finally:
            db.close()

    def get_rate_limit_stats(self) -> dict:
        db = SessionLocal()
        try:
            recent_logs = db.query(RateLimitLog).order_by(RateLimitLog.timestamp.desc()).limit(100).all()
            
            ip_counts = {}
            for log in recent_logs:
                ip_counts[log.ip_address] = ip_counts.get(log.ip_address, 0) + 1
            
            return {
                "total_requests": len(recent_logs),
                "unique_ips": len(ip_counts),
                "top_ips": sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            }
        finally:
            db.close()


analytics_service = AnalyticsService()