"""Intelligence service: builds deterministic portfolio facts, analytical signals, and health score.

Phase 3.4B Architecture:
- Uses unified evaluate_subscription_evidence as the single authoritative decision model.
- Portfolio-aware health score based on spend efficiency without overlapping double deductions.
- Conservative potential savings calculation (deduplicated, no invented numbers).
- Produces clean evidence-backed recommendation candidates for dashboard and AI reasoning layer.
"""

from datetime import date, timedelta
from typing import Any, Dict, List

from repositories.subscription_repository import SubscriptionRepository
from utils.insights_engine import generate_insight
from utils.recommendation_engine import INTERACTIVE_CATEGORIES, evaluate_subscription_evidence


class IntelligenceService:
    """Encapsulates deterministic financial math, health scoring, and analytical signal detection."""

    def __init__(self, subscription_repository: SubscriptionRepository | None = None):
        self.subscription_repository = subscription_repository or SubscriptionRepository()

    def calculate_health_score(self, subscriptions: List[Any]) -> Dict[str, Any]:
        """
        Calculate deterministic portfolio health score (0–100) and structured factor breakdown.

        Score is portfolio-aware:
        - Evaluates proportion of spend on active/verified utility vs underutilized spend.
        - Expensive productive subscriptions (e.g. AWS, ChatGPT Plus, JetBrains) do NOT lower the score.
        - Deductions are capped and strictly non-overlapping.
        """
        if not subscriptions:
            return {
                "score": 100,
                "factors": [],
            }

        total_monthly = sum(float(getattr(sub, "monthly_cost", 0.0) or 0.0) for sub in subscriptions)
        if total_monthly <= 0:
            return {
                "score": 100,
                "factors": [],
            }

        score = 100.0
        factors = []
        today = date.today()

        # ---------------------------------------------------------------------
        # 1. Underutilized Spend Ratio (up to -40 points)
        # Evaluates actual wasted recurring spend relative to total budget.
        # ---------------------------------------------------------------------
        underutilized_cost = 0.0
        for sub in subscriptions:
            days_left = (sub.renewal_date - today).days if getattr(sub, "renewal_date", None) else None
            evidence = evaluate_subscription_evidence(
                category=getattr(sub, "category", "Other"),
                monthly_cost=getattr(sub, "monthly_cost", 0.0),
                usage_frequency=getattr(sub, "usage_frequency", None),
                usage_hours=getattr(sub, "usage_hours", None),
                days_until_renewal=days_left,
                total_monthly_spend=total_monthly,
            )
            if evidence["priority"] == "Low":
                underutilized_cost += float(sub.monthly_cost)

        if underutilized_cost > 0:
            waste_ratio = min(1.0, underutilized_cost / total_monthly)
            waste_deduction = round(waste_ratio * 40.0)
            score -= waste_deduction
            factors.append({
                "type": "underutilized_spend",
                "name": "Underutilized Spend",
                "impact": -waste_deduction,
                "description": f"₹{underutilized_cost:.2f}/mo ({waste_ratio * 100:.0f}% of budget) is on low-utilization services.",
            })

        # ---------------------------------------------------------------------
        # 2. Subscription Creep / Micro-Leakage (up to -15 points)
        # Detects accumulation of many small subscriptions (<= ₹300) adding up
        # ---------------------------------------------------------------------
        micro_subs = [s for s in subscriptions if float(getattr(s, "monthly_cost", 0.0) or 0.0) <= 300.0]
        if len(micro_subs) >= 4:
            micro_total = sum(float(s.monthly_cost) for s in micro_subs)
            creep_ratio = micro_total / total_monthly
            if creep_ratio >= 0.25:
                creep_deduction = min(15, round(len(micro_subs) * 2.5))
                score -= creep_deduction
                factors.append({
                    "type": "subscription_creep",
                    "name": "Subscription Creep",
                    "impact": -creep_deduction,
                    "description": f"{len(micro_subs)} small subscriptions accumulate to ₹{micro_total:.2f}/mo ({creep_ratio * 100:.0f}% of spend).",
                })

        # ---------------------------------------------------------------------
        # 3. Urgent Renewal Risk on Unreviewed / Low-Utility Subscriptions (up to -10 points)
        # ---------------------------------------------------------------------
        urgent_risky_subs = []
        for sub in subscriptions:
            if getattr(sub, "renewal_date", None):
                days_left = (sub.renewal_date - today).days
                if 0 <= days_left <= 7:
                    evidence = evaluate_subscription_evidence(
                        category=getattr(sub, "category", "Other"),
                        monthly_cost=getattr(sub, "monthly_cost", 0.0),
                        usage_frequency=getattr(sub, "usage_frequency", None),
                        usage_hours=getattr(sub, "usage_hours", None),
                        days_until_renewal=days_left,
                        total_monthly_spend=total_monthly,
                    )
                    if evidence["priority"] == "Low":
                        urgent_risky_subs.append(sub)

        if urgent_risky_subs:
            renewal_deduction = min(10, len(urgent_risky_subs) * 5)
            score -= renewal_deduction
            factors.append({
                "type": "renewal_risk",
                "name": "Upcoming Renewal Attention",
                "impact": -renewal_deduction,
                "description": f"{len(urgent_risky_subs)} low-utilization service(s) renew within 7 days.",
            })

        # ---------------------------------------------------------------------
        # 4. Severe Entertainment Overconcentration (up to -8 points)
        # ---------------------------------------------------------------------
        entertainment_subs = [s for s in subscriptions if getattr(s, "category", "") == "Entertainment"]
        if len(entertainment_subs) >= 3:
            ent_total = sum(float(s.monthly_cost) for s in entertainment_subs)
            ent_ratio = ent_total / total_monthly
            if ent_ratio >= 0.50:
                conc_deduction = 8
                score -= conc_deduction
                factors.append({
                    "type": "category_concentration",
                    "name": "Entertainment Concentration",
                    "impact": -conc_deduction,
                    "description": f"Entertainment accounts for {ent_ratio * 100:.0f}% of spend across {len(entertainment_subs)} streaming services.",
                })

        final_score = int(round(max(0.0, min(100.0, score))))
        return {
            "score": final_score,
            "factors": factors,
        }

    def generate_recommendation_candidates(self, user: Any, subscriptions: List[Any]) -> List[Dict[str, Any]]:
        """
        Detect analytical signals and candidate optimization opportunities.

        Deduplicates multiple signals into ONE consolidated candidate per subscription.
        Emits portfolio-level signals for creep and streaming concentration.
        """
        if not subscriptions:
            return []

        candidates: List[Dict[str, Any]] = []
        today = date.today()
        total_monthly = sum(float(getattr(sub, "monthly_cost", 0.0) or 0.0) for sub in subscriptions)
        pref = getattr(user, "financial_preference", "Balanced")

        # 1. Per-Subscription Candidates (Deduplicated)
        for sub in subscriptions:
            days_left = (sub.renewal_date - today).days if getattr(sub, "renewal_date", None) else None
            evidence = evaluate_subscription_evidence(
                category=getattr(sub, "category", "Other"),
                monthly_cost=getattr(sub, "monthly_cost", 0.0),
                usage_frequency=getattr(sub, "usage_frequency", None),
                usage_hours=getattr(sub, "usage_hours", None),
                days_until_renewal=days_left,
                total_monthly_spend=total_monthly,
                financial_preference=pref,
            )

            # Only create candidates for items needing review or attention
            if evidence["priority"] in ("Low", "Medium") or "imminent_renewal" in evidence["signals"]:
                estimated_savings = float(sub.monthly_cost) if evidence["action"] == "cancel" else 0.0

                reason_text = " · ".join(evidence["reasons"])
                if "imminent_renewal" in evidence["signals"] and days_left is not None:
                    reason_text += f" (Renews in {days_left} day{'s' if days_left != 1 else ''})"

                candidates.append({
                    "subscription": getattr(sub, "service_name", "Unknown"),
                    "category": getattr(sub, "category", "Other"),
                    "action": evidence["action"],
                    "signals": evidence["signals"],
                    "confidence": evidence["confidence"],
                    "reason": reason_text,
                    "recommendation": evidence["recommendation"],
                    "color": evidence["color"],
                    "estimated_savings": estimated_savings,
                    "score": evidence["score"],
                })

        # 2. Portfolio-Level Signal: Subscription Creep
        micro_subs = [s for s in subscriptions if float(getattr(s, "monthly_cost", 0.0) or 0.0) <= 300.0]
        if len(micro_subs) >= 4:
            micro_total = sum(float(s.monthly_cost) for s in micro_subs)
            creep_pct = (micro_total / total_monthly * 100) if total_monthly > 0 else 0
            if creep_pct >= 25:
                candidates.append({
                    "type": "subscription_creep",
                    "subscription": None,
                    "action": "review",
                    "signals": ["subscription_creep", "micro_spending_accumulation"],
                    "confidence": "high",
                    "reason": f"You have {len(micro_subs)} small subscriptions totaling ₹{micro_total:.2f}/month ({creep_pct:.0f}% of total spend).",
                    "recommendation": "Audit recurring micro-subscriptions to verify if each service is actively needed.",
                    "color": "info",
                    "estimated_savings": 0.0,
                    "score": 60,
                })

        # 3. Portfolio-Level Signal: Streaming Concentration
        category_groups: Dict[str, List[Any]] = {}
        for sub in subscriptions:
            category_groups.setdefault(getattr(sub, "category", "Other"), []).append(sub)

        for cat, subs in category_groups.items():
            if len(subs) >= 2:
                cat_total = sum(float(s.monthly_cost) for s in subs)
                cat_pct = (cat_total / total_monthly * 100) if total_monthly > 0 else 0
                if cat in INTERACTIVE_CATEGORIES:
                    candidates.append({
                        "type": "category_concentration",
                        "category": cat,
                        "action": "rotate" if len(subs) >= 3 else "review",
                        "signals": ["category_concentration", "interactive_multi_service"],
                        "confidence": "high",
                        "reason": f"You have {len(subs)} {cat} services totaling ₹{cat_total:.2f}/month ({cat_pct:.0f}% of spend).",
                        "recommendation": f"Consider alternating or rotating between {cat} services rather than paying for all simultaneously.",
                        "color": "info",
                        "estimated_savings": 0.0,
                        "score": 55,
                    })

        # Sort candidates by urgency / score descending
        candidates.sort(key=lambda c: c.get("score", 0), reverse=True)
        return candidates

    def build_intelligence_context(self, user: Any) -> Dict[str, Any]:
        """
        Build the unified, grounded intelligence context for a specific authenticated user.

        Ensures strict user isolation and non-duplicated potential savings.
        """
        subscriptions = self.subscription_repository.get_user_subscriptions(user.id)
        pref = getattr(user, "financial_preference", "Balanced")

        # 1. Deterministic financial metrics
        total_monthly = sum(float(sub.monthly_cost) for sub in subscriptions)
        total_yearly = total_monthly * 12.0
        active_count = len(subscriptions)

        # 2. Honest, Non-Duplicated Potential Savings
        # Count each Low-priority / cancelled service at most ONCE
        potential_monthly_savings = 0.0
        for sub in subscriptions:
            evidence = evaluate_subscription_evidence(
                category=getattr(sub, "category", "Other"),
                monthly_cost=getattr(sub, "monthly_cost", 0.0),
                usage_frequency=getattr(sub, "usage_frequency", None),
                usage_hours=getattr(sub, "usage_hours", None),
                total_monthly_spend=total_monthly,
                financial_preference=pref,
            )
            if evidence["priority"] == "Low":
                potential_monthly_savings += float(sub.monthly_cost)

        potential_yearly_savings = potential_monthly_savings * 12.0

        # 3. Category breakdown
        category_totals: Dict[str, float] = {}
        category_counts: Dict[str, int] = {}
        for sub in subscriptions:
            cat = getattr(sub, "category", "Other") or "Other"
            category_totals[cat] = category_totals.get(cat, 0.0) + float(sub.monthly_cost)
            category_counts[cat] = category_counts.get(cat, 0) + 1

        categories_summary = []
        for cat, total in sorted(category_totals.items(), key=lambda x: -x[1]):
            pct = (total / total_monthly * 100.0) if total_monthly > 0 else 0.0
            categories_summary.append({
                "name": cat,
                "monthly_spending": round(total, 2),
                "percentage": round(pct, 1),
                "count": category_counts[cat],
            })

        # 4. Renewals
        today = date.today()
        renewals_summary = []
        for sub in subscriptions:
            if getattr(sub, "renewal_date", None):
                days_left = (sub.renewal_date - today).days
                renewals_summary.append({
                    "name": getattr(sub, "service_name", "Unknown"),
                    "cost": float(sub.monthly_cost),
                    "renewal_date": sub.renewal_date.isoformat(),
                    "days_until_renewal": days_left,
                    "billing_cycle": getattr(sub, "billing_cycle", "Monthly"),
                })
        renewals_summary.sort(key=lambda r: r["days_until_renewal"])

        # 5. Deterministic health score & factor breakdown
        health_info = self.calculate_health_score(subscriptions)

        # 6. Recommendation candidates (deduplicated)
        candidates = self.generate_recommendation_candidates(user, subscriptions)

        # 7. Serialized subscriptions list
        sub_list = []
        for sub in subscriptions:
            sub_list.append({
                "id": sub.id,
                "name": getattr(sub, "service_name", "Unknown"),
                "category": getattr(sub, "category", "Other"),
                "monthly_cost": float(sub.monthly_cost),
                "yearly_cost": round(float(sub.monthly_cost) * 12.0, 2),
                "billing_cycle": getattr(sub, "billing_cycle", "Monthly"),
                "renewal_date": sub.renewal_date.isoformat() if getattr(sub, "renewal_date", None) else None,
                "usage_frequency": getattr(sub, "usage_frequency", None),
                "priority": getattr(sub, "priority", None),
            })

        return {
            "user": {
                "id": user.id,
                "username": getattr(user, "username", "user"),
                "occupation": getattr(user, "occupation", "Other"),
                "financial_preference": pref,
            },
            "financial_summary": {
                "monthly_spending": round(total_monthly, 2),
                "yearly_projection": round(total_yearly, 2),
                "active_subscriptions": active_count,
                "potential_monthly_savings": round(potential_monthly_savings, 2),
                "potential_yearly_savings": round(potential_yearly_savings, 2),
            },
            "categories": categories_summary,
            "renewals": renewals_summary,
            "health_score": health_info,
            "recommendation_candidates": candidates,
            "subscriptions": sub_list,
            "today": today.isoformat(),
        }


intelligence_service = IntelligenceService()
