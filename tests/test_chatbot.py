"""Tests for the Subscription Advisor chatbot backend.

Tests cover:
  A. Authenticated relevant question → returns successful response.
  B. Unauthenticated request → returns 401.
  C. Out-of-scope question → returns controlled refusal, Groq NOT called.
  D. User isolation → service retrieves subscriptions only for authenticated user.
  E. Missing/empty message → returns 400 validation response.
  F. Groq failure → returns safe error response, no provider details leaked.

All Groq API calls are mocked — no real external calls are made.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from flask import Flask
from flask_jwt_extended import JWTManager

from config import Config
from database.db import db
from exceptions.exceptions import AppException
from models.user import User
from models.subscription import Subscription
from routes.api import api
from routes.auth import auth
from services.auth_service import AuthService
from exceptions.error_handlers import register_error_handlers
from middleware.rate_limiter import limiter
from utils.currency import format_inr


# ---------------------------------------------------------------------------
# Test App Configuration
# ---------------------------------------------------------------------------

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-that-is-at-least-32-bytes-long"
    JWT_SECRET_KEY = "test-secret-that-is-at-least-32-bytes-long"
    WTF_CSRF_ENABLED = False
    # Ensure no real Groq key is accidentally used in tests
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

    @jwt.invalid_token_loader
    def invalid_token_loader(callback):
        return {"success": False, "message": "Invalid token"}, 401

    @jwt.expired_token_loader
    def expired_token_loader(jwt_header, jwt_payload):
        return {"success": False, "message": "Token has expired"}, 401

    # Bind Flask-Limiter to this test app (required — limiter is a module singleton)
    limiter.init_app(test_app)

    test_app.register_blueprint(auth)
    test_app.register_blueprint(api, url_prefix="/api")

    # Register error handlers so AppException → proper HTTP response in tests
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
def authenticated_user(app, client):
    """Create, verify, log in via API, and return user object + Bearer token."""
    auth_svc = AuthService()

    # We are already inside the app context provided by the `app` fixture.
    user = auth_svc.register_user(
        username="chatbot_tester",
        email="chatbot@example.com",
        mobile_number="9000000001",
        password="Password123!",
        occupation="Software Developer",
        financial_preference="Balanced",
    )
    auth_svc.verify_email(user.verification_token)

    # Add subscriptions directly within the existing app context
    from datetime import date
    from dateutil.relativedelta import relativedelta

    sub1 = Subscription(
        service_name="Netflix",
        monthly_cost=649.0,
        category="Entertainment",
        start_date=date(2026, 1, 1),
        renewal_date=date(2026, 1, 1) + relativedelta(months=1),
        billing_cycle="Monthly",
        usage_frequency="Daily",
        usage_hours=2.0,
        priority="High",
        user_id=user.id,
    )
    sub2 = Subscription(
        service_name="GitHub Pro",
        monthly_cost=330.0,
        category="Productivity",
        start_date=date(2026, 1, 1),
        renewal_date=date(2026, 1, 1) + relativedelta(months=1),
        billing_cycle="Monthly",
        usage_frequency="Daily",
        usage_hours=5.0,
        priority="High",
        user_id=user.id,
    )
    db.session.add_all([sub1, sub2])
    db.session.commit()

    # Obtain a real JWT token via the API login endpoint
    # (identity is always str(user.id) as per auth_service convention)
    login_resp = client.post(
        "/api/login",
        json={"email": "chatbot@example.com", "password": "Password123!"},
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.get_json()}"
    token = login_resp.get_json()["data"]["access_token"]

    return user, token



# ---------------------------------------------------------------------------
# Test A — Authenticated relevant question returns successful response
# ---------------------------------------------------------------------------

def test_authenticated_relevant_question_returns_response(app, client, authenticated_user):
    """Authenticated user asking a relevant subscription question gets a response."""
    user, token = authenticated_user

    mock_response = "You are spending ₹979.00 per month across 2 active subscriptions."

    with patch("services.chat_service._call_groq", return_value=mock_response):
        resp = client.post(
            "/api/chat",
            json={"message": "How much am I spending every month?", "page": "dashboard"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert "response" in data["data"]
    assert data["data"]["response"] == mock_response


# ---------------------------------------------------------------------------
# Test B — Unauthenticated request returns 401
# ---------------------------------------------------------------------------

def test_unauthenticated_request_returns_401(client):
    """POST /api/chat without a token must return 401."""
    resp = client.post(
        "/api/chat",
        json={"message": "How much am I spending?"},
    )
    assert resp.status_code == 401
    data = resp.get_json()
    assert data["success"] is False


# ---------------------------------------------------------------------------
# Test C — Out-of-scope question: controlled refusal, Groq NOT called
# ---------------------------------------------------------------------------

def test_out_of_scope_question_returns_refusal_without_calling_groq(app, client, authenticated_user):
    """Out-of-scope question must return the controlled refusal and NOT call Groq."""
    user, token = authenticated_user

    with patch("services.chat_service._call_groq") as mock_groq:
        resp = client.post(
            "/api/chat",
            json={"message": "What is machine learning?"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    # Controlled refusal message must reference the app's domain
    assert "Subscription Advisor" in data["data"]["response"]
    # Groq must NEVER have been called for an out-of-scope question
    mock_groq.assert_not_called()


def test_general_knowledge_question_returns_refusal_without_calling_groq(app, client, authenticated_user):
    """Another out-of-scope check — general knowledge should be refused."""
    user, token = authenticated_user

    with patch("services.chat_service._call_groq") as mock_groq:
        resp = client.post(
            "/api/chat",
            json={"message": "Who is the president of India?"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    mock_groq.assert_not_called()


# ---------------------------------------------------------------------------
# Test D — User isolation: only authenticated user's subscriptions are fetched
# ---------------------------------------------------------------------------

def test_user_isolation_only_fetches_authenticated_user_subscriptions(app, client, authenticated_user):
    """
    Verifies that the subscription context built for the chatbot only
    includes records belonging to the authenticated user, not another user.
    """
    user, token = authenticated_user
    auth_svc = AuthService()

    # Create a second user with their own subscription (already in app context from fixture)
    from datetime import date
    from dateutil.relativedelta import relativedelta

    other_user = auth_svc.register_user(
        username="other_user",
        email="other@example.com",
        mobile_number="9000000002",
        password="Password123!",
        occupation="Teacher",
        financial_preference="Money Saver",
    )
    auth_svc.verify_email(other_user.verification_token)

    other_sub = Subscription(
        service_name="PRIVATE_OTHER_USER_SUB",
        monthly_cost=5000.0,
        category="Other",
        start_date=date(2026, 1, 1),
        renewal_date=date(2026, 1, 1) + relativedelta(months=1),
        billing_cycle="Monthly",
        usage_frequency="Monthly",
        usage_hours=1.0,
        priority="Low",
        user_id=other_user.id,
    )
    db.session.add(other_sub)
    db.session.commit()

    # Intercept the context that gets built and inspect it
    captured_context = {}

    original_build = __import__(
        "services.chat_service", fromlist=["_build_subscription_context"]
    )._build_subscription_context

    def capturing_build(usr, page):
        ctx = original_build(usr, page)
        captured_context.update(ctx)
        return ctx

    with patch("services.chat_service._build_subscription_context", side_effect=capturing_build):
        with patch("services.chat_service._call_groq", return_value="You have 2 subscriptions."):
            resp = client.post(
                "/api/chat",
                json={"message": "How many subscriptions do I have?"},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert resp.status_code == 200
    # The captured context must NOT contain the other user's subscription
    sub_names = [s["name"] for s in captured_context.get("subscriptions", [])]
    assert "PRIVATE_OTHER_USER_SUB" not in sub_names
    # And it must contain the authenticated user's subscriptions
    assert "Netflix" in sub_names
    assert "GitHub Pro" in sub_names


# ---------------------------------------------------------------------------
# Test E — Missing / empty message returns 400
# ---------------------------------------------------------------------------

def test_missing_message_field_returns_400(app, client, authenticated_user):
    """Request body with no 'message' key must return 400."""
    user, token = authenticated_user

    resp = client.post(
        "/api/chat",
        json={"page": "dashboard"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["success"] is False


def test_empty_message_returns_400(app, client, authenticated_user):
    """Request body with empty string message must return 400."""
    user, token = authenticated_user

    resp = client.post(
        "/api/chat",
        json={"message": "   ", "page": "dashboard"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["success"] is False


def test_message_too_long_returns_400(app, client, authenticated_user):
    """Message exceeding 2000 characters must return 400."""
    user, token = authenticated_user

    long_message = "subscription " * 200  # well over 2000 chars

    resp = client.post(
        "/api/chat",
        json={"message": long_message},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["success"] is False


# ---------------------------------------------------------------------------
# Test F — Groq failure returns safe error, no provider details
# ---------------------------------------------------------------------------

def test_groq_api_failure_returns_safe_503_without_leaking_provider_details(app, client, authenticated_user):
    """When Groq raises an AppException, the response must be safe and opaque."""
    user, token = authenticated_user

    with patch(
        "services.chat_service._call_groq",
        side_effect=AppException("The advisor service encountered an error. Please try again.", status_code=503),
    ):
        resp = client.post(
            "/api/chat",
            json={"message": "How much am I spending on subscriptions?"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 503
    data = resp.get_json()
    assert data["success"] is False
    # Must not leak Groq-specific details, API keys, or stack traces
    response_text = str(data)
    assert "GROQ_API_KEY" not in response_text
    assert "groq" not in response_text.lower() or "groq" not in data.get("message", "").lower()
    assert "traceback" not in response_text.lower()


def test_groq_timeout_returns_safe_error(app, client, authenticated_user):
    """When Groq times out, the response must be safe."""
    user, token = authenticated_user

    with patch(
        "services.chat_service._call_groq",
        side_effect=AppException("Advisor response timed out. Please try again shortly.", status_code=503),
    ):
        resp = client.post(
            "/api/chat",
            json={"message": "What are my upcoming renewals?"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 503
    data = resp.get_json()
    assert data["success"] is False
    # User-friendly message should not mention Groq internals
    assert "GROQ" not in data.get("message", "")
