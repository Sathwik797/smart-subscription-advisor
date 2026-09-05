"""Tests for Phase 3.3 — Hybrid AI Subscription Intelligence.

Tests verify:
1. Deterministic financial summary & aggregations.
2. User data isolation in intelligence context.
3. Deterministic health score calculation and structured factors.
4. Recommendation candidate generation from analytical signals.
5. AI reasoning with valid Groq JSON response.
6. AI reasoning fallback when Groq returns malformed JSON.
7. AI reasoning fallback on Groq timeout.
8. AI reasoning fallback when GROQ_API_KEY is missing.
9. Empty subscription profile behavior.
10. GET /api/intelligence endpoint integration with JWT.

ALL Groq API calls are mocked — zero external network requests.
"""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from flask import Flask
from flask_jwt_extended import JWTManager
from groq import APITimeoutError

from config import Config
from database.db import db
from exceptions.error_handlers import register_error_handlers
from middleware.rate_limiter import limiter
from models.subscription import Subscription
from models.user import User
from routes.api import api
from routes.auth import auth
from services.ai_reasoning_service import AIReasoningService, ai_reasoning_service
from services.auth_service import AuthService
from services.intelligence_service import IntelligenceService, intelligence_service
from utils.currency import format_inr


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-that-is-at-least-32-bytes-long"
    JWT_SECRET_KEY = "test-secret-that-is-at-least-32-bytes-long"
    WTF_CSRF_ENABLED = False
    GROQ_API_KEY = ""


@pytest.fixture
def app():
    test_app = Flask(
        __name__,
        template_folder=str(Path(__file__).resolve().parents[1] / "templates"),
    )
    test_app.config.from_object(TestConfig)

    test_app.jinja_env.filters["inr"] = format_inr
    test_app.jinja_env.globals["format_inr"] = format_inr

    db.init_app(test_app)
    jwt = JWTManager(test_app)

    @jwt.unauthorized_loader
    def unauthorized_loader(callback):
        return {"success": False, "message": "Missing or invalid token"}, 401

    limiter.init_app(test_app)
    test_app.register_blueprint(auth)
    test_app.register_blueprint(api, url_prefix="/api")
    register_error_handlers(test_app)

    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user_with_subscriptions(app, client):
    """Create a verified test user with active subscriptions and return (user, token)."""
    auth_svc = AuthService()
    user = auth_svc.register_user(
        username="hybrid_tester",
        email="hybrid@example.com",
        mobile_number="9876543210",
        password="Password123!",
        occupation="Software Developer",
        financial_preference="Money Saver",
    )
    auth_svc.verify_email(user.verification_token)

    from dateutil.relativedelta import relativedelta

    sub1 = Subscription(
        service_name="Netflix Premium",
        monthly_cost=649.0,
        category="Entertainment",
        start_date=date(2026, 1, 1),
        renewal_date=date.today() + relativedelta(days=3),
        billing_cycle="Monthly",
        usage_frequency="Rarely",
        usage_hours=0.5,
        priority="Low",
        user_id=user.id,
    )
    sub2 = Subscription(
        service_name="Spotify",
        monthly_cost=119.0,
        category="Entertainment",
        start_date=date(2026, 1, 1),
        renewal_date=date.today() + relativedelta(days=20),
        billing_cycle="Monthly",
        usage_frequency="Daily",
        usage_hours=2.0,
        priority="High",
        user_id=user.id,
    )
    sub3 = Subscription(
        service_name="AWS Cloud",
        monthly_cost=1500.0,
        category="Cloud Storage",
        start_date=date(2026, 1, 1),
        renewal_date=date.today() + relativedelta(days=15),
        billing_cycle="Monthly",
        usage_frequency="Daily",
        usage_hours=4.0,
        priority="High",
        user_id=user.id,
    )
    db.session.add_all([sub1, sub2, sub3])
    db.session.commit()

    login_resp = client.post(
        "/api/login",
        json={"email": "hybrid@example.com", "password": "Password123!"},
    )
    token = login_resp.get_json()["data"]["access_token"]
    return user, token


# ---------------------------------------------------------------------------
# Test 1: Intelligence Context Generation & Deterministic Math
# ---------------------------------------------------------------------------

def test_intelligence_context_generation_math(app, user_with_subscriptions):
    """Verify that financial aggregations are 100% deterministic and accurate."""
    user, _ = user_with_subscriptions
    svc = IntelligenceService()
    ctx = svc.build_intelligence_context(user)

    summary = ctx["financial_summary"]
    # Total monthly: 649 + 119 + 1500 = 2268.0
    assert summary["monthly_spending"] == 2268.0
    # Total yearly: 2268.0 * 12 = 27216.0
    assert summary["yearly_projection"] == 27216.0
    assert summary["active_subscriptions"] == 3

    # Potential savings: Netflix is Low priority and rarely used -> 649.0
    assert summary["potential_monthly_savings"] >= 649.0

    # Categories: Entertainment (649+119=768), Cloud Storage (1500)
    cats = {c["name"]: c["monthly_spending"] for c in ctx["categories"]}
    assert cats["Entertainment"] == 768.0
    assert cats["Cloud Storage"] == 1500.0


# ---------------------------------------------------------------------------
# Test 2: User Isolation
# ---------------------------------------------------------------------------

def test_intelligence_context_user_isolation(app, user_with_subscriptions):
    """Verify that only the authenticated user's records are included in context."""
    user, _ = user_with_subscriptions
    auth_svc = AuthService()

    # Create another user with a private subscription
    other_user = auth_svc.register_user(
        username="other_person",
        email="other_person@example.com",
        mobile_number="9876543211",
        password="Password123!",
        occupation="Doctor",
        financial_preference="Balanced",
    )
    auth_svc.verify_email(other_user.verification_token)

    other_sub = Subscription(
        service_name="Private Medical Journal",
        monthly_cost=9999.0,
        category="Education",
        start_date=date(2026, 1, 1),
        renewal_date=date(2026, 2, 1),
        billing_cycle="Monthly",
        usage_frequency="Daily",
        usage_hours=1.0,
        priority="High",
        user_id=other_user.id,
    )
    db.session.add(other_sub)
    db.session.commit()

    svc = IntelligenceService()
    ctx = svc.build_intelligence_context(user)

    # Must NOT include other user's subscription
    sub_names = [s["name"] for s in ctx["subscriptions"]]
    assert "Private Medical Journal" not in sub_names
    assert "Netflix Premium" in sub_names
    assert ctx["financial_summary"]["monthly_spending"] == 2268.0


# ---------------------------------------------------------------------------
# Test 3: Deterministic Health Score Calculation & Factor Breakdown
# ---------------------------------------------------------------------------

def test_deterministic_health_score_and_factors(app, user_with_subscriptions):
    """Verify health score formula and structured factor output."""
    user, _ = user_with_subscriptions
    svc = IntelligenceService()
    ctx = svc.build_intelligence_context(user)

    health = ctx["health_score"]
    assert "score" in health
    assert 0 <= health["score"] <= 100
    assert isinstance(health["factors"], list)
    assert len(health["factors"]) > 0

    # In user_with_subscriptions, Netflix is Low priority and renews in 3 days
    factor_types = [f["type"] for f in health["factors"]]
    assert "underutilized_spend" in factor_types or "renewal_risk" in factor_types


# ---------------------------------------------------------------------------
# Test 4: Recommendation Candidates Detection
# ---------------------------------------------------------------------------

def test_recommendation_candidates_detection(app, user_with_subscriptions):
    """Verify analytical signal / candidate detection rules."""
    user, _ = user_with_subscriptions
    svc = IntelligenceService()
    ctx = svc.build_intelligence_context(user)

    candidates = ctx["recommendation_candidates"]
    assert len(candidates) > 0

    # Netflix candidate has imminent_renewal and low_utilization signals
    netflix_candidates = [c for c in candidates if c.get("subscription") == "Netflix Premium"]
    assert len(netflix_candidates) == 1
    assert "imminent_renewal" in netflix_candidates[0]["signals"]

    # Category concentration candidate for Entertainment (2 subscriptions)
    conc_candidates = [c for c in candidates if c.get("type") == "category_concentration"]
    assert len(conc_candidates) == 1
    assert conc_candidates[0]["category"] == "Entertainment"


# ---------------------------------------------------------------------------
# Test 5: AI Reasoning with Valid Groq Response
# ---------------------------------------------------------------------------

def test_ai_reasoning_with_valid_groq_response(app, user_with_subscriptions):
    """Verify AI reasoning successfully parses valid structured JSON from Groq."""
    user, _ = user_with_subscriptions

    mock_ai_json = {
        "insights": [
            {
                "title": "Entertainment Spend Concentration",
                "message": "You have 2 entertainment subscriptions totaling ₹768.00/month.",
                "priority": "medium",
                "category": "category",
            }
        ],
        "recommendations": [
            {
                "title": "Review Netflix Premium",
                "reason": "You rarely use this service and it is renewing in 3 days.",
                "estimated_monthly_savings": 649.0,
                "action": "cancel",
                "color": "danger",
            }
        ],
    }

    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content=__import__("json").dumps(mock_ai_json)))]

    with patch.dict("os.environ", {"GROQ_API_KEY": "gsk_mock_test_key"}):
        with patch("groq.resources.chat.completions.Completions.create", return_value=mock_completion):
            result = ai_reasoning_service.get_reasoned_intelligence(user)

    intel = result["intelligence"]
    assert intel["source"] == "groq_ai"
    assert len(intel["insights"]) == 1
    assert intel["insights"][0]["title"] == "Entertainment Spend Concentration"
    assert intel["recommendations"][0]["estimated_monthly_savings"] == 649.0


# ---------------------------------------------------------------------------
# Test 6: Fallback on Malformed Groq Output
# ---------------------------------------------------------------------------

def test_fallback_on_malformed_groq_output(app, user_with_subscriptions):
    """Verify fallback seamlessly activates if Groq returns invalid JSON."""
    user, _ = user_with_subscriptions

    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content="THIS IS NOT VALID JSON"))]

    with patch.dict("os.environ", {"GROQ_API_KEY": "gsk_mock_test_key"}):
        with patch("groq.resources.chat.completions.Completions.create", return_value=mock_completion):
            result = ai_reasoning_service.get_reasoned_intelligence(user)

    intel = result["intelligence"]
    assert intel["source"] == "deterministic_fallback"
    assert len(intel["insights"]) >= 1
    assert len(intel["recommendations"]) >= 1


# ---------------------------------------------------------------------------
# Test 7: Fallback on Groq Timeout
# ---------------------------------------------------------------------------

def test_fallback_on_groq_timeout(app, user_with_subscriptions):
    """Verify fallback seamlessly activates if Groq times out."""
    user, _ = user_with_subscriptions

    with patch.dict("os.environ", {"GROQ_API_KEY": "gsk_mock_test_key"}):
        with patch(
            "groq.resources.chat.completions.Completions.create",
            side_effect=APITimeoutError(MagicMock()),
        ):
            result = ai_reasoning_service.get_reasoned_intelligence(user)

    intel = result["intelligence"]
    assert intel["source"] == "deterministic_fallback"
    assert "insights" in intel
    assert "recommendations" in intel


# ---------------------------------------------------------------------------
# Test 8: Fallback when GROQ_API_KEY is Missing
# ---------------------------------------------------------------------------

def test_fallback_when_api_key_missing(app, user_with_subscriptions):
    """Verify fallback activates immediately when GROQ_API_KEY is unset."""
    user, _ = user_with_subscriptions

    with patch.dict("os.environ", {"GROQ_API_KEY": ""}):
        result = ai_reasoning_service.get_reasoned_intelligence(user)

    intel = result["intelligence"]
    assert intel["source"] == "deterministic_fallback"


# ---------------------------------------------------------------------------
# Test 9: Empty Subscriptions Profile
# ---------------------------------------------------------------------------

def test_empty_subscriptions_profile(app):
    """Verify empty profile returns deterministic empty intelligence without Groq call."""
    auth_svc = AuthService()
    user = auth_svc.register_user(
        username="empty_user",
        email="empty@example.com",
        mobile_number="9876543299",
        password="Password123!",
        occupation="Student",
        financial_preference="Balanced",
    )
    auth_svc.verify_email(user.verification_token)

    with patch("services.ai_reasoning_service.AIReasoningService._call_groq_reasoning") as mock_groq:
        result = ai_reasoning_service.get_reasoned_intelligence(user)
        mock_groq.assert_not_called()

    intel = result["intelligence"]
    assert intel["source"] == "deterministic_empty"
    assert result["context"]["financial_summary"]["active_subscriptions"] == 0


# ---------------------------------------------------------------------------
# Test 10: GET /api/intelligence Protected Endpoint
# ---------------------------------------------------------------------------

def test_api_intelligence_endpoint(app, client, user_with_subscriptions):
    """Verify GET /api/intelligence returns 200 with Bearer token, 401 without."""
    user, token = user_with_subscriptions

    # 1. Unauthenticated request -> 401
    unauth_resp = client.get("/api/intelligence")
    assert unauth_resp.status_code == 401

    # 2. Authenticated request -> 200
    auth_resp = client.get(
        "/api/intelligence",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert auth_resp.status_code == 200
    data = auth_resp.get_json()
    assert data["success"] is True
    assert "context" in data["data"]
    assert "intelligence" in data["data"]
    assert data["data"]["context"]["financial_summary"]["active_subscriptions"] == 3
