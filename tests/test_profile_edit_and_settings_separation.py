"""Integration tests verifying strict separation between Edit Profile and Settings workspaces."""

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


def test_edit_profile_page_structure(app, client):
    """Verify /profile/edit renders dedicated edit_profile.html without Settings sections."""
    auth_service = AuthService()
    with app.app_context():
        user = auth_service.register_user(
            username="editor_user",
            email="editor@example.com",
            mobile_number="9876543201",
            password="Password123!",
            occupation="Product Designer",
            financial_preference="Balanced",
        )
        auth_service.verify_email(user.verification_token)

    # Log in
    client.post(
        "/login",
        data={"email": "editor@example.com", "password": "Password123!"},
        follow_redirects=True,
    )

    resp = client.get("/profile/edit")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # 1. Edit Profile header & cards
    assert "ACCOUNT WORKSPACE" in html
    assert "Edit Profile" in html
    assert "Update your personal information and account preferences." in html
    assert "Personal Details" in html
    assert "Username" in html
    assert "Email address" in html
    assert "Occupation" in html
    assert "Financial preference" in html
    assert "Save Changes" in html
    assert "Back to Profile" in html

    # 2. Must NOT contain Settings sections
    assert "Notification Preferences" not in html
    assert "Appearance & Interface" not in html
    assert "Subscription Preferences" not in html
    assert "Danger Zone" not in html
    assert "Dark mode" not in html

    # 3. Contextual sidebar navigation MUST be Profile, NOT Settings
    assert 'data-nav="profile"' in html
    assert 'data-nav="settings"' in html
    # Profile link should be marked active or active_nav == 'profile'
    assert 'data-nav="profile"' in html


def test_edit_profile_post_update_functionality(app, client):
    """Verify updating personal information via /profile/edit works and redirects to profile."""
    auth_service = AuthService()
    with app.app_context():
        user = auth_service.register_user(
            username="update_target_user",
            email="target@example.com",
            mobile_number="9876543202",
            password="Password123!",
            occupation="Student",
            financial_preference="Balanced",
        )
        auth_service.verify_email(user.verification_token)

    # Log in
    client.post(
        "/login",
        data={"email": "target@example.com", "password": "Password123!"},
        follow_redirects=True,
    )

    cookie = client.get_cookie("csrf_access_token")
    csrf_token = cookie.value if cookie else ""

    # Submit profile update
    post_resp = client.post(
        "/profile/edit",
        data={
            "csrf_token": csrf_token,
            "username": "updated_new_name",
            "occupation": "Software Developer",
            "financial_preference": "Money Saver",
        },
        follow_redirects=True,
    )
    assert post_resp.status_code == 200
    html = post_resp.get_data(as_text=True)

    # Verify redirected to profile with updated details
    assert "updated_new_name" in html
    assert "Software Developer" in html
    assert "Money Saver" in html
    assert "Profile updated successfully!" in html


def test_settings_page_does_not_contain_edit_profile_form(app, client):
    """Verify /settings renders settings.html and does NOT render the Edit Profile form."""
    auth_service = AuthService()
    with app.app_context():
        user = auth_service.register_user(
            username="settings_distinct_user",
            email="distinct@example.com",
            mobile_number="9876543203",
            password="Password123!",
            occupation="Working Professional",
            financial_preference="Convenience",
        )
        auth_service.verify_email(user.verification_token)

    # Log in
    client.post(
        "/login",
        data={"email": "distinct@example.com", "password": "Password123!"},
        follow_redirects=True,
    )

    resp = client.get("/settings")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # 1. Must contain Settings sections
    assert "SETTINGS" in html
    assert "Settings" in html
    assert "Notification Preferences" in html
    assert "Appearance & Interface" in html
    assert "Subscription Preferences" in html
    assert "Danger Zone" in html

    # 2. Must NOT contain Edit Profile specific elements
    assert "Personal Details" not in html
    assert "Back to Profile" not in html
    assert 'name="username"' not in html

    # 3. Contextual sidebar navigation MUST be Settings
    assert 'data-nav="settings"' in html
