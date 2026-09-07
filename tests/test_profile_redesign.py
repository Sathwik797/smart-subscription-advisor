"""Regression and integration tests for the redesigned Profile workspace page."""

from pathlib import Path
from datetime import date
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


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-that-is-at-least-32-bytes-long"
    JWT_SECRET_KEY = "test-secret-that-is-at-least-32-bytes-long"
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False


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


def test_profile_requires_login(client):
    """Unauthenticated users should be redirected to login."""
    response = client.get("/profile", follow_redirects=False)
    assert response.status_code in (302, 401)


def test_profile_authenticated_structure_and_no_missing_data(app, client):
    """Verify profile renders clean architecture, identity, metrics, security, and no 'Not available'."""
    auth_service = AuthService()
    with app.app_context():
        user = auth_service.register_user(
            username="profile_fintech_user",
            email="fintech_user@example.com",
            mobile_number="9876500111",
            password="Password123!",
            occupation="Product Designer",
            financial_preference="Aggressive Saver",
        )
        auth_service.verify_email(user.verification_token)

    # Log in
    login_resp = client.post(
        "/login",
        data={"email": "fintech_user@example.com", "password": "Password123!"},
        follow_redirects=True,
    )
    assert login_resp.status_code == 200

    # Request Profile page
    resp = client.get("/profile")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # 1. Header checks
    assert "ACCOUNT WORKSPACE" in html
    assert "My Profile" in html
    assert "Manage your account information and preferences." in html
    assert "Edit Profile" in html

    # 2. Identity card
    assert "profile_fintech_user" in html
    assert "fintech_user@example.com" in html
    assert "Account active" in html
    assert "Account type" in html
    assert "Product Designer" in html
    assert "Glad to have you here!" in html
    assert "welcome-sprout-icon" in html

    # 3. Verify missing data is NOT rendered as prominent text
    assert "Member since Not available" not in html
    assert "Account ID Not available" not in html
    assert "Registration date Not available" not in html

    # 4. Account Information card
    assert "Account Information" in html
    assert "Your personal information and preferences." in html
    assert "Username" in html
    assert "Email address" in html
    assert "Occupation" in html
    assert "Financial preference" in html
    assert "Aggressive Saver" in html

    # 5. Account Overview card
    assert "Account Overview" in html
    assert "A quick overview of your subscription activity." in html
    assert "Subscriptions" in html
    assert "Monthly spending" in html
    assert "Yearly spending" in html
    assert "Upcoming renewals" in html
    assert "View your subscriptions" in html
    assert "/subscriptions" in html

    # 6. Security card
    assert "Security" in html
    assert "Keep your account secure." in html
    assert "••••••••••••" in html
    assert "Change password" in html
    assert "JWT protected session" in html
    assert "Active" in html

    # 7. Preferences and Danger Zone MUST BE REMOVED from profile
    assert "INTERFACE PREFERENCES" not in html
    assert "DANGER ZONE" not in html
    assert "Delete account" not in html
    assert "Renewal reminders" not in html
    assert "Dark mode" not in html


def test_profile_metrics_with_subscriptions(app, client):
    """Verify subscription metrics display accurately on the redesigned profile page."""
    auth_service = AuthService()
    with app.app_context():
        user = auth_service.register_user(
            username="profile_metrics_user",
            email="metrics_user@example.com",
            mobile_number="9876500222",
            password="Password123!",
            occupation="Fintech Lead",
            financial_preference="Balanced",
        )
        auth_service.verify_email(user.verification_token)
        user_id = user.id

        # Add 2 subscriptions: 649 (Netflix) and 149 (Spotify)
        sub1 = Subscription(
            user_id=user_id,
            service_name="Netflix",
            category="Entertainment",
            monthly_cost=649.0,
            billing_cycle="Monthly",
            start_date=date(2024, 1, 1),
            renewal_date=date(2026, 9, 20),
            priority="High",
        )
        sub2 = Subscription(
            user_id=user_id,
            service_name="Spotify",
            category="Music",
            monthly_cost=149.0,
            billing_cycle="Monthly",
            start_date=date(2024, 1, 1),
            renewal_date=date(2026, 9, 25),
            priority="Medium",
        )
        db.session.add_all([sub1, sub2])
        db.session.commit()

    # Log in
    login_resp = client.post(
        "/login",
        data={"email": "metrics_user@example.com", "password": "Password123!"},
        follow_redirects=True,
    )
    assert login_resp.status_code == 200

    resp = client.get("/profile")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # Total subscriptions should be 2
    assert "2" in html
    # Monthly spending should be 649 + 149 = 798 -> ₹798
    assert "₹798" in html
    # Yearly spending should be 798 * 12 = 9,576 -> ₹9,576
    assert "₹9,576" in html
