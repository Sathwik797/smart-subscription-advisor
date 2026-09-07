"""Service layer for subscription-related business logic.

Services contain the application's business rules and orchestrate repository
calls without directly handling HTTP requests.
"""

import calendar
import csv
from datetime import datetime, timedelta
from decimal import Decimal
from io import StringIO

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
        """Create a new subscription for a user with precise Decimal storage and billing-cycle awareness."""
        if monthly_cost is None or monthly_cost == "":
            raise ValidationException("Monthly cost is required")
        try:
            monthly_cost_dec = Decimal(str(monthly_cost))
        except (ValueError, TypeError) as exc:
            raise ValidationException("Monthly cost must be a valid number") from exc
        if monthly_cost_dec <= Decimal("0.00"):
            raise ValidationException("Monthly cost must be greater than zero")

        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()

        parsed_usage_hours = None
        if usage_hours is not None and str(usage_hours).strip() != "":
            try:
                parsed_usage_hours = float(usage_hours)
            except (ValueError, TypeError):
                parsed_usage_hours = None

        cycle = (billing_cycle or "Monthly").strip().capitalize()
        if cycle == "Monthly":
            renewal_date = start_date + relativedelta(months=1)
            effective_monthly = monthly_cost_dec
        elif cycle == "Yearly":
            renewal_date = start_date + relativedelta(years=1)
            effective_monthly = monthly_cost_dec / Decimal("12")
        elif cycle == "Quarterly":
            renewal_date = start_date + relativedelta(months=3)
            effective_monthly = monthly_cost_dec / Decimal("3")
        elif cycle == "Weekly":
            renewal_date = start_date + relativedelta(weeks=1)
            effective_monthly = (monthly_cost_dec * Decimal("52")) / Decimal("12")
        else:
            renewal_date = start_date + relativedelta(months=1)
            effective_monthly = monthly_cost_dec

        priority_data = calculate_priority(
            occupation=user.occupation,
            financial_preference=user.financial_preference,
            category=category,
            monthly_cost=float(effective_monthly),
            usage_frequency=usage_frequency,
            usage_hours=parsed_usage_hours,
        )

        subscription = Subscription(
            service_name=service_name,
            monthly_cost=monthly_cost_dec,
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
            monthly_cost=float(subscription.monthly_equivalent),
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

        total_monthly_dec = sum(s.monthly_equivalent for s in all_subs)
        total_yearly_dec = sum(s.yearly_equivalent for s in all_subs)
        active_count = len(all_subs)
        avg_cost_dec = (total_monthly_dec / Decimal(str(active_count))) if active_count > 0 else Decimal("0.00")

        # Renewing this week (between today and today + 7 days)
        today = datetime.now().date()
        week_end = today + timedelta(days=7)
        renewing_this_week = sum(
            1 for s in all_subs 
            if s.renewal_date and today <= s.renewal_date <= week_end
        )

        # Most expensive & most affordable by monthly equivalent
        sorted_by_cost = sorted(all_subs, key=lambda s: s.monthly_equivalent, reverse=True)
        most_expensive = sorted_by_cost[0] if sorted_by_cost else None
        most_affordable = sorted_by_cost[-1] if sorted_by_cost else None

        # Categories
        categories = sorted(list(set(s.category for s in all_subs if s.category)))
        category_preview = ", ".join(categories[:2])
        if len(categories) > 2:
            category_preview += ", and more"

        return {
            "monthly_spend": float(round(total_monthly_dec, 2)),
            "projected_yearly": float(round(total_yearly_dec, 2)),
            "active_count": active_count,
            "renewing_this_week": renewing_this_week,
            "most_expensive": most_expensive,
            "most_affordable": most_affordable,
            "avg_monthly_cost": float(round(avg_cost_dec, 2)),
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
            monthly_cost=float(subscription.monthly_equivalent),
            usage_frequency=subscription.usage_frequency,
            usage_hours=subscription.usage_hours,
        )

    def update_subscription(self, user, subscription_id, service_name, monthly_cost, category, start_date, billing_cycle, usage_frequency, usage_hours):
        """Update a subscription and recalculate its priority."""
        if monthly_cost is None or monthly_cost == "":
            raise ValidationException("Monthly cost is required")
        try:
            monthly_cost_dec = Decimal(str(monthly_cost))
        except (ValueError, TypeError) as exc:
            raise ValidationException("Monthly cost must be a valid number") from exc
        if monthly_cost_dec <= Decimal("0.00"):
            raise ValidationException("Monthly cost must be greater than zero")

        subscription = self.get_subscription_for_user(user, subscription_id)
        subscription.service_name = service_name
        subscription.monthly_cost = monthly_cost_dec
        subscription.category = category
        subscription.start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        subscription.billing_cycle = billing_cycle

        cycle = (billing_cycle or "Monthly").strip().capitalize()
        if cycle == "Monthly":
            subscription.renewal_date = subscription.start_date + relativedelta(months=1)
            effective_monthly = monthly_cost_dec
        elif cycle == "Yearly":
            subscription.renewal_date = subscription.start_date + relativedelta(years=1)
            effective_monthly = monthly_cost_dec / Decimal("12")
        elif cycle == "Quarterly":
            subscription.renewal_date = subscription.start_date + relativedelta(months=3)
            effective_monthly = monthly_cost_dec / Decimal("3")
        elif cycle == "Weekly":
            subscription.renewal_date = subscription.start_date + relativedelta(weeks=1)
            effective_monthly = (monthly_cost_dec * Decimal("52")) / Decimal("12")
        else:
            subscription.renewal_date = subscription.start_date + relativedelta(months=1)
            effective_monthly = monthly_cost_dec

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
            monthly_cost=float(effective_monthly),
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
            "monthly_cost": float(subscription.monthly_cost) if subscription.monthly_cost is not None else 0.0,
            "monthly_equivalent": float(round(subscription.monthly_equivalent, 2)) if subscription.monthly_equivalent is not None else 0.0,
            "yearly_equivalent": float(round(subscription.yearly_equivalent, 2)) if subscription.yearly_equivalent is not None else 0.0,
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
        intel = self.intelligence_service.build_intelligence_context(user, subscriptions=subscriptions)

        fin_summary = intel.get("financial_summary", {})
        total_monthly = float(fin_summary.get("monthly_spending", intel.get("total_monthly", 0.0)))
        total_yearly = float(fin_summary.get("yearly_projection", intel.get("total_yearly", 0.0)))
        potential_monthly_savings = float(fin_summary.get("potential_monthly_savings", intel.get("potential_monthly_savings", 0.0)))
        potential_yearly_savings = float(fin_summary.get("potential_yearly_savings", intel.get("potential_yearly_savings", 0.0)))
        active_count = len(subscriptions)
        avg_monthly = round(total_monthly / active_count, 2) if active_count > 0 else 0.0

        # 1. Projected Billing Schedule (Next 6 Months of actual projected payment events based on cycle & renewal date)
        today = datetime.now().date()
        schedule_months = []
        schedule_values = []
        for i in range(6):
            target_date = today + relativedelta(months=i)
            schedule_months.append(target_date.strftime("%b"))
            if not subscriptions:
                schedule_values.append(0.0)
            else:
                target_year = target_date.year
                target_month = target_date.month
                month_payment_sum = Decimal("0.00")
                for s in subscriptions:
                    cycle = (getattr(s, "billing_cycle", "Monthly") or "Monthly").strip().capitalize()
                    cost = getattr(s, "cost_decimal", Decimal(str(s.monthly_cost or "0.00")))
                    ren_date = getattr(s, "renewal_date", None) or getattr(s, "start_date", None) or today

                    if cycle == "Monthly":
                        month_payment_sum += cost
                    elif cycle == "Yearly":
                        if ren_date.month == target_month:
                            month_payment_sum += cost
                    elif cycle == "Quarterly":
                        month_diff = (target_year - ren_date.year) * 12 + (target_month - ren_date.month)
                        if month_diff % 3 == 0:
                            month_payment_sum += cost
                    elif cycle == "Weekly":
                        num_days = calendar.monthrange(target_year, target_month)[1]
                        weekday_count = sum(
                            1 for d in range(1, num_days + 1)
                            if datetime(target_year, target_month, d).weekday() == ren_date.weekday()
                        )
                        month_payment_sum += cost * Decimal(str(weekday_count))
                    else:
                        month_payment_sum += cost

                schedule_values.append(float(round(month_payment_sum, 2)))

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
        categories_source = intel.get("categories", intel.get("categories_summary", []))
        for idx, cat_item in enumerate(categories_source):
            categories_data.append({
                "name": cat_item["name"],
                "monthly_amount": cat_item["monthly_spending"],
                "yearly_amount": round(cat_item["monthly_spending"] * 12.0, 2),
                "percentage": cat_item["percentage"],
                "count": cat_item["count"],
                "color": category_palette[idx % len(category_palette)],
            })

        # 3. Top Subscriptions by Spend (using monthly equivalent)
        sorted_subs = sorted(subscriptions, key=lambda s: s.monthly_equivalent, reverse=True)
        top_subscriptions = []
        for s in sorted_subs[:5]:
            m_equiv = float(round(s.monthly_equivalent, 2))
            y_equiv = float(round(s.yearly_equivalent, 2))
            pct = round(m_equiv / total_monthly * 100.0, 1) if total_monthly > 0 else 0.0
            top_subscriptions.append({
                "id": s.id,
                "service_name": s.service_name,
                "category": s.category,
                "monthly_cost": float(s.monthly_cost),
                "monthly_equivalent": m_equiv,
                "yearly_cost": y_equiv,
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

        # 5. Data-Driven Spending Insights
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
                        "description": f"Over a third of your recurring spend goes to {top_cat['name'].lower()} subscriptions.",
                    })
                else:
                    insights.append({
                        "icon": "bi-pie-chart-fill",
                        "color": "purple",
                        "title": f"{top_cat['name']} is your highest category",
                        "description": f"Accounts for {top_cat['percentage']:.0f}% (₹{top_cat['monthly_amount']:,.0f}/mo) of total spend.",
                    })

            # Insight 2: Largest Single Commitment
            if top_subscriptions:
                top_sub = top_subscriptions[0]
                insights.append({
                    "icon": "bi-award-fill",
                    "color": "blue",
                    "title": f"{top_sub['service_name']} is your largest service",
                    "description": f"Accounts for {top_sub['percentage']:.0f}% of recurring commitments (₹{top_sub['monthly_equivalent']:,.0f}/mo).",
                })

            # Insight 3: Upcoming Renewals (Next 7 Days)
            next_7_days = today + timedelta(days=7)
            renewing_soon = [s for s in subscriptions if s.renewal_date and today <= s.renewal_date <= next_7_days]
            if renewing_soon:
                soon_total = sum(float(s.monthly_cost) for s in renewing_soon)
                insights.append({
                    "icon": "bi-calendar-event-fill",
                    "color": "amber",
                    "title": f"{len(renewing_soon)} renewal{'s' if len(renewing_soon) != 1 else ''} in next 7 days",
                    "description": f"₹{soon_total:,.0f} due across upcoming scheduled renewals.",
                })
            else:
                insights.append({
                    "icon": "bi-shield-check",
                    "color": "green",
                    "title": "No renewals this week",
                    "description": "All scheduled subscription renewals are outside the next 7 days.",
                })

            # Insight 4: Optimization Opportunities
            if potential_monthly_savings > 0:
                low_subs = [s for s in subscriptions if getattr(s, "priority", "") == "Low"]
                opt_count = len(low_subs) if low_subs else 1
                insights.append({
                    "icon": "bi-piggy-bank-fill",
                    "color": "amber",
                    "title": f"₹{potential_monthly_savings:,.0f}/mo potential savings",
                    "description": f"Identified across {opt_count} low-utilization or optimizable service{'s' if opt_count != 1 else ''}.",
                })
            else:
                insights.append({
                    "icon": "bi-check2-circle",
                    "color": "emerald",
                    "title": "Portfolio is well-managed",
                    "description": "No immediate low-utility subscriptions detected in your portfolio.",
                })

        return {
            "summary": {
                "total_monthly": total_monthly,
                "total_yearly": total_yearly,
                "avg_monthly": avg_monthly,
                "potential_monthly_savings": potential_monthly_savings,
                "potential_yearly_savings": potential_yearly_savings,
                "active_subscriptions": active_count,
            },
            "categories": categories_data,
            "top_subscriptions": top_subscriptions,
            "billing_cycles": billing_cycles,
            "spending_schedule": {
                "months": schedule_months,
                "values": schedule_values,
                "label": "Projected Billing Schedule",
            },
            "pro_tip": pro_tip,
            "insights": insights,
            # Backward-compatible aliases for templates and JS consumption
            "total_monthly": total_monthly,
            "total_yearly": total_yearly,
            "avg_monthly": avg_monthly,
            "potential_monthly_savings": potential_monthly_savings,
            "potential_yearly_savings": potential_yearly_savings,
            "total_subscriptions": active_count,
            "trend_months": schedule_months,
            "trend_values": schedule_values,
            "categories_data": categories_data,
        }


subscription_service = SubscriptionService()
