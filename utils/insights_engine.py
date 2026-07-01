def generate_insight(subscription, financial_preference):
    """
    Generates insight for a subscription.

    Returns:
    {
        service,
        reason,
        recommendation,
        color,
        score
    }
    """

    # Convert usage to average daily hours
    if subscription.usage_frequency == "Daily":
        daily_usage = subscription.usage_hours
    elif subscription.usage_frequency == "Weekly":
        daily_usage = subscription.usage_hours / 7
    elif subscription.usage_frequency == "Monthly":
        daily_usage = subscription.usage_hours / 30
    else:
        daily_usage = subscription.usage_hours / 30

    score = 0

    # Low priority
    if subscription.priority == "Low":
        score += 100

    elif subscription.priority == "Medium":
        score += 50

    # Expensive subscription
    if subscription.monthly_cost >= 1000:
        score += 30

    # Very low usage
    if daily_usage < 0.5:
        score += 30

    # Money Saver users
    if financial_preference == "Money Saver":
        score += 20

    # Decide recommendation
    if score >= 120:

        color = "danger"

        reason = (
            f"High monthly cost (₹{subscription.monthly_cost:.2f}) "
            f"and low usage ({daily_usage:.2f} hrs/day)."
        )

        recommendation = (
            f"Consider cancelling to save ₹{subscription.monthly_cost:.2f}/month."
        )

    elif score >= 70:

        color = "warning"

        reason = (
            f"Moderate usage ({daily_usage:.2f} hrs/day)."
        )

        recommendation = (
            "Review whether this subscription still provides enough value."
        )

    else:

        color = "success"

        reason = (
            f"Frequently used ({daily_usage:.2f} hrs/day)."
        )

        recommendation = (
            "Keep this subscription."
        )

    return {
        "service": subscription.service_name,
        "reason": reason,
        "recommendation": recommendation,
        "color": color,
        "score": score
    }