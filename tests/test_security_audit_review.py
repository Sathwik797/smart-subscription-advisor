"""Focused security and authentication verification tests for Phase 1.4 audit."""

from pathlib import Path
import pytest
from flask import Flask
from flask_jwt_extended import JWTManager

from config import Config
from database.db import db
from exceptions.error_handlers import register_error_handlers
from models.user import User
from routes.auth import auth
from routes.api import api
import routes.subscription  # noqa: F401
from services.auth_service import AuthService
from utils.currency import format_inr
from middleware.rate_limiter import limiter


class TestSecurityConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-that-is-at-least-32-bytes-long"
    JWT_SECRET_KEY = "test-secret-that-is-at-least-32-bytes-long"
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = True


@pytest.fixture
def app():
    test_app = Flask(__name__, template_folder=str(Path(__file__).resolve().parents[1] / "templates"))
    test_app.config.from_object(TestSecurityConfig)

    test_app.jinja_env.filters["inr"] = format_inr
    test_app.jinja_env.globals["format_inr"] = format_inr

    db.init_app(test_app)
    limiter.init_app(test_app)
    jwt = JWTManager(test_app)

    @test_app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    @jwt.unauthorized_loader
    def unauthorized_loader(callback):
        return {"success": False, "message": "Missing or invalid token"}, 401

    @test_app.route("/")
    def index():
        return "OK"

    register_error_handlers(test_app)
    test_app.register_blueprint(auth)
    test_app.register_blueprint(api, url_prefix="/api")

    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_security_headers_present_on_responses(client):
    """Verify essential HTTP security headers are returned on all responses."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    # Also on 404 or auth endpoints
    login_resp = client.get("/login")
    assert login_resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert login_resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert login_resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_login_does_not_enumerate_accounts(client):
    """Verify login failure gives identical message for wrong password and non-existent email."""
    resp_no_user = client.post("/login", data={"email": "nonexistent@example.com", "password": "Password123!"})
    assert "Invalid email or password." in resp_no_user.get_data(as_text=True)

    resp_api = client.post("/api/login", json={"email": "nonexistent@example.com", "password": "Password123!"})
    assert resp_api.status_code == 401
    assert "Invalid email or password." in resp_api.get_json()["message"]


def test_password_reset_does_not_enumerate_email(client):
    """Verify forgot-password gives identical message regardless of whether email exists."""
    resp_web = client.post("/forgot-password", data={"email": "nobody@example.com"}, follow_redirects=True)
    assert resp_web.status_code == 200
    assert "If an account with that email exists" in resp_web.get_data(as_text=True)

    resp_api = client.post("/api/forgot-password", json={"email": "nobody@example.com"})
    assert resp_api.status_code == 200
    assert "If an account with that email exists" in resp_api.get_json()["message"]


def test_unauthenticated_protected_route_rejected(client):
    """Verify accessing protected routes without auth redirects to login or returns 401."""
    resp_dash = client.get("/dashboard", follow_redirects=False)
    assert resp_dash.status_code == 302
    assert "/login" in resp_dash.headers["Location"]

    resp_api_sub = client.get("/api/subscriptions")
    assert resp_api_sub.status_code == 401
    assert resp_api_sub.get_json()["success"] is False


def test_password_reset_token_cannot_be_reused(app):
    """Verify reset token is invalidated immediately upon successful password change."""
    auth_service = AuthService()
    with app.app_context():
        user = auth_service.register_user(
            username="reset_security_user",
            email="reset_sec@example.com",
            mobile_number="9876543290",
            password="OriginalPassword123!",
            occupation="Dev",
            financial_preference="Balanced",
        )
        auth_service.request_password_reset("reset_sec@example.com")
        updated_user = User.query.filter_by(email="reset_sec@example.com").first()
        token = updated_user.reset_token
        assert token is not None

        # First reset succeeds
        auth_service.reset_password(token, "NewSecurePassword123!")

        # Token was cleared
        reloaded = User.query.filter_by(email="reset_sec@example.com").first()
        assert reloaded.reset_token is None

        # Second attempt with same token fails
        from exceptions.exceptions import ValidationException
        with pytest.raises(ValidationException) as exc:
            auth_service.reset_password(token, "AnotherPassword123!")
        assert "Invalid or expired" in str(exc.value)
