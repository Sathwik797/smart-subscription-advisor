"""Recommendation engine: Multi-dimensional evidence evaluation for subscriptions.

Phase 3.4B Architecture:
- Evaluates multi-dimensional evidence (utilization, financial impact, category context, confidence, preference).
- Avoids treating estimated usage hours as scientific telemetry.
- Replaces raw 'Rarely -> Cancel' jumps with confidence-weighted review/cancel decisions.
- Integrates user financial preference (Money Saver vs Balanced vs Premium/Convenience).
- Acts as the single authoritative decision model consumed across insights and intelligence layers.
"""

from typing import Any, Dict, List, Optional

INTERACTIVE_CATEGORIES = {"Entertainment", "Music", "Gaming"}
UTILITY_CATEGORIES = {"Cloud Storage", "Productivity", "Education"}


def evaluate_subscription_evidence(
    category: str = "Other",
    monthly_cost: float = 0.0,
    usage_frequency: str | None = None,
    usage_hours: float | None = None,
    days_until_renewal: int | None = None,
    total_monthly_spend: float = 0.0,
    financial_preference: str | None = "Balanced",
) -> Dict[str, Any]:
    """
    Evaluate multidimensional evidence for a single subscription.

    Returns an internal decision dictionary:
    {
        "score": int (0-100),
        "priority": "High" | "Medium" | "Low",
        "action": "keep" | "review" | "rotate" | "cancel",
        "color": "success" | "warning" | "danger" | "info",
        "confidence": "high" | "moderate" | "low",
        "category_type": "interactive" | "utility" | "general",
        "reasons": List[str],
        "signals": List[str],
        "recommendation": str
    }
    """
    monthly_cost = max(0.0, float(monthly_cost or 0.0))
    usage_freq = usage_frequency or "Monthly"
    has_hours_provided = usage_hours is not None and usage_hours > 0
    raw_hours = float(usage_hours) if has_hours_provided else 0.0
    pref = financial_preference or "Balanced"

    # 1. Category Classification
    if category in INTERACTIVE_CATEGORIES:
        category_type = "interactive"
    elif category in UTILITY_CATEGORIES:
        category_type = "utility"
    else:
        category_type = "general"

    # 2. Daily active hours estimation
    if usage_freq == "Daily":
        daily_hours = raw_hours if has_hours_provided else 1.0
    elif usage_freq == "Weekly":
        daily_hours = (raw_hours / 7.0) if has_hours_provided else (1.0 / 7.0)
    elif usage_freq == "Monthly":
        daily_hours = (raw_hours / 30.0) if has_hours_provided else (1.0 / 30.0)
    else:  # Rarely
        daily_hours = (raw_hours / 30.0) if has_hours_provided else 0.0

    # 3. Evidence Confidence
    # Distinguish estimated user inputs from strong reported engagement
    if has_hours_provided and usage_frequency is not None:
        confidence = "high"
    elif usage_frequency is not None:
        confidence = "moderate"
    else:
        confidence = "low"

    # 4. Multi-dimensional Scoring
    score = 0
    reasons: List[str] = []
    signals: List[str] = []

    if category_type == "interactive":
        # Interactive media (Streaming, Gaming, Music)
        if usage_freq == "Daily":
            score += 45
            if daily_hours >= 2.0:
                score += 35
                reasons.append(f"Actively used (~{raw_hours:.1f} hrs/day).")
            elif daily_hours >= 0.5:
                score += 25
                reasons.append(f"Regularly used (~{raw_hours:.1f} hrs/day).")
            else:
                score += 15
                reasons.append("Daily access with light screen time.")
        elif usage_freq == "Weekly":
            score += 30
            if daily_hours >= 0.3:
                score += 20
                reasons.append(f"Weekly entertainment (~{raw_hours:.1f} hrs/week).")
            else:
                score += 10
                reasons.append("Occasional weekly entertainment.")
        elif usage_freq == "Monthly":
            score += 15
            reasons.append("Accessed on a monthly basis.")
            signals.append("moderate_utilization")
        else:  # Rarely
            score += 0
            signals.append("low_utilization")
            reasons.append("Low engagement reported.")

        # Cost-per-hour efficiency check for interactive media
        if daily_hours > 0:
            cph = monthly_cost / (daily_hours * 30.0)
            if cph <= 15.0:
                score += 20
                reasons.append(f"High value-for-money (₹{cph:.1f}/hr).")
            elif cph <= 40.0:
                score += 10
            elif cph > 80.0:
                signals.append("high_cost_per_hour")
                reasons.append(f"High cost per active hour (₹{cph:.1f}/hr).")

    elif category_type == "utility":
        # Passive / Utility infrastructure (Cloud Storage, Productivity, Work Tools)
        # Background tools deliver continuous utility without requiring screen time
        score += 50
        reasons.append(f"{category} provides continuous background utility.")

        if usage_freq == "Daily":
            score += 35
            reasons.append(f"Core daily tool ({raw_hours:.1f} hrs/day)." if has_hours_provided else "Core daily tool.")
        elif usage_freq == "Weekly":
            score += 25
            reasons.append("Regularly utilized work/utility service.")
        elif usage_freq == "Monthly":
            score += 10
            reasons.append("Periodic background maintenance or sync.")
        else:  # Rarely
            score -= 5
            signals.append("passive_infrequent_access")
            reasons.append("Infrequently accessed background service; confirm active storage/account requirement.")

        # High usage hours bonus for work tools (e.g. AWS, IDEs, Notion)
        if daily_hours >= 2.0:
            score += 15

    else:
        # General / Other category (Gym, offline memberships, general services)
        score += 45
        if usage_freq == "Daily":
            score += 40
            reasons.append("Actively utilized recurring service.")
        elif usage_freq == "Weekly":
            score += 25
            reasons.append("Regularly used service.")
        elif usage_freq == "Monthly":
            score += 10
            reasons.append("Monthly recurring service.")
        else:  # Rarely
            score -= 25
            signals.append("low_utilization")
            reasons.append("Infrequently utilized service.")

    # 5. Financial Impact & Portfolio Share
    if total_monthly_spend > 0:
        portfolio_share = (monthly_cost / total_monthly_spend) * 100.0
        if portfolio_share >= 35.0 and total_monthly_spend >= 1000.0:
            signals.append("high_portfolio_share")
            reasons.append(f"Represents {portfolio_share:.0f}% of total subscription budget.")

    # 6. Renewal Proximity Signal
    if days_until_renewal is not None and 0 <= days_until_renewal <= 7:
        signals.append("imminent_renewal")
        if days_until_renewal <= 1:
            signals.append("renewal_tomorrow")

    # 7. Financial Preference Influence
    # - "Money Saver": increases scrutiny on underutilized services
    # - "Premium" / "Convenience": values continuity, avoids eager cancellation advice
    if pref == "Money Saver":
        if "low_utilization" in signals:
            score -= 10
            reasons.append("Optimization prioritized under Money Saver profile.")
    elif pref in ("Premium", "Convenience"):
        score += 5

    # Clamp score
    final_score = max(0, min(100, score))

    # 8. Priority & Action Determination
    if final_score >= 70:
        priority = "High"
        action = "keep"
        color = "success"
        recommendation = "Keep this subscription. It delivers reliable value."
    elif final_score >= 40:
        priority = "Medium"
        action = "review"
        color = "warning"
        recommendation = "Review tier or billing cycle periodically to maintain efficiency."
    else:
        priority = "Low"
        # Reserve 'cancel' for strong multi-signal evidence:
        # Low utilization + interactive (or general) + non-trivial cost
        if "low_utilization" in signals and (category_type == "interactive" or category_type == "general"):
            if pref == "Money Saver" or monthly_cost >= 300.0:
                action = "cancel"
                color = "danger"
                recommendation = f"Consider cancelling or downgrading to save ₹{monthly_cost:.2f}/month."
            else:
                action = "review"
                color = "warning"
                recommendation = f"Low utilization recorded. Review before next billing cycle to save ₹{monthly_cost:.2f}/month."
        else:
            action = "review"
            color = "warning"
            recommendation = "Review whether this subscription is still needed for your current workflow."

    return {
        "score": final_score,
        "priority": priority,
        "action": action,
        "color": color,
        "confidence": confidence,
        "category_type": category_type,
        "reasons": reasons,
        "signals": signals,
        "recommendation": recommendation,
    }


def calculate_priority(
    occupation: str | None = None,
    financial_preference: str | None = "Balanced",
    category: str = "Other",
    monthly_cost: float = 0.0,
    usage_frequency: str | None = None,
    usage_hours: float | None = None,
) -> Dict[str, Any]:
    """Backward-compatible wrapper returning score, priority, reasons, recommendation."""
    evidence = evaluate_subscription_evidence(
        category=category,
        monthly_cost=monthly_cost,
        usage_frequency=usage_frequency,
        usage_hours=usage_hours,
        financial_preference=financial_preference,
    )
    return {
        "score": evidence["score"],
        "priority": evidence["priority"],
        "reasons": evidence["reasons"],
        "recommendation": evidence["recommendation"],
        "action": evidence["action"],
        "color": evidence["color"],
        "is_interactive": evidence["category_type"] == "interactive",
    }


def get_recommendation(
    priority: str,
    financial_preference: str | None = "Balanced",
    monthly_cost: float = 0.0,
    usage_frequency: str | None = None,
    usage_hours: float | None = None,
    category: str = "Other",
) -> Dict[str, Any]:
    """Backward-compatible wrapper returning message, action, and color."""
    evidence = evaluate_subscription_evidence(
        category=category,
        monthly_cost=monthly_cost,
        usage_frequency=usage_frequency,
        usage_hours=usage_hours,
        financial_preference=financial_preference,
    )
    return {
        "color": evidence["color"],
        "action": evidence["action"],
        "message": evidence["recommendation"],
    }