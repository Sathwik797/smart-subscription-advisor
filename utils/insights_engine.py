"""Insights engine: Formats evidence-based decisions into structured insight cards.

Phase 3.4B Architecture:
- Uses evaluate_subscription_evidence as the authoritative evaluation engine.
- Formats reasons, actions, and recommendations consistently across dashboard and API.
"""

from typing import Any, Dict

from utils.recommendation_engine import evaluate_subscription_evidence


def generate_insight(
    subscription: Any,
    financial_preference: str | None = None,
    total_monthly_spend: float = 0.0,
) -> Dict[str, Any]:
    """
    Generate a standardized insight card for a specific subscription.

    Returns:
    {
        "service": str,
        "reason": str,
        "recommendation": str,
        "color": "success" | "warning" | "danger" | "info",
        "action": "keep" | "review" | "rotate" | "cancel",
        "confidence": "high" | "moderate" | "low",
        "score": int (0-100),
        "priority": "High" | "Medium" | "Low"
    }
    """
    category = getattr(subscription, "category", "Other")
    monthly_cost = float(getattr(subscription, "monthly_cost", 0.0) or 0.0)
    usage_freq = getattr(subscription, "usage_frequency", None)
    usage_hrs = getattr(subscription, "usage_hours", None)

    # Calculate days until renewal if available
    days_left = None
    if getattr(subscription, "renewal_date", None):
        from datetime import date
        days_left = (subscription.renewal_date - date.today()).days

    evidence = evaluate_subscription_evidence(
        category=category,
        monthly_cost=monthly_cost,
        usage_frequency=usage_freq,
        usage_hours=usage_hrs,
        days_until_renewal=days_left,
        total_monthly_spend=total_monthly_spend,
        financial_preference=financial_preference,
    )

    service_name = getattr(subscription, "service_name", "Unknown")
    reason_str = " · ".join(evidence["reasons"]) if evidence["reasons"] else f"{category} subscription."

    return {
        "service": service_name,
        "reason": reason_str,
        "recommendation": evidence["recommendation"],
        "color": evidence["color"],
        "action": evidence["action"],
        "confidence": evidence["confidence"],
        "score": evidence["score"],
        "priority": evidence["priority"],
        "signals": evidence["signals"],
    }