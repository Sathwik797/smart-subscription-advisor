"""Comprehensive tests for the deterministic recommendation engine (Phase 3.4B).

Covers Scenarios A through R, boundary thresholds, evidence confidence, and financial preferences.
All tests are 100% deterministic — zero LLM calls.
"""

from datetime import date
from unittest.mock import MagicMock
import pytest

from services.intelligence_service import IntelligenceService
from utils.insights_engine import generate_insight
from utils.recommendation_engine import calculate_priority, evaluate_subscription_evidence


class MockSub:
    """Lightweight test double for Subscription model."""
    def __init__(
        self,
        service_name="Test Service",
        monthly_cost=100.0,
        category="Other",
        start_date=None,
        renewal_date=None,
        billing_cycle="Monthly",
        usage_frequency="Daily",
        usage_hours=1.0,
        priority="High",
        sub_id=1,
    ):
        self.id = sub_id
        self.service_name = service_name
        self.monthly_cost = monthly_cost
        self.category = category
        self.start_date = start_date or date(2026, 1, 1)
        self.renewal_date = renewal_date or date(2026, 9, 1)
        self.billing_cycle = billing_cycle
        self.usage_frequency = usage_frequency
        self.usage_hours = usage_hours
        self.priority = priority


class MockUser:
    """Lightweight test double for User model."""
    def __init__(self, user_id=1, username="test_user", occupation="Developer", financial_preference="Balanced"):
        self.id = user_id
        self.username = username
        self.occupation = occupation
        self.financial_preference = financial_preference


# ---------------------------------------------------------------------------
# Scenario A: High-use Netflix -> Keep (never recommend cancellation)
# ---------------------------------------------------------------------------
def test_scenario_a_netflix_high_usage():
    sub = MockSub(service_name="Netflix", monthly_cost=649.0, category="Entertainment", usage_frequency="Daily", usage_hours=3.0)
    ev = evaluate_subscription_evidence(sub.category, sub.monthly_cost, sub.usage_frequency, sub.usage_hours)
    assert ev["action"] == "keep"
    assert ev["priority"] == "High"
    assert ev["color"] == "success"
    assert ev["confidence"] == "high"


# ---------------------------------------------------------------------------
# Scenario B: Rarely-used Netflix -> Review opportunity, not immediate forced cancellation
# ---------------------------------------------------------------------------
def test_scenario_b_netflix_rarely_used():
    sub = MockSub(service_name="Netflix", monthly_cost=649.0, category="Entertainment", usage_frequency="Rarely", usage_hours=0.0)
    ev = evaluate_subscription_evidence(sub.category, sub.monthly_cost, sub.usage_frequency, sub.usage_hours, financial_preference="Balanced")
    assert ev["priority"] == "Low"
    assert ev["action"] in ("cancel", "review")
    insight = generate_insight(sub, financial_preference="Balanced")
    assert "save" in insight["recommendation"] or "Review" in insight["recommendation"]


# ---------------------------------------------------------------------------
# Scenario C: Daily Spotify -> Keep
# ---------------------------------------------------------------------------
def test_scenario_c_spotify_daily():
    sub = MockSub(service_name="Spotify", monthly_cost=119.0, category="Music", usage_frequency="Daily", usage_hours=2.0)
    ev = evaluate_subscription_evidence(sub.category, sub.monthly_cost, sub.usage_frequency, sub.usage_hours)
    assert ev["action"] == "keep"
    assert ev["priority"] == "High"


# ---------------------------------------------------------------------------
# Scenario D: Google One rarely opened -> Not treated as wasted purely due to low screen time
# ---------------------------------------------------------------------------
def test_scenario_d_google_one_passive_utility():
    sub = MockSub(service_name="Google One", monthly_cost=130.0, category="Cloud Storage", usage_frequency="Rarely", usage_hours=0.1)
    ev = evaluate_subscription_evidence(sub.category, sub.monthly_cost, sub.usage_frequency, sub.usage_hours)
    # Utility tool is evaluated with utility baseline (Medium priority, NOT Low danger)
    assert ev["category_type"] == "utility"
    assert ev["priority"] in ("Medium", "High")
    assert ev["action"] != "cancel"


# ---------------------------------------------------------------------------
# Scenario E: AWS expensive but actively used -> No automatic high-cost penalty
# ---------------------------------------------------------------------------
def test_scenario_e_aws_expensive_active_work_tool():
    sub = MockSub(service_name="AWS Cloud", monthly_cost=1500.0, category="Cloud Storage", usage_frequency="Daily", usage_hours=6.0)
    ev = evaluate_subscription_evidence(sub.category, sub.monthly_cost, sub.usage_frequency, sub.usage_hours)
    assert ev["priority"] == "High"
    assert ev["action"] == "keep"
    assert ev["score"] >= 80


# ---------------------------------------------------------------------------
# Scenario F: ChatGPT heavily used -> Treated as valuable evidence
# ---------------------------------------------------------------------------
def test_scenario_f_chatgpt_heavily_used():
    sub = MockSub(service_name="ChatGPT Plus", monthly_cost=1999.0, category="Productivity", usage_frequency="Daily", usage_hours=4.0)
    ev = evaluate_subscription_evidence(sub.category, sub.monthly_cost, sub.usage_frequency, sub.usage_hours)
    assert ev["priority"] == "High"
    assert ev["action"] == "keep"


# ---------------------------------------------------------------------------
# Scenario G: Multiple streaming services -> Rotation/review signal, not automatic cancellation
# ---------------------------------------------------------------------------
def test_scenario_g_multiple_streaming_services():
    subs = [
        MockSub("Netflix", 649.0, "Entertainment", usage_frequency="Daily", usage_hours=2.0),
        MockSub("Prime Video", 125.0, "Entertainment", usage_frequency="Weekly", usage_hours=2.0),
        MockSub("Disney+ Hotstar", 299.0, "Entertainment", usage_frequency="Weekly", usage_hours=1.0),
    ]
    svc = IntelligenceService(subscription_repository=MagicMock())
    candidates = svc.generate_recommendation_candidates(MockUser(), subs)

    conc = [c for c in candidates if c.get("type") == "category_concentration"]
    assert len(conc) == 1
    assert conc[0]["category"] == "Entertainment"
    assert conc[0]["action"] == "rotate"
    # Does NOT cancel all individual services
    for s in subs:
        ev = evaluate_subscription_evidence(s.category, s.monthly_cost, s.usage_frequency, s.usage_hours)
        assert ev["action"] != "cancel"


# ---------------------------------------------------------------------------
# Scenario H: Multiple productivity tools -> NOT marked redundant
# ---------------------------------------------------------------------------
def test_scenario_h_multiple_productivity_tools_not_redundant():
    subs = [
        MockSub("GitHub Pro", 330.0, "Productivity", usage_frequency="Daily", usage_hours=4.0),
        MockSub("Notion Plus", 800.0, "Productivity", usage_frequency="Daily", usage_hours=3.0),
    ]
    svc = IntelligenceService(subscription_repository=MagicMock())
    candidates = svc.generate_recommendation_candidates(MockUser(), subs)

    # Productivity tools must NOT receive redundant cancellation advice
    for c in candidates:
        if c.get("subscription") in ("GitHub Pro", "Notion Plus"):
            assert c.get("action") != "cancel"


# ---------------------------------------------------------------------------
# Scenario I: Several small subscriptions -> Subscription creep only when meaningful
# ---------------------------------------------------------------------------
def test_scenario_i_subscription_creep_when_meaningful():
    # 2 small subscriptions = NOT creep
    two_subs = [MockSub("Sub1", 199.0, "Other"), MockSub("Sub2", 199.0, "Other")]
    svc = IntelligenceService(subscription_repository=MagicMock())
    cand_small = svc.generate_recommendation_candidates(MockUser(), two_subs)
    assert not any(c.get("type") == "subscription_creep" for c in cand_small)

    # 6 small subscriptions = Trigger creep
    six_subs = [MockSub(f"Sub{i}", 249.0, "Other", sub_id=i) for i in range(6)]
    cand_large = svc.generate_recommendation_candidates(MockUser(), six_subs)
    creep = [c for c in cand_large if c.get("type") == "subscription_creep"]
    assert len(creep) == 1


# ---------------------------------------------------------------------------
# Scenario J: Expensive but essential portfolio -> Healthy score remains high
# ---------------------------------------------------------------------------
def test_scenario_j_expensive_essential_portfolio():
    subs = [
        MockSub("AWS Cloud", 2500.0, "Cloud Storage", usage_frequency="Daily", usage_hours=6.0),
        MockSub("JetBrains All Products", 1800.0, "Productivity", usage_frequency="Daily", usage_hours=8.0),
        MockSub("ChatGPT Plus", 1999.0, "Productivity", usage_frequency="Daily", usage_hours=3.0),
    ]
    svc = IntelligenceService(subscription_repository=MagicMock())
    health = svc.calculate_health_score(subs)
    assert health["score"] >= 90


# ---------------------------------------------------------------------------
# Scenario K: Mostly underutilized portfolio -> Score declines proportionally
# ---------------------------------------------------------------------------
def test_scenario_k_underutilized_portfolio_score_declines():
    subs = [
        MockSub("Unused Gym", 2000.0, "Other", usage_frequency="Rarely", usage_hours=0.0),
        MockSub("Unused Gaming", 1000.0, "Gaming", usage_frequency="Rarely", usage_hours=0.0),
        MockSub("Active Spotify", 119.0, "Music", usage_frequency="Daily", usage_hours=2.0),
    ]
    svc = IntelligenceService(subscription_repository=MagicMock())
    health = svc.calculate_health_score(subs)
    assert health["score"] <= 70
    assert any(f["type"] == "underutilized_spend" for f in health["factors"])


# ---------------------------------------------------------------------------
# Scenario L: Renewal tomorrow + weak evidence -> Highlight renewal, do NOT force cancel
# ---------------------------------------------------------------------------
def test_scenario_l_renewal_tomorrow_weak_evidence():
    from dateutil.relativedelta import relativedelta
    sub = MockSub("Medium Tool", 400.0, "Productivity", renewal_date=date.today() + relativedelta(days=1), usage_frequency=None, usage_hours=None)
    ev = evaluate_subscription_evidence(sub.category, sub.monthly_cost, sub.usage_frequency, sub.usage_hours, days_until_renewal=1)
    assert "renewal_tomorrow" in ev["signals"]
    assert ev["action"] == "review"  # Review, not cancel!


# ---------------------------------------------------------------------------
# Scenario M: Renewal tomorrow + strong low-value evidence -> Stronger cancel/review candidate
# ---------------------------------------------------------------------------
def test_scenario_m_renewal_tomorrow_strong_low_value():
    from dateutil.relativedelta import relativedelta
    sub = MockSub("Unused Streaming", 649.0, "Entertainment", renewal_date=date.today() + relativedelta(days=1), usage_frequency="Rarely", usage_hours=0.0)
    ev = evaluate_subscription_evidence(sub.category, sub.monthly_cost, sub.usage_frequency, sub.usage_hours, days_until_renewal=1, financial_preference="Money Saver")
    assert ev["priority"] == "Low"
    assert ev["action"] == "cancel"
    assert "imminent_renewal" in ev["signals"]


# ---------------------------------------------------------------------------
# Scenario N: Empty portfolio
# ---------------------------------------------------------------------------
def test_scenario_n_empty_portfolio():
    svc = IntelligenceService(subscription_repository=MagicMock())
    health = svc.calculate_health_score([])
    assert health["score"] == 100
    assert health["factors"] == []


# ---------------------------------------------------------------------------
# Scenario O: Same subscription triggered by multiple signals -> Savings counted once
# ---------------------------------------------------------------------------
def test_scenario_o_savings_not_double_counted():
    from dateutil.relativedelta import relativedelta
    # Sub with low utilization, imminent renewal, and high portfolio share
    sub = MockSub("Heavy Unused", 1000.0, "Entertainment", renewal_date=date.today() + relativedelta(days=2), usage_frequency="Rarely", usage_hours=0.0)
    svc = IntelligenceService(subscription_repository=MagicMock())
    user = MockUser()
    svc.subscription_repository.get_user_subscriptions = MagicMock(return_value=[sub])

    ctx = svc.build_intelligence_context(user)
    # Potential monthly savings must be exact single cost (1000.0), not 2000 or 3000!
    assert ctx["financial_summary"]["potential_monthly_savings"] == 1000.0
    assert ctx["financial_summary"]["potential_yearly_savings"] == 12000.0


# ---------------------------------------------------------------------------
# Scenario P: Financial preferences influence recommendation urgency
# ---------------------------------------------------------------------------
def test_scenario_p_financial_preferences_impact():
    # An underutilized moderate sub evaluated under Money Saver vs Premium
    ev_saver = evaluate_subscription_evidence("Entertainment", 400.0, "Rarely", 0.0, financial_preference="Money Saver")
    ev_premium = evaluate_subscription_evidence("Entertainment", 400.0, "Rarely", 0.0, financial_preference="Premium")

    assert ev_saver["score"] <= ev_premium["score"]
    assert "Optimization prioritized under Money Saver profile." in ev_saver["reasons"]


# ---------------------------------------------------------------------------
# Scenario Q: Missing/zero usage data -> Lower confidence, not automatic zero
# ---------------------------------------------------------------------------
def test_scenario_q_missing_usage_data_confidence():
    ev_missing = evaluate_subscription_evidence("Productivity", 500.0, usage_frequency=None, usage_hours=None)
    assert ev_missing["confidence"] == "low"
    assert ev_missing["action"] == "review"

    ev_complete = evaluate_subscription_evidence("Productivity", 500.0, usage_frequency="Daily", usage_hours=2.0)
    assert ev_complete["confidence"] == "high"


# ---------------------------------------------------------------------------
# Scenario R: "Other" category conservative behavior
# ---------------------------------------------------------------------------
def test_scenario_r_other_category_conservative():
    # Active other category
    ev_active = evaluate_subscription_evidence("Other", 500.0, "Daily", 1.0)
    assert ev_active["priority"] in ("High", "Medium")

    # Inactive other category
    ev_inactive = evaluate_subscription_evidence("Other", 500.0, "Rarely", 0.0)
    assert ev_inactive["priority"] == "Low"


# ---------------------------------------------------------------------------
# Boundary Threshold Tests (2.0h, 7-day renewals, 4 micro-subs)
# ---------------------------------------------------------------------------
def test_boundary_screen_time_thresholds():
    # Daily hours threshold around 2.0h
    ev_below = evaluate_subscription_evidence("Entertainment", 500.0, "Daily", 1.9)
    ev_at = evaluate_subscription_evidence("Entertainment", 500.0, "Daily", 2.0)
    ev_above = evaluate_subscription_evidence("Entertainment", 500.0, "Daily", 2.1)

    assert ev_below["score"] < ev_at["score"]
    assert ev_at["score"] == ev_above["score"]


def test_boundary_renewal_days_thresholds():
    # 7 days is imminent, 8 days is not
    ev_7 = evaluate_subscription_evidence("Entertainment", 500.0, "Daily", 2.0, days_until_renewal=7)
    ev_8 = evaluate_subscription_evidence("Entertainment", 500.0, "Daily", 2.0, days_until_renewal=8)

    assert "imminent_renewal" in ev_7["signals"]
    assert "imminent_renewal" not in ev_8["signals"]


def test_boundary_micro_subs_count_threshold():
    svc = IntelligenceService(subscription_repository=MagicMock())
    # 3 micro-subs -> No creep
    subs_3 = [MockSub(f"S{i}", 200.0, "Other", sub_id=i) for i in range(3)]
    cand_3 = svc.generate_recommendation_candidates(MockUser(), subs_3)
    assert not any(c.get("type") == "subscription_creep" for c in cand_3)

    # 4 micro-subs -> Triggers creep
    subs_4 = [MockSub(f"S{i}", 200.0, "Other", sub_id=i) for i in range(4)]
    cand_4 = svc.generate_recommendation_candidates(MockUser(), subs_4)
    assert any(c.get("type") == "subscription_creep" for c in cand_4)
