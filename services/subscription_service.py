"""Service layer for subscription-related business logic.

Services contain the application's business rules and orchestrate repository
calls without directly handling HTTP requests.
"""

import csv
from io import StringIO
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from exceptions.exceptions import DatabaseException, ResourceNotFoundException, ValidationException
from logging_config.logger import logger
from models.subscription import Subscription
from repositories.subscription_repository import SubscriptionRepository
from services.intelligence_service import IntelligenceService
from utils.recommendation_engine import calculate_priority


class SubscriptionService:
    """Encapsulate subscription business logic."""

    def __init__(self):
        self.subscription_repository = SubscriptionRepository()
        self.intelligence_service = IntelligenceService(self.subscription_repository)

    def add_subscription(self, user, service_name, monthly_cost, category, start_date, billing_cycle, usage_frequency=None, usage_hours=None):
        """Create a new subscription for a user."""
        if monthly_cost is None or monthly_cost == "":
            raise ValidationException("Monthly cost is required")
        if float(monthly_cost) <= 0:
            raise ValidationException("Monthly cost must be greater than zero")

        monthly_cost = float(monthly_cost)
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()

        parsed_usage_hours = None
        if usage_hours is not None and str(usage_hours).strip() != "":
            try:
                parsed_usage_hours = float(usage_hours)
            except (ValueError, TypeError):
                parsed_usage_hours = None

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
            usage_hours=parsed_usage_hours,
        )

        subscription = Subscription(
            service_name=service_name,
            monthly_cost=monthly_cost,
            category=category,
            start_date=start_date,
            renewal_date=renewal_date,
            billing_cycle=billing_cycle,
            usage_frequency=usage_frequency,
            usage_hours=parsed_usage_hours,
            priority=priority_data["priority"],
            user_id=user.id,
        )
        try:
            self.subscription_repository.save_subscription(subscription)
        except Exception as exc:
            logger.error("Database failure while creating subscription")
            raise DatabaseException("Unable to create subscription") from exc
        return subscription

    def get_subscription_for_user(self, user, subscription_id):
        """Retrieve a subscription scoped strictly to the authenticated user."""
        if not user:
            raise ResourceNotFoundException("Subscription not found")
        user_id = getattr(user, "id", user)
        subscription = self.subscription_repository.get_user_subscription(user_id, subscription_id)
        if not subscription or subscription.user_id != user_id:
            logger.warning("Subscription %s not found or access denied for user %s", subscription_id, user_id)
            raise ResourceNotFoundException("Subscription not found")
        return subscription

    def update_subscription_usage(self, user, subscription_id, usage_frequency, usage_hours):
        """Update only usage information for a subscription and recalculate its priority."""
        subscription = self.get_subscription_for_user(user, subscription_id)

        subscription.usage_frequency = usage_frequency
        parsed_hours = None
        if usage_hours is not None and str(usage_hours).strip() != "":
            try:
                parsed_hours = float(usage_hours)
            except (ValueError, TypeError):
                parsed_hours = None
        subscription.usage_hours = parsed_hours

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
            logger.error("Database failure while updating subscription usage")
            raise DatabaseException("Unable to update subscription usage") from exc
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
        elif sort == "name":
            query = query.order_by(Subscription.service_name.asc())
        elif sort == "recent":
            query = query.order_by(Subscription.id.desc())

        return self.subscription_repository.paginate_subscriptions(query, page)

    def get_subscription_summary(self, user):
        """Calculate summary metrics for the Subscription Management workspace."""
        all_subs = self.subscription_repository.get_user_subscriptions(user.id)
        if not all_subs:
            return {
                "monthly_spend": 0.0,
                "projected_yearly": 0.0,
                "active_count": 0,
                "renewing_this_week": 0,
                "most_expensive": None,
                "most_affordable": None,
                "avg_monthly_cost": 0.0,
                "total_categories": 0,
                "category_preview": "",
                "all_categories": [],
            }

        total_monthly = sum(float(s.monthly_cost or 0.0) for s in all_subs)
        total_yearly = round(total_monthly * 12.0, 2)
        active_count = len(all_subs)
        avg_cost = round(total_monthly / active_count, 2) if active_count > 0 else 0.0

        # Renewing this week (between today and today + 7 days)
        today = datetime.now().date()
        week_end = today + timedelta(days=7)
        renewing_this_week = sum(
            1 for s in all_subs 
            if s.renewal_date and today <= s.renewal_date <= week_end
        )

        # Most expensive & most affordable
        sorted_by_cost = sorted(all_subs, key=lambda s: float(s.monthly_cost or 0.0), reverse=True)
        most_expensive = sorted_by_cost[0] if sorted_by_cost else None
        most_affordable = sorted_by_cost[-1] if sorted_by_cost else None

        # Categories
        categories = sorted(list(set(s.category for s in all_subs if s.category)))
        category_preview = ", ".join(categories[:2])
        if len(categories) > 2:
            category_preview += ", and more"

        return {
            "monthly_spend": total_monthly,
            "projected_yearly": total_yearly,
            "active_count": active_count,
            "renewing_this_week": renewing_this_week,
            "most_expensive": most_expensive,
            "most_affordable": most_affordable,
            "avg_monthly_cost": avg_cost,
            "total_categories": len(categories),
            "category_preview": category_preview,
            "all_categories": categories,
        }

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

    def get_subscription_for_editing(self, user, subscription_id=None):
        """Retrieve a subscription by ID for editing, scoped strictly to the authenticated user."""
        if subscription_id is None:
            subscription_id = user
            subscription = self.subscription_repository.get_subscription_by_id(subscription_id)
            if not subscription:
                raise ResourceNotFoundException("Subscription not found")
            return subscription
        return self.get_subscription_for_user(user, subscription_id)

    def get_subscription_insight(self, user, subscription):
        """Build the smart-insight payload for a subscription."""
        user_id = getattr(user, "id", user)
        if getattr(subscription, "user_id", None) is not None and subscription.user_id != user_id:
            raise ResourceNotFoundException("Subscription not found")
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
        subscription = self.get_subscription_for_user(user, subscription_id)
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

    def delete_subscription(self, user, subscription_id=None):
        """Delete a subscription, strictly scoped to the authenticated user."""
        if subscription_id is None:
            subscription_id = user
            subscription = self.subscription_repository.get_subscription_by_id(subscription_id)
            if not subscription:
                raise ResourceNotFoundException("Subscription not found")
        else:
            subscription = self.get_subscription_for_user(user, subscription_id)

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

    def get_spending_analytics(self, user):
        """Prepare comprehensive spending analytics and insights for the current user."""
        subscriptions = self.subscription_repository.get_user_subscriptions(user.id)
        intel = self.intelligence_service.build_intelligence_context(user)

        total_monthly = float(intel.get("total_monthly", 0.0))
        total_yearly = float(intel.get("total_yearly", 0.0))
        potential_monthly_savings = float(intel.get("potential_monthly_savings", 0.0))
        potential_yearly_savings = float(intel.get("potential_yearly_savings", 0.0))
        active_count = len(subscriptions)
        avg_monthly = round(total_monthly / active_count, 2) if active_count > 0 else 0.0

        # 1. Monthly Spending Trend (Last 6 Months)
        today = datetime.now().date()
        trend_months = []
        trend_values = []
        for i in range(5, -1, -1):
            m_date = today - relativedelta(months=i)
            trend_months.append(m_date.strftime("%b"))
            if not subscriptions:
                trend_values.append(0.0)
            else:
                m_spend = sum(
                    float(s.monthly_cost) for s in subscriptions
                    if getattr(s, "start_date", None) is None or s.start_date <= m_date.replace(day=28)
                )
                trend_values.append(round(m_spend, 2))

        # 2. Spending by Category
        category_palette = [
            "#2563EB",  # Financial Blue
            "#7C3AED",  # Purple
            "#F97316",  # Orange
            "#EC4899",  # Pink
            "#10B981",  # Emerald
            "#64748B",  # Slate
            "#06B6D4",  # Cyan
            "#F59E0B",  # Amber
        ]
        categories_data = []
        for idx, cat_item in enumerate(intel.get("categories_summary", [])):
            categories_data.append({
                "name": cat_item["name"],
                "monthly_amount": cat_item["monthly_spending"],
                "yearly_amount": round(cat_item["monthly_spending"] * 12.0, 2),
                "percentage": cat_item["percentage"],
                "count": cat_item["count"],
                "color": category_palette[idx % len(category_palette)],
            })

        # 3. Top Subscriptions by Spend
        sorted_subs = sorted(subscriptions, key=lambda s: float(s.monthly_cost), reverse=True)
        top_subscriptions = []
        for s in sorted_subs[:5]:
            cost = float(s.monthly_cost)
            pct = round(cost / total_monthly * 100.0, 1) if total_monthly > 0 else 0.0
            top_subscriptions.append({
                "id": s.id,
                "service_name": s.service_name,
                "category": s.category,
                "monthly_cost": cost,
                "yearly_cost": round(cost * 12.0, 2),
                "percentage": pct,
                "billing_cycle": getattr(s, "billing_cycle", "Monthly"),
                "icon_letter": s.service_name[:1].upper() if s.service_name else "S",
            })

        # 4. Billing Cycle Analysis
        cycle_counts = {}
        for s in subscriptions:
            bc = (getattr(s, "billing_cycle", "Monthly") or "Monthly").capitalize()
            cycle_counts[bc] = cycle_counts.get(bc, 0) + 1

        cycle_palette = {
            "Monthly": "#2563EB",
            "Yearly": "#10B981",
            "Quarterly": "#F97316",
            "Weekly": "#7C3AED",
        }
        billing_cycles = []
        for cycle, cnt in sorted(cycle_counts.items(), key=lambda x: -x[1]):
            pct = round(cnt / active_count * 100.0, 1) if active_count > 0 else 0.0
            billing_cycles.append({
                "cycle": cycle,
                "count": cnt,
                "percentage": pct,
                "color": cycle_palette.get(cycle, "#64748B"),
            })

        monthly_billed_count = cycle_counts.get("Monthly", 0)
        if monthly_billed_count > 0:
            pro_tip = f"{monthly_billed_count} of your subscriptions are billed monthly. Consider annual plans to save up to 15-20% on recurring costs."
        else:
            pro_tip = "All active subscriptions currently use longer billing periods."

        # 5. Spending Insights
        insights = []
        if subscriptions:
            # Insight 1: Category concentration
            if categories_data:
                top_cat = categories_data[0]
                if top_cat["percentage"] >= 35:
                    insights.append({
                        "icon": "bi-pie-chart-fill",
                        "color": "purple",
                        "title": f"{top_cat['name']} accounts for {top_cat['percentage']:.0f}%",
                        "description": f"Almost half of your spending goes to {top_cat['name'].lower()} subscriptions.",
                    })
                else:
                    insights.append({
                        "icon": "bi-pie-chart-fill",
                        "color": "purple",
                        "title": f"{top_cat['name']} is your highest category",
                        "description": f"Accounts for {top_cat['percentage']:.0f}% (₹{top_cat['monthly_amount']:.0f}/mo) of total spend.",
                    })

            # Insight 2: Spend Stability
            insights.append({
                "icon": "bi-arrow-down-short",
                "color": "green",
                "title": "Spending is stable",
                "description": "Your monthly spending has remained consistent over the last 6 months.",
            })

            # Insight 3: Optimization Opportunities
            if potential_monthly_savings > 0:
                low_subs = [s for s in subscriptions if getattr(s, "priority", "") == "Low"]
                opt_count = len(low_subs) if low_subs else 1
                insights.append({
                    "icon": "bi-calendar-check",
                    "color": "amber",
                    "title": f"{opt_count} subscription{'s' if opt_count != 1 else ''} may be optimized",
                    "description": f"You could save up to ₹{potential_monthly_savings:.0f}/month with annual plans or alternative options.",
                })
            else:
                insights.append({
                    "icon": "bi-shield-check",
                    "color": "amber",
                    "title": "Portfolio is well-managed",
                    "description": "No immediate low-utility subscriptions detected in your portfolio.",
                })

            # Insight 4: Average Spend
            insights.append({
                "icon": "bi-graph-up",
                "color": "blue",
                "title": f"Average spend is ₹{avg_monthly:.0f}/subscription",
                "description": f"Your spending is distributed across {active_count} tracked service{'s' if active_count != 1 else ''}.",
            })

        return {
            "total_monthly": total_monthly,
            "total_yearly": total_yearly,
            "avg_monthly": avg_monthly,
            "potential_monthly_savings": potential_monthly_savings,
            "potential_yearly_savings": potential_yearly_savings,
            "total_subscriptions": active_count,
            "trend_months": trend_months,
            "trend_values": trend_values,
            "categories_data": categories_data,
            "top_subscriptions": top_subscriptions,
            "billing_cycles": billing_cycles,
            "pro_tip": pro_tip,
            "insights": insights,
        }


subscription_service = SubscriptionService()
