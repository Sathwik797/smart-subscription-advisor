"""Intelligence service: builds deterministic portfolio facts, analytical signals, and health score.

Phase 2 Architecture:
- Uses precise Python Decimal for all monetary and financial calculations.
- Authoritative billing-cycle awareness (Monthly vs Yearly vs Quarterly vs Weekly).
- Portfolio-aware health score based on spend efficiency without overlapping deductions.
- Conservative, non-duplicated potential savings calculation based on true monthly/yearly equivalents.
- Canonical contract alignment between financial summaries and consumers.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from repositories.subscription_repository import SubscriptionRepository
from utils.recommendation_engine import INTERACTIVE_CATEGORIES, evaluate_subscription_evidence


class IntelligenceService:
    """Encapsulates deterministic financial math, health scoring, and analytical signal detection."""

    def __init__(self, subscription_repository: SubscriptionRepository | None = None):
        self.subscription_repository = subscription_repository or SubscriptionRepository()

    def calculate_health_score(self, subscriptions_or_user: Any) -> Dict[str, Any]:
        """
        Calculate deterministic portfolio health score (0–100) and structured factor breakdown.
        Accepts either a list of subscriptions or a User object.

        Score is portfolio-aware:
        - Evaluates proportion of spend on active/verified utility vs underutilized spend.
        - Expensive productive subscriptions (e.g. AWS, ChatGPT Plus, JetBrains) do NOT lower the score.
        - Deductions are capped and strictly non-overlapping.
        """
        if hasattr(subscriptions_or_user, "id") and not isinstance(subscriptions_or_user, (list, tuple)):
            subscriptions = self.subscription_repository.get_user_subscriptions(subscriptions_or_user.id)
        else:
            subscriptions = subscriptions_or_user

        if not subscriptions:
            return {
                "score": 100,
                "factors": [],
            }

        total_monthly = sum(
            (getattr(sub, "monthly_equivalent", Decimal(str(getattr(sub, "monthly_cost", 0.0) or 0.0))) for sub in subscriptions),
            Decimal("0.00"),
        )
        if total_monthly <= Decimal("0.00"):
            return {
                "score": 100,
                "factors": [],
            }

        score = Decimal("100.0")
        factors = []
        today = date.today()

        # ---------------------------------------------------------------------
        # 1. Underutilized Spend Ratio (up to -40 points)
        # Evaluates actual wasted recurring spend relative to total budget.
        # ---------------------------------------------------------------------
        underutilized_cost = Decimal("0.00")
        for sub in subscriptions:
            days_left = (sub.renewal_date - today).days if getattr(sub, "renewal_date", None) else None
            monthly_equiv = getattr(sub, "monthly_equivalent", Decimal(str(getattr(sub, "monthly_cost", 0.0) or 0.0)))
            evidence = evaluate_subscription_evidence(
                category=getattr(sub, "category", "Other"),
                monthly_cost=float(monthly_equiv),
                usage_frequency=getattr(sub, "usage_frequency", None),
                usage_hours=getattr(sub, "usage_hours", None),
                days_until_renewal=days_left,
                total_monthly_spend=float(total_monthly),
            )
            if evidence["priority"] == "Low":
                underutilized_cost += monthly_equiv

        if underutilized_cost > Decimal("0.00"):
            waste_ratio = min(Decimal("1.0"), underutilized_cost / total_monthly)
            waste_deduction = int(round(float(waste_ratio) * 40.0))
            score -= Decimal(waste_deduction)
            factors.append({
                "type": "underutilized_spend",
                "name": "Underutilized Spend",
                "impact": -waste_deduction,
                "description": f"₹{underutilized_cost:,.2f}/mo ({float(waste_ratio) * 100:.0f}% of budget) is on low-utilization services.",
            })

        # ---------------------------------------------------------------------
        # 2. Subscription Creep / Micro-Leakage (up to -15 points)
        # Detects accumulation of many small subscriptions (<= ₹300/mo) adding up
        # ---------------------------------------------------------------------
        micro_subs = [
            s for s in subscriptions
            if getattr(s, "monthly_equivalent", Decimal(str(getattr(s, "monthly_cost", 0.0) or 0.0))) <= Decimal("300.00")
        ]
        if len(micro_subs) >= 4:
            micro_total = sum(
                (getattr(s, "monthly_equivalent", Decimal(str(getattr(s, "monthly_cost", 0.0) or 0.0))) for s in micro_subs),
                Decimal("0.00"),
            )
            creep_ratio = micro_total / total_monthly
            if creep_ratio >= Decimal("0.25"):
                creep_deduction = min(15, int(round(len(micro_subs) * 2.5)))
                score -= Decimal(creep_deduction)
                factors.append({
                    "type": "subscription_creep",
                    "name": "Subscription Creep",
                    "impact": -creep_deduction,
                    "description": f"{len(micro_subs)} small subscriptions accumulate to ₹{micro_total:,.2f}/mo ({float(creep_ratio) * 100:.0f}% of spend).",
                })

        # ---------------------------------------------------------------------
        # 3. Urgent Renewal Risk on Unreviewed / Low-Utility Subscriptions (up to -10 points)
        # ---------------------------------------------------------------------
        urgent_risky_subs = []
        for sub in subscriptions:
            if getattr(sub, "renewal_date", None):
                days_left = (sub.renewal_date - today).days
                if 0 <= days_left <= 7:
                    monthly_equiv = getattr(sub, "monthly_equivalent", Decimal(str(getattr(sub, "monthly_cost", 0.0) or 0.0)))
                    evidence = evaluate_subscription_evidence(
                        category=getattr(sub, "category", "Other"),
                        monthly_cost=float(monthly_equiv),
                        usage_frequency=getattr(sub, "usage_frequency", None),
                        usage_hours=getattr(sub, "usage_hours", None),
                        days_until_renewal=days_left,
                        total_monthly_spend=float(total_monthly),
                    )
                    if evidence["priority"] == "Low":
                        urgent_risky_subs.append(sub)

        if urgent_risky_subs:
            renewal_deduction = min(10, len(urgent_risky_subs) * 5)
            score -= Decimal(renewal_deduction)
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
            ent_total = sum(
                (getattr(s, "monthly_equivalent", Decimal(str(getattr(s, "monthly_cost", 0.0) or 0.0))) for s in entertainment_subs),
                Decimal("0.00"),
            )
            ent_ratio = ent_total / total_monthly
            if ent_ratio >= Decimal("0.50"):
                conc_deduction = 8
                score -= Decimal(conc_deduction)
                factors.append({
                    "type": "category_concentration",
                    "name": "Entertainment Concentration",
                    "impact": -conc_deduction,
                    "description": f"Entertainment accounts for {float(ent_ratio) * 100:.0f}% of spend across {len(entertainment_subs)} streaming services.",
                })

        final_score = int(round(max(0.0, min(100.0, float(score)))))
        return {
            "score": final_score,
            "factors": factors,
        }

    def generate_recommendation_candidates(self, user: Any, subscriptions: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """
        Detect analytical signals and candidate optimization opportunities.

        Deduplicates multiple signals into ONE consolidated candidate per subscription.
        Emits portfolio-level signals for creep and streaming concentration.
        """
        if subscriptions is None:
            subscriptions = self.subscription_repository.get_user_subscriptions(user.id)

        if not subscriptions:
            return []

        candidates: List[Dict[str, Any]] = []
        today = date.today()
        total_monthly = sum(
            (getattr(sub, "monthly_equivalent", Decimal(str(getattr(sub, "monthly_cost", 0.0) or 0.0))) for sub in subscriptions),
            Decimal("0.00"),
        )
        pref = getattr(user, "financial_preference", "Balanced")

        # 1. Per-Subscription Candidates (Deduplicated)
        for sub in subscriptions:
            days_left = (sub.renewal_date - today).days if getattr(sub, "renewal_date", None) else None
            monthly_equiv = getattr(sub, "monthly_equivalent", Decimal(str(getattr(sub, "monthly_cost", 0.0) or 0.0)))
            evidence = evaluate_subscription_evidence(
                category=getattr(sub, "category", "Other"),
                monthly_cost=float(monthly_equiv),
                usage_frequency=getattr(sub, "usage_frequency", None),
                usage_hours=getattr(sub, "usage_hours", None),
                days_until_renewal=days_left,
                total_monthly_spend=float(total_monthly),
                financial_preference=pref,
            )

            # Only create candidates for items needing review or attention
            if evidence["priority"] in ("Low", "Medium") or "imminent_renewal" in evidence["signals"]:
                estimated_savings = float(round(monthly_equiv, 2)) if evidence["action"] == "cancel" else 0.0

                reason_text = " · ".join(evidence["reasons"])
                if "imminent_renewal" in evidence["signals"] and days_left is not None:
                    reason_text += f" (Renews in {days_left} day{'s' if days_left != 1 else ''})"

                candidates.append({
                    "subscription": getattr(sub, "service_name", "Unknown"),
                    "subscription_id": getattr(sub, "id", None),
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
        micro_subs = [
            s for s in subscriptions
            if getattr(s, "monthly_equivalent", Decimal(str(getattr(s, "monthly_cost", 0.0) or 0.0))) <= Decimal("300.00")
        ]
        if len(micro_subs) >= 4:
            micro_total = sum(
                (getattr(s, "monthly_equivalent", Decimal(str(getattr(s, "monthly_cost", 0.0) or 0.0))) for s in micro_subs),
                Decimal("0.00"),
            )
            creep_pct = (float(micro_total / total_monthly) * 100.0) if total_monthly > Decimal("0.00") else 0.0
            if creep_pct >= 25.0:
                candidates.append({
                    "type": "subscription_creep",
                    "subscription": None,
                    "action": "review",
                    "signals": ["subscription_creep", "micro_spending_accumulation"],
                    "confidence": "high",
                    "reason": f"You have {len(micro_subs)} small subscriptions totaling ₹{micro_total:,.2f}/month ({creep_pct:.0f}% of total spend).",
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
                cat_total = sum(
                    (getattr(s, "monthly_equivalent", Decimal(str(getattr(s, "monthly_cost", 0.0) or 0.0))) for s in subs),
                    Decimal("0.00"),
                )
                cat_pct = (float(cat_total / total_monthly) * 100.0) if total_monthly > Decimal("0.00") else 0.0
                if cat in INTERACTIVE_CATEGORIES:
                    candidates.append({
                        "type": "category_concentration",
                        "category": cat,
                        "action": "rotate" if len(subs) >= 3 else "review",
                        "signals": ["category_concentration", "interactive_multi_service"],
                        "confidence": "high",
                        "reason": f"You have {len(subs)} {cat} services totaling ₹{cat_total:,.2f}/month ({cat_pct:.0f}% of spend).",
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

        Ensures strict user isolation and non-duplicated potential savings using Decimal precision.
        """
        subscriptions = self.subscription_repository.get_user_subscriptions(user.id)
        pref = getattr(user, "financial_preference", "Balanced")

        # 1. Deterministic financial metrics (authoritative Decimal calculations)
        total_monthly = sum(
            (getattr(sub, "monthly_equivalent", Decimal(str(getattr(sub, "monthly_cost", 0.0) or 0.0))) for sub in subscriptions),
            Decimal("0.00"),
        )
        total_yearly = sum(
            (getattr(sub, "yearly_equivalent", Decimal(str(getattr(sub, "monthly_cost", 0.0) or 0.0)) * Decimal("12")) for sub in subscriptions),
            Decimal("0.00"),
        )
        active_count = len(subscriptions)

        # 2. Honest, Non-Duplicated Potential Savings
        # Count each Low-priority / cancelled service at most ONCE using its true monthly & yearly equivalent
        potential_monthly_savings = Decimal("0.00")
        potential_yearly_savings = Decimal("0.00")

        for sub in subscriptions:
            monthly_equiv = getattr(sub, "monthly_equivalent", Decimal(str(getattr(sub, "monthly_cost", 0.0) or 0.0)))
            yearly_equiv = getattr(sub, "yearly_equivalent", monthly_equiv * Decimal("12"))
            evidence = evaluate_subscription_evidence(
                category=getattr(sub, "category", "Other"),
                monthly_cost=float(monthly_equiv),
                usage_frequency=getattr(sub, "usage_frequency", None),
                usage_hours=getattr(sub, "usage_hours", None),
                total_monthly_spend=float(total_monthly),
                financial_preference=pref,
            )
            if evidence["priority"] == "Low":
                potential_monthly_savings += monthly_equiv
                potential_yearly_savings += yearly_equiv

        # 3. Category breakdown
        category_totals: Dict[str, Decimal] = {}
        category_counts: Dict[str, int] = {}
        for sub in subscriptions:
            cat = getattr(sub, "category", "Other") or "Other"
            monthly_equiv = getattr(sub, "monthly_equivalent", Decimal(str(getattr(sub, "monthly_cost", 0.0) or 0.0)))
            category_totals[cat] = category_totals.get(cat, Decimal("0.00")) + monthly_equiv
            category_counts[cat] = category_counts.get(cat, 0) + 1

        categories_summary = []
        for cat, total in sorted(category_totals.items(), key=lambda x: -x[1]):
            pct = (float(total / total_monthly) * 100.0) if total_monthly > Decimal("0.00") else 0.0
            categories_summary.append({
                "name": cat,
                "monthly_spending": float(round(total, 2)),
                "percentage": round(pct, 1),
                "count": category_counts[cat],
            })

        # 4. Renewals
        today = date.today()
        renewals_summary = []
        for sub in subscriptions:
            if getattr(sub, "renewal_date", None):
                days_left = (sub.renewal_date - today).days
                cost_dec = getattr(sub, "cost_decimal", Decimal(str(getattr(sub, "monthly_cost", 0.0) or 0.0)))
                renewals_summary.append({
                    "name": getattr(sub, "service_name", "Unknown"),
                    "cost": float(round(cost_dec, 2)),
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
            cost_dec = getattr(sub, "cost_decimal", Decimal(str(getattr(sub, "monthly_cost", 0.0) or 0.0)))
            monthly_equiv = getattr(sub, "monthly_equivalent", cost_dec)
            yearly_equiv = getattr(sub, "yearly_equivalent", cost_dec * Decimal("12"))
            sub_list.append({
                "id": sub.id,
                "name": getattr(sub, "service_name", "Unknown"),
                "category": getattr(sub, "category", "Other"),
                "monthly_cost": float(round(cost_dec, 2)),
                "monthly_equivalent": float(round(monthly_equiv, 2)),
                "yearly_cost": float(round(yearly_equiv, 2)),
                "billing_cycle": getattr(sub, "billing_cycle", "Monthly"),
                "renewal_date": sub.renewal_date.isoformat() if getattr(sub, "renewal_date", None) else None,
                "usage_frequency": getattr(sub, "usage_frequency", None),
                "priority": getattr(sub, "priority", None),
            })

        fin_summary = {
            "monthly_spending": float(round(total_monthly, 2)),
            "yearly_projection": float(round(total_yearly, 2)),
            "active_subscriptions": active_count,
            "potential_monthly_savings": float(round(potential_monthly_savings, 2)),
            "potential_yearly_savings": float(round(potential_yearly_savings, 2)),
        }

        return {
            "user": {
                "id": user.id,
                "username": getattr(user, "username", "user"),
                "occupation": getattr(user, "occupation", "Other"),
                "financial_preference": pref,
            },
            "financial_summary": fin_summary,
            "categories": categories_summary,
            "renewals": renewals_summary,
            "health_score": health_info,
            "recommendation_candidates": candidates,
            "subscriptions": sub_list,
            "today": today.isoformat(),
            # Canonical/backward-compatible top-level keys:
            "total_monthly": fin_summary["monthly_spending"],
            "total_yearly": fin_summary["yearly_projection"],
            "potential_monthly_savings": fin_summary["potential_monthly_savings"],
            "potential_yearly_savings": fin_summary["potential_yearly_savings"],
            "categories_summary": categories_summary,
        }


intelligence_service = IntelligenceService()
