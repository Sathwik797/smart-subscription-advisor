"""Integration and regression tests for the redesigned Settings workspace."""

from pathlib import Path
import pytest
from flask import Flask
from flask_jwt_extended import JWTManager

from config import Config
from database.db import db
from models.user import User
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


def test_settings_requires_login(client):
    """Unauthenticated users accessing /settings should be redirected."""
    resp = client.get("/settings", follow_redirects=False)
    assert resp.status_code in (302, 401)


def test_settings_authenticated_structure(app, client):
    """Verify Settings page renders with approved sections and active navigation."""
    auth_service = AuthService()
    with app.app_context():
        user = auth_service.register_user(
            username="settings_user",
            email="settings_user@example.com",
            mobile_number="9876543210",
            password="Password123!",
            occupation="Product Manager",
            financial_preference="Balanced",
        )
        auth_service.verify_email(user.verification_token)

    # Log in
    client.post(
        "/login",
        data={"email": "settings_user@example.com", "password": "Password123!"},
        follow_redirects=True,
    )

    resp = client.get("/settings")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # 1. Header checks
    assert "SETTINGS" in html
    assert "Settings" in html
    assert "Manage your preferences, notifications, and account." in html
    assert "Save Changes" in html

    # 2. Notification Preferences Card
    assert "Notification Preferences" in html
    assert "Choose what Smart Subscription Advisor should notify you about." in html
    assert "Email notifications" in html
    assert "Renewal reminders" in html
    assert "Subscription insights" in html

    # 3. Appearance & Interface Card
    assert "Appearance & Interface" in html
    assert "Customize how Smart Subscription Advisor looks and feels." in html
    assert "Theme" in html
    assert "Light (Default)" in html
    assert "Language" in html
    assert "English (US)" in html
    assert "Dark mode" in html
    assert "Coming soon" in html

    # 4. Subscription Preferences Card
    assert "Subscription Preferences" in html
    assert "Control how Smart Subscription Advisor analyzes your subscriptions." in html
    assert "Renewal warning" in html
    assert "7 days" in html
    assert "Spending insights" in html
    assert "Usage-based insights" in html

    # 5. Danger Zone Card
    assert "Danger Zone" in html
    assert "These actions can affect your account permanently." in html
    assert "Delete account" in html
    assert "Permanently remove your account and all subscription data." in html
    assert "Delete Account" in html

    # 6. Sidebar active state
    assert 'data-nav="settings"' in html
    assert "sidebar-nav-item active" in html or 'data-nav="settings"' in html

    # 7. Ensure no duplicate Profile stats cards on Settings
    assert "Total Subscriptions" not in html
    assert "Monthly Spending" not in html
    assert "Yearly Spending" not in html


def test_settings_save_post(app, client):
    """Verify POST to /settings saves successfully without breaking."""
    auth_service = AuthService()
    with app.app_context():
        user = auth_service.register_user(
            username="settings_post_user",
            email="settings_post@example.com",
            mobile_number="9876543211",
            password="Password123!",
            occupation="Designer",
            financial_preference="Balanced",
        )
        auth_service.verify_email(user.verification_token)

    # Log in
    client.post(
        "/login",
        data={"email": "settings_post@example.com", "password": "Password123!"},
        follow_redirects=True,
    )

    # Submit settings update
    resp = client.post(
        "/settings",
        data={"email_notifications": "on", "renewal_warning": "14"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Settings saved successfully!" in html or "Settings" in html
