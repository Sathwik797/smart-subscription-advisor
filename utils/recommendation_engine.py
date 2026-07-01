def calculate_priority(
    occupation,
    financial_preference,
    category,
    monthly_cost,
    usage_frequency,
    usage_hours
):
    score = 0

    # -----------------------------------
    # Convert usage to daily hours
    # -----------------------------------
    if usage_frequency == "Daily":
        daily_usage = usage_hours
    elif usage_frequency == "Weekly":
        daily_usage = usage_hours / 7
    elif usage_frequency == "Monthly":
        daily_usage = usage_hours / 30
    else:
        daily_usage = usage_hours / 30

    # -----------------------------------
    # 1. Usage Frequency (30)
    # -----------------------------------
    frequency_scores = {
        "Daily": 30,
        "Weekly": 20,
        "Monthly": 10,
        "Rarely": 0
    }

    score += frequency_scores.get(usage_frequency, 0)

    # -----------------------------------
    # 2. Daily Usage Hours (25)
    # -----------------------------------
    if daily_usage >= 3:
        score += 25
    elif daily_usage >= 2:
        score += 20
    elif daily_usage >= 1:
        score += 15
    elif daily_usage >= 0.5:
        score += 10

    # -----------------------------------
    # 3. Category Value (15)
    # -----------------------------------
    category_scores = {
        "Education": 15,
        "Productivity": 15,
        "Health": 12,
        "Cloud Storage": 10,
        "Entertainment": 8,
        "Music": 7,
        "Gaming": 6,
        "Other": 5
    }

    score += category_scores.get(category, 5)

    # -----------------------------------
    # 4. Monthly Cost (15)
    # -----------------------------------
    if monthly_cost <= 300:
        score += 15
    elif monthly_cost <= 700:
        score += 12
    elif monthly_cost <= 1000:
        score += 8
    elif monthly_cost <= 2000:
        score += 4

    # -----------------------------------
    # 5. Occupation Bonus (10)
    # -----------------------------------
    occupation_bonus = 3

    if occupation == "Student":

        if category == "Education":
            occupation_bonus = 10

        elif category == "Productivity":
            occupation_bonus = 8

    elif occupation == "Software Developer":

        if category == "Productivity":
            occupation_bonus = 10

        elif category == "Education":
            occupation_bonus = 8

        elif category == "Cloud Storage":
            occupation_bonus = 8

    elif occupation == "Teacher":

        if category == "Education":
            occupation_bonus = 10

    elif occupation == "Business":

        if category == "Productivity":
            occupation_bonus = 10

    score += occupation_bonus
    
    # -----------------------------------
    # 6. Value for Money (5)
    # -----------------------------------

    # Cost per hour of daily usage
    if daily_usage > 0:
        value_ratio = monthly_cost / (daily_usage * 30)
    else:
        value_ratio = float("inf")

    # Lower cost per hour = better value
    if value_ratio <= 10:
        score += 5

    elif value_ratio <= 20:
        score += 3

    elif value_ratio <= 40:
        score += 1

    else:
        score -= 2

    # -----------------------------------
    # 7. Financial Preference (5)
    # -----------------------------------
    if financial_preference == "Money Saver":

        if monthly_cost <= 700:
            score += 5
        else:
            score -= 5

    elif financial_preference == "Balanced":
        score += 3

    elif financial_preference == "Premium":
        score += 5

    # Cap score
    # -----------------------------------
    # Final Score
    # -----------------------------------
    score = max(0, min(score, 100))

    # -----------------------------------
    # Priority
    # -----------------------------------
    if score >= 80:
        priority = "High"
    elif score >= 50:
        priority = "Medium"
    else:
        priority = "Low"

    # -----------------------------------
    # Reasons
    # -----------------------------------
    reasons = []

    # Usage
    if usage_frequency == "Daily":
        reasons.append(f"Used daily for about {usage_hours} hour(s).")
    elif usage_frequency == "Weekly":
        reasons.append(f"Used weekly for about {usage_hours} hour(s).")
    elif usage_frequency == "Monthly":
        reasons.append(f"Used monthly for about {usage_hours} hour(s).")
    else:
        reasons.append("Rarely used.")

    # Category
    reasons.append(f"{category} subscription.")

    # Cost
    if monthly_cost <= 700:
        reasons.append("Good value for money.")
    elif monthly_cost <= 1500:
        reasons.append("Moderately priced subscription.")
    else:
        reasons.append("High monthly cost.")

    # Occupation
    reasons.append(f"Relevant for a {occupation}.")

    # -----------------------------------
    # Recommendation
    # -----------------------------------
    if priority == "High":
        recommendation = "Keep this subscription. It provides strong value."

    elif priority == "Medium":
        recommendation = (
            "Review this subscription occasionally to ensure it is worth the cost."
        )

    else:
        recommendation = (
            "Consider cancelling or downgrading this subscription to save money."
        )

    # -----------------------------------
    # Return Complete Insight
    # -----------------------------------
    return {
        "score": score,
        "priority": priority,
        "reasons": reasons,
        "recommendation": recommendation
    }

def get_recommendation(
    priority,
    financial_preference,
    monthly_cost,
    usage_frequency,
    usage_hours
):
    """
    Returns a recommendation message and color.
    """

    # Convert usage to daily hours
    if usage_frequency == "Daily":
        daily_usage = usage_hours
    elif usage_frequency == "Weekly":
        daily_usage = usage_hours / 7
    elif usage_frequency == "Monthly":
        daily_usage = usage_hours / 30
    else:
        daily_usage = usage_hours / 30

    # Low priority
    if priority == "Low":
        return {
            "color": "danger",
            "message": (
                f"Low priority and limited usage. "
                f"Consider cancelling to save ₹{monthly_cost:.2f}/month."
            )
        }

    # Money Saver + expensive subscription
    if (
        financial_preference == "Money Saver"
        and monthly_cost > 1000
        and daily_usage < 1
    ):
        return {
            "color": "warning",
            "message": (
                "This subscription is expensive compared to your usage. "
                "Review whether it's still worth keeping."
            )
        }

    # Medium priority
    if priority == "Medium":
        return {
            "color": "warning",
            "message": (
                "Moderate value subscription. Review it occasionally."
            )
        }

    # High priority
    return {
        "color": "success",
        "message": (
            "Frequently used and valuable. Recommended to keep."
        )
    }