"""Repository layer for subscription-related SQLAlchemy queries and writes."""

from database.db import db
from exceptions.exceptions import DatabaseException
from logging_config.logger import logger
from models.subscription import Subscription


class SubscriptionRepository:
    """Handle subscription database access."""

    @staticmethod
    def get_user_subscriptions(user_id):
        return Subscription.query.filter_by(user_id=user_id).all()

    @staticmethod
    def get_user_subscriptions_query(user_id):
        return Subscription.query.filter_by(user_id=user_id)

    @staticmethod
    def get_upcoming_renewals(user_id, start_date, end_date):
        return (
            Subscription.query.filter(
                Subscription.user_id == user_id,
                Subscription.renewal_date >= start_date,
                Subscription.renewal_date <= end_date,
            ).all()
        )

    @staticmethod
    def get_user_subscription(user_id, subscription_id):
        return Subscription.query.filter_by(id=subscription_id, user_id=user_id).first()

    @staticmethod
    def get_subscription_by_id(subscription_id):
        return db.session.get(Subscription, subscription_id)

    @staticmethod
    def get_subscription_or_404(subscription_id):
        return db.get_or_404(Subscription, subscription_id)

    @staticmethod
    def paginate_subscriptions(query, page):
        return query.paginate(page=page, per_page=10, error_out=False)

    @staticmethod
    def save_subscription(subscription):
        try:
            db.session.add(subscription)
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            logger.error("Database failure while saving subscription")
            raise DatabaseException("Unable to save subscription") from exc
        return subscription

    @staticmethod
    def update_subscription(subscription):
        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            logger.error("Database failure while updating subscription")
            raise DatabaseException("Unable to update subscription") from exc
        return subscription

    @staticmethod
    def delete_subscription(subscription):
        try:
            db.session.delete(subscription)
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            logger.error("Database failure while deleting subscription")
            raise DatabaseException("Unable to delete subscription") from exc
        return subscription
