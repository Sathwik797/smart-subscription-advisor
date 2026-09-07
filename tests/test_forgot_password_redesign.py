"""Regression and integration tests for the redesigned Forgot Password page."""
from pathlib import Path
import pytest
from flask import Flask
from flask_jwt_extended import JWTManager

from config import Config
from database.db import db
from routes.auth import auth
from routes.api import api
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
    test_app = Flask(__name__, template_folder=str(Path(__file__).resolve().parents[1] / "templates"), static_folder=str(Path(__file__).resolve().parents[1] / "static"))
    test_app.config.from_object(TestConfig)

    test_app.jinja_env.filters['inr'] = format_inr
    test_app.jinja_env.globals['format_inr'] = format_inr

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


def test_forgot_password_get(client):
    """Verify Forgot Password page structure and content matches design requirements."""
    response = client.get("/forgot-password")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # 1. Authentication Header
    assert 'class="auth-header"' in html
    assert 'class="auth-brand-mark">SA</span>' in html
    assert 'Smart Subscription Advisor' in html
    assert 'class="auth-back-link"' in html
    assert 'Back to Login' in html
    assert '/login' in html

    # 2. Main Centered Card
    assert 'class="forgot-card"' in html
    assert 'class="forgot-icon-wrap"' in html
    assert '<svg' in html
    assert 'Forgot Password?' in html
    assert "Enter your email address and we&#39;ll send you a password reset link." in html or "Enter your email address and we'll send you a password reset link." in html

    # 3. Form
    assert 'action="/forgot-password"' in html
    assert 'name="email"' in html
    assert 'type="email"' in html
    assert 'placeholder="you@example.com"' in html
    assert 'input-leading-icon' in html
    assert 'bi-envelope' in html

    # 4. Submit Button
    assert 'btn-reset-submit' in html
    assert 'Send Reset Link' in html
    assert 'bi-arrow-right' in html

    # 5. Recovery Links
    assert 'Remembered your password?' in html
    assert 'recovery-link' in html

    # 6. Footer
    assert '© 2026 Smart Subscription Advisor. All rights reserved.' in html

    # 7. Authenticated Dashboard Sidebar should NOT be rendered
    assert 'class="app-sidebar"' not in html
    assert 'class="sidebar-nav"' not in html


def test_forgot_password_post_invalid_email(client):
    """Verify validation error handling on invalid email."""
    response = client.post("/forgot-password", data={"email": "invalid-email"})
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "forgot-card-alert" in html
    assert "alert-danger" in html


def test_forgot_password_post_empty_email(client):
    """Verify validation error handling on empty email."""
    response = client.post("/forgot-password", data={"email": ""})
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "forgot-card-alert" in html
    assert "alert-danger" in html
