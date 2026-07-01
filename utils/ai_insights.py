def generate_subscription_insight(subscription, user):
    score = 50
    reasons = []

    # Usage
    if subscription.usage_frequency == "Daily":
        score += 25
        reasons.append("Daily usage increases value.")
    elif subscription.usage_frequency == "Weekly":
        score += 10
        reasons.append("Used regularly during the week.")
    else:
        score -= 10
        reasons.append("Low usage reduces value.")

    # Cost
    if subscription.monthly_cost <= 300:
        score += 15
        reasons.append("Affordable monthly cost.")
    elif subscription.monthly_cost >= 1000:
        score -= 20
        reasons.append("High monthly cost.")

    # Financial Preference
    if user.financial_preference == "Saver":
        score -= 5
        reasons.append("Saver profile prefers fewer subscriptions.")
    elif user.financial_preference == "Balanced":
        score += 5
        reasons.append("Matches balanced spending habits.")

    score = max(0, min(score, 100))

    if score >= 80:
        priority = "High"
        color = "success"
        recommendation = "Keep this subscription."
    elif score >= 60:
        priority = "Medium"
        color = "warning"
        recommendation = "Review usage occasionally."
    else:
        priority = "Low"
        color = "danger"
        recommendation = "Consider cancelling or downgrading."

    return {
        "score": score,
        "priority": priority,
        "color": color,
        "reasons": reasons,
        "recommendation": recommendation
    }