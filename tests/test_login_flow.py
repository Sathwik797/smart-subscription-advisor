"""Targeted tests for Smart Subscription Advisor Login flow (email verification removed)."""
from pathlib import Path
import pytest
from flask import Flask
from flask_jwt_extended import JWTManager

from config import Config
from database.db import db
from models.user import User
from routes.auth import auth
from routes.api import api
from services.auth_service import AuthService
from exceptions.exceptions import AuthenticationException
from utils.currency import format_inr
from middleware.rate_limiter import limiter


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-that-is-at-least-32-bytes-long"
    JWT_SECRET_KEY = "test-secret-that-is-at-least-32-bytes-long"
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False


@pytest.fixture
def app():
    test_app = Flask(
        __name__,
        template_folder=str(Path(__file__).resolve().parents[1] / "templates"),
        static_folder=str(Path(__file__).resolve().parents[1] / "static"),
    )
    test_app.config.from_object(TestConfig)

    test_app.jinja_env.filters["inr"] = format_inr
    test_app.jinja_env.globals["format_inr"] = format_inr

    db.init_app(test_app)
    limiter.init_app(test_app)
    JWTManager(test_app)

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


@pytest.fixture
def auth_service():
    return AuthService()


def test_login_page_renders_without_verification_ui(client):
    """GET /login should display clean login card without any verification alert/resend button."""
    response = client.get("/login")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "Smart Subscription Advisor" in html
    assert "Log in to your account" in html
    assert "Forgot password?" in html
    assert "/forgot-password" in html

    # Verification warning & resend link should be completely absent
    assert "Please verify your email before logging in" not in html
    assert "Resend Verification Email" not in html
    assert "btn-resend-link" not in html


def test_unverified_registered_user_login_succeeds(app, auth_service, client):
    """Unverified registered user with correct password logs in successfully."""
    with app.app_context():
        user = auth_service.register_user(
            username="unverified_bob",
            email="bob_unverified@example.com",
            mobile_number="9876543210",
            password="SecurePassword123!",
            occupation="Developer",
            financial_preference="Saver",
        )
        assert user.email_verified is False

        # Service-level authentication succeeds
        authed_user = auth_service.authenticate_user("bob_unverified@example.com", "SecurePassword123!")
        assert authed_user is not None
        assert authed_user.id == user.id

    # Web login POST succeeds and redirects to dashboard
    response = client.post(
        "/login",
        data={"email": "bob_unverified@example.com", "password": "SecurePassword123!"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/dashboard" or response.headers["Location"].endswith("/dashboard")
    assert "access_token_cookie" in response.headers.get("Set-Cookie", "")


def test_verified_registered_user_login_succeeds(app, auth_service, client):
    """Verified registered user with correct password logs in successfully."""
    with app.app_context():
        user = auth_service.register_user(
            username="verified_alice",
            email="alice_verified@example.com",
            mobile_number="9876543211",
            password="SecurePassword123!",
            occupation="Designer",
            financial_preference="Investor",
        )
        # Verify user
        auth_service.verify_email(user.verification_token)
        reloaded = db.session.get(User, user.id)
        assert reloaded.email_verified is True

        authed_user = auth_service.authenticate_user("alice_verified@example.com", "SecurePassword123!")
        assert authed_user is not None
        assert authed_user.id == user.id

    # Web login POST succeeds and redirects to dashboard
    response = client.post(
        "/login",
        data={"email": "alice_verified@example.com", "password": "SecurePassword123!"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/dashboard" or response.headers["Location"].endswith("/dashboard")


def test_incorrect_password_login_fails(app, auth_service, client):
    """Registered user with wrong password cannot log in."""
    with app.app_context():
        auth_service.register_user(
            username="charlie_test",
            email="charlie@example.com",
            mobile_number="9876543212",
            password="CorrectPassword123!",
            occupation="Teacher",
            financial_preference="Balanced",
        )

        with pytest.raises(AuthenticationException) as exc_info:
            auth_service.authenticate_user("charlie@example.com", "WrongPassword999!")
        assert "Invalid email or password" in str(exc_info.value)

    # Web login POST shows error
    response = client.post(
        "/login",
        data={"email": "charlie@example.com", "password": "WrongPassword999!"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Invalid email or password." in html
    assert "Please verify your email before logging in" not in html
    assert "Resend Verification Email" not in html


def test_unknown_email_login_fails(app, auth_service, client):
    """Non-existent email cannot log in."""
    with app.app_context():
        with pytest.raises(AuthenticationException) as exc_info:
            auth_service.authenticate_user("ghost@example.com", "SomePassword123!")
        assert "Invalid email or password" in str(exc_info.value)

    # Web login POST shows error
    response = client.post(
        "/login",
        data={"email": "ghost@example.com", "password": "SomePassword123!"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Invalid email or password." in html


def test_forgot_password_accessible(client):
    """Forgot password page and links remain intact and fully functional."""
    # From login page
    login_res = client.get("/login")
    assert "/forgot-password" in login_res.get_data(as_text=True)

    # Direct access
    response = client.get("/forgot-password")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Forgot Password?" in html
    assert "Send Reset Link" in html
