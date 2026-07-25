"""Service layer for subscription-related business logic.

Services contain the application's business rules and orchestrate repository
calls without directly handling HTTP requests.
"""

import csv
from io import StringIO
from datetime import datetime

from dateutil.relativedelta import relativedelta

from exceptions.exceptions import DatabaseException, ResourceNotFoundException, ValidationException
from logging_config.logger import logger
from models.subscription import Subscription
from repositories.subscription_repository import SubscriptionRepository
from utils.recommendation_engine import calculate_priority


class SubscriptionService:
    """Encapsulate subscription business logic."""

    def __init__(self):
        self.subscription_repository = SubscriptionRepository()

    def add_subscription(self, user, service_name, monthly_cost, category, start_date, billing_cycle, usage_frequency, usage_hours):
        """Create a new subscription for a user."""
        if monthly_cost is None or monthly_cost == "":
            raise ValidationException("Monthly cost is required")
        if float(monthly_cost) <= 0:
            raise ValidationException("Monthly cost must be greater than zero")

        monthly_cost = float(monthly_cost)
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        usage_hours = float(usage_hours)

        if billing_cycle == "Monthly":
            renewal_date = start_date + relativedelta(months=1)
        else:
            renewal_date = start_date + relativedelta(years=1)

        priority_data = calculate_priority(
            occupation=user.occupation,
            financial_preference=user.financial_preference,
            category=category,
            monthly_cost=monthly_cost,
            usage_frequency=usage_frequency,
            usage_hours=usage_hours,
        )

        subscription = Subscription(
            service_name=service_name,
            monthly_cost=monthly_cost,
            category=category,
            start_date=start_date,
            renewal_date=renewal_date,
            billing_cycle=billing_cycle,
            usage_frequency=usage_frequency,
            usage_hours=usage_hours,
            priority=priority_data["priority"],
            user_id=user.id,
        )
        try:
            self.subscription_repository.save_subscription(subscription)
        except Exception as exc:
            logger.error("Database failure while creating subscription")
            raise DatabaseException("Unable to create subscription") from exc
        return subscription

    def get_user_subscriptions(self, user, search, category, sort, page):
        """Return filtered and paginated subscriptions for the current user."""
        query = self.subscription_repository.get_user_subscriptions_query(user.id)

        if search:
            query = query.filter(Subscription.service_name.ilike(f"%{search}%"))

        if category:
            query = query.filter_by(category=category)

        if sort == "renewal":
            query = query.order_by(Subscription.renewal_date.asc())
        elif sort == "cost":
            query = query.order_by(Subscription.monthly_cost.desc())

        return self.subscription_repository.paginate_subscriptions(query, page)

    def get_user_subscriptions_for_api(self, user):
        """Return a JSON-friendly list of subscriptions for JWT-based API responses."""
        subscriptions = self.subscription_repository.get_user_subscriptions(user.id)
        return [self.serialize_subscription(subscription) for subscription in subscriptions]

    def build_subscription_csv(self, user):
        """Create a CSV export for the current user's subscriptions."""
        subscriptions = self.subscription_repository.get_user_subscriptions(user.id)
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Service Name", "Monthly Cost", "Category", "Start Date", "Renewal Date"])

        for sub in subscriptions:
            writer.writerow([sub.service_name, sub.monthly_cost, sub.category, sub.start_date, sub.renewal_date])

        output.seek(0)
        return output.getvalue()

    def get_subscription_for_editing(self, subscription_id):
        """Retrieve a subscription by ID for editing."""
        return self.subscription_repository.get_subscription_or_404(subscription_id)

    def get_subscription_insight(self, user, subscription):
        """Build the smart-insight payload for a subscription."""
        return calculate_priority(
            occupation=user.occupation,
            financial_preference=user.financial_preference,
            category=subscription.category,
            monthly_cost=subscription.monthly_cost,
            usage_frequency=subscription.usage_frequency,
            usage_hours=subscription.usage_hours,
        )

    def update_subscription(self, user, subscription_id, service_name, monthly_cost, category, start_date, billing_cycle, usage_frequency, usage_hours):
        """Update a subscription and recalculate its priority."""
        subscription = self.subscription_repository.get_subscription_by_id(subscription_id)
        if not subscription:
            raise ResourceNotFoundException("Subscription not found")
        subscription.service_name = service_name
        subscription.monthly_cost = float(monthly_cost)
        subscription.category = category
        subscription.start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        subscription.billing_cycle = billing_cycle

        if subscription.billing_cycle == "Monthly":
            subscription.renewal_date = subscription.start_date + relativedelta(months=1)
        else:
            subscription.renewal_date = subscription.start_date + relativedelta(years=1)

        subscription.usage_frequency = usage_frequency
        subscription.usage_hours = float(usage_hours)

        priority_data = calculate_priority(
            occupation=user.occupation,
            financial_preference=user.financial_preference,
            category=subscription.category,
            monthly_cost=subscription.monthly_cost,
            usage_frequency=subscription.usage_frequency,
            usage_hours=subscription.usage_hours,
        )
        subscription.priority = priority_data["priority"]
        try:
            self.subscription_repository.update_subscription(subscription)
        except Exception as exc:
            logger.error("Database failure while updating subscription")
            raise DatabaseException("Unable to update subscription") from exc
        return subscription

    def delete_subscription(self, subscription_id):
        """Delete a subscription by ID."""
        subscription = self.subscription_repository.get_subscription_by_id(subscription_id)
        if not subscription:
            raise ResourceNotFoundException("Subscription not found")
        try:
            self.subscription_repository.delete_subscription(subscription)
        except Exception as exc:
            logger.error("Database failure while deleting subscription")
            raise DatabaseException("Unable to delete subscription") from exc
        return subscription

    def serialize_subscription(self, subscription):
        """Convert a Subscription model into a JSON-safe dictionary."""
        return {
            "id": subscription.id,
            "service_name": subscription.service_name,
            "monthly_cost": subscription.monthly_cost,
            "category": subscription.category,
            "start_date": subscription.start_date.strftime("%Y-%m-%d") if subscription.start_date else None,
            "renewal_date": subscription.renewal_date.strftime("%Y-%m-%d") if subscription.renewal_date else None,
            "billing_cycle": subscription.billing_cycle,
            "usage_frequency": subscription.usage_frequency,
            "usage_hours": subscription.usage_hours,
            "priority": subscription.priority,
            "user_id": subscription.user_id,
        }


subscription_service = SubscriptionService()
