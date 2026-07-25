"""Validation helpers for subscription-related requests.

This layer validates incoming request data before any business logic runs.
It is intentionally separate from the service layer so services can focus on
business rules rather than input checks.
"""

from datetime import datetime

from exceptions.exceptions import ValidationException


class SubscriptionValidator:
    """Validate subscription create and update payloads."""

    @staticmethod
    def validate_create(data):
        service_name = (data.get("service_name") or "").strip()
        monthly_cost = data.get("monthly_cost")
        category = (data.get("category") or "").strip()
        start_date = (data.get("start_date") or "").strip()
        billing_cycle = (data.get("billing_cycle") or "").strip()

        if not service_name:
            raise ValidationException("Service name is required")
        if monthly_cost is None or str(monthly_cost).strip() == "":
            raise ValidationException("Monthly cost is required")
        try:
            monthly_cost_value = float(monthly_cost)
        except (TypeError, ValueError) as exc:
            raise ValidationException("Monthly cost must be a valid number") from exc
        if monthly_cost_value <= 0:
            raise ValidationException("Monthly cost must be greater than zero")
        if not category:
            raise ValidationException("Category is required")
        if not start_date:
            raise ValidationException("Start date is required")
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError as exc:
            raise ValidationException("Start date must be valid") from exc
        if not billing_cycle:
            raise ValidationException("Billing cycle is required")

    @staticmethod
    def validate_update(data):
        if not data:
            return

        if "service_name" in data:
            service_name = (data.get("service_name") or "").strip()
            if not service_name:
                raise ValidationException("Service name is required")

        if "monthly_cost" in data and data.get("monthly_cost") is not None:
            monthly_cost = data.get("monthly_cost")
            if str(monthly_cost).strip() == "":
                raise ValidationException("Monthly cost is required")
            try:
                monthly_cost_value = float(monthly_cost)
            except (TypeError, ValueError) as exc:
                raise ValidationException("Monthly cost must be a valid number") from exc
            if monthly_cost_value <= 0:
                raise ValidationException("Monthly cost must be greater than zero")

        if "category" in data:
            category = (data.get("category") or "").strip()
            if not category:
                raise ValidationException("Category is required")

        if "start_date" in data and data.get("start_date") is not None:
            start_date = (data.get("start_date") or "").strip()
            if not start_date:
                raise ValidationException("Start date is required")
            try:
                datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError as exc:
                raise ValidationException("Start date must be valid") from exc

        if "billing_cycle" in data:
            billing_cycle = (data.get("billing_cycle") or "").strip()
            if not billing_cycle:
                raise ValidationException("Billing cycle is required")


subscription_validator = SubscriptionValidator()
