"""End-to-end integration test verifying full JWT authentication migration."""

from pathlib import Path
import pytest
from flask import Flask
from flask_jwt_extended import JWTManager

from config import Config
from database.db import db
from models.user import User
from models.subscription import Subscription
from routes.auth import auth
from routes.api import api
import routes.subscription  # noqa: F401
from utils.currency import format_inr
from services.auth_service import AuthService
from werkzeug.security import generate_password_hash


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-that-is-at-least-32-bytes-long"
    JWT_SECRET_KEY = "test-secret-that-is-at-least-32-bytes-long"
    WTF_CSRF_ENABLED = False


@pytest.fixture
def app():
    test_app = Flask(__name__, template_folder=str(Path(__file__).resolve().parents[1] / "templates"))
    test_app.config.from_object(TestConfig)

    test_app.jinja_env.filters['inr'] = format_inr
    test_app.jinja_env.globals['format_inr'] = format_inr

    db.init_app(test_app)
    jwt = JWTManager(test_app)

    @jwt.unauthorized_loader
    def unauthorized_loader(callback):
        return {"success": False, "message": "Missing or invalid token"}, 401

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


def test_full_web_user_journey(app, client):
    """Test full web workflow: register -> verify -> login (JWT cookie) -> dashboard -> subscription CRUD -> logout."""
    auth_service = AuthService()

    # 1. Register & Verify user
    with app.app_context():
        user = auth_service.register_user(
            username="journey_user",
            email="journey@example.com",
            mobile_number="9876500001",
            password="Password123!",
            occupation="Engineer",
            financial_preference="Balanced",
        )
        auth_service.verify_email(user.verification_token)

    # 2. Unauthenticated user accessing /dashboard should be redirected to /login
    unauth_resp = client.get("/dashboard", follow_redirects=False)
    assert unauth_resp.status_code == 302
    assert "/login" in unauth_resp.headers["Location"]

    # 3. Login via web form (should set JWT access cookie)
    login_resp = client.post(
        "/login",
        data={"email": "journey@example.com", "password": "Password123!"},
        follow_redirects=False,
    )
    assert login_resp.status_code == 302
    assert "/dashboard" in login_resp.headers["Location"]
    cookie_header = login_resp.headers.get("Set-Cookie", "")
    assert "access_token_cookie" in cookie_header

    # 4. Access dashboard with JWT cookie (follow redirect)
    dash_resp = client.get("/dashboard")
    assert dash_resp.status_code == 200
    assert b"journey_user" in dash_resp.data

    # 5. Add subscription via web form
    add_resp = client.post(
        "/add-subscription",
        data={
            "service_name": "Spotify Premium",
            "monthly_cost": "119",
            "category": "Entertainment",
            "start_date": "2026-01-01",
            "billing_cycle": "Monthly",
            "usage_frequency": "Daily",
            "usage_hours": "2",
        },
        follow_redirects=True,
    )
    assert add_resp.status_code == 200
    assert b"Spotify Premium" in add_resp.data

    # 6. Profile page
    profile_resp = client.get("/profile")
    assert profile_resp.status_code == 200
    assert b"journey_user" in profile_resp.data

    # 7. Logout (unsets cookie and redirects to login)
    logout_resp = client.get("/logout", follow_redirects=True)
    assert logout_resp.status_code == 200

    # 8. Dashboard should now redirect back to /login
    post_logout_resp = client.get("/dashboard", follow_redirects=False)
    assert post_logout_resp.status_code == 302
    assert "/login" in post_logout_resp.headers["Location"]


def test_full_api_user_journey(app, client):
    """Test REST API JWT workflow: /api/login -> Bearer token -> /api/profile -> 401 on unauth."""
    auth_service = AuthService()

    with app.app_context():
        user = auth_service.register_user(
            username="api_jwt_user",
            email="apijwt@example.com",
            mobile_number="9876500002",
            password="Password123!",
            occupation="Analyst",
            financial_preference="Money Saver",
        )
        auth_service.verify_email(user.verification_token)

    # 1. Unauthenticated API request should return 401 JSON
    unauth_api = client.get("/api/subscriptions")
    assert unauth_api.status_code == 401
    assert unauth_api.is_json
    assert unauth_api.json["success"] is False

    # 2. Login via /api/login
    login_resp = client.post(
        "/api/login",
        json={"email": "apijwt@example.com", "password": "Password123!"},
    )
    assert login_resp.status_code == 200
    data = login_resp.json
    assert "access_token" in data["data"]
    token = data["data"]["access_token"]

    # 3. Authenticated API request with Bearer token
    auth_api = client.get(
        "/api/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert auth_api.status_code == 200
    assert auth_api.json["success"] is True
    assert auth_api.json["data"]["user"]["username"] == "api_jwt_user"
