"""Comprehensive tests for global collapsible sidebar and authenticated navigation."""

from pathlib import Path
import pytest
from flask import Flask
from flask_jwt_extended import JWTManager
from datetime import datetime, date

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


@pytest.fixture
def authenticated_client(app, client):
    auth_service = AuthService()
    with app.app_context():
        user = auth_service.register_user(
            username="nav_tester",
            email="nav_tester@example.com",
            mobile_number="9876543299",
            password="Password123!",
            occupation="Engineer",
            financial_preference="Optimized",
        )
        auth_service.verify_email(user.verification_token)
        user_id = user.id

        sub = Subscription(
            user_id=user_id,
            service_name="Spotify",
            category="Music",
            monthly_cost=119.0,
            billing_cycle="Monthly",
            start_date=date(2024, 1, 1),
            renewal_date=date(2026, 10, 3)
        )
        db.session.add(sub)
        db.session.commit()

    login_resp = client.post(
        "/login",
        data={"email": "nav_tester@example.com", "password": "Password123!"},
        follow_redirects=False,
    )
    assert login_resp.status_code in (200, 302)
    return client


def test_sidebar_rendered_on_dashboard(authenticated_client):
    res = authenticated_client.get("/dashboard")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # Reusable sidebar shell & toggle
    assert 'id="appSidebar"' in html
    assert 'id="sidebarToggle"' in html
    assert 'class="dashboard-sidebar' in html

    # Navigation items & tooltips
    assert 'data-nav="dashboard"' in html
    assert 'data-nav="subscriptions"' in html
    assert 'data-nav="add_subscription"' in html
    assert 'data-nav="recommendations"' in html
    assert 'data-nav="analytics"' in html
    assert 'data-nav="profile"' in html
    assert 'data-nav="settings"' in html
    assert 'data-nav="logout"' in html

    # Tooltip contents
    assert '<span class="sidebar-tooltip">Dashboard</span>' in html
    assert '<span class="sidebar-tooltip">Subscriptions</span>' in html
    assert '<span class="sidebar-tooltip">Add Subscription</span>' in html
    assert '<span class="sidebar-tooltip">Recommendations</span>' in html
    assert '<span class="sidebar-tooltip">Analytics</span>' in html
    assert '<span class="sidebar-tooltip">Profile</span>' in html
    assert '<span class="sidebar-tooltip">Settings</span>' in html
    assert '<span class="sidebar-tooltip">Sign Out</span>' in html

    # Active state for dashboard
    assert 'data-nav="dashboard"' in html
    assert 'sidebar-nav-item active"\n           data-nav="dashboard"' in html or 'sidebar-nav-item active' in html

    # Product name branding
    assert "Smart Subscription Advisor" in html
    assert "SmartSub" not in html


def test_sidebar_rendered_on_subscriptions(authenticated_client):
    res = authenticated_client.get("/subscriptions")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    assert 'id="appSidebar"' in html
    assert 'id="sidebarToggle"' in html
    assert 'data-nav="subscriptions"' in html
    assert 'sidebar-nav-item active' in html

    # Subscriptions table columns present
    assert "Service" in html
    assert "Category" in html
    assert "Billing Cycle" in html
    assert "Next Renewal" in html
    assert "Monthly Cost" in html
    assert "Status" in html
    assert "Actions" in html

    # Summary and Tips cards
    assert "Subscription Summary" in html
    assert "Subscription Tips" in html
    assert "Review unused subscriptions" in html


def test_sidebar_rendered_on_add_subscription(authenticated_client):
    res = authenticated_client.get("/add-subscription")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    assert 'id="appSidebar"' in html
    assert 'id="sidebarToggle"' in html
    assert 'data-nav="add_subscription"' in html


def test_sidebar_rendered_on_edit_subscription(app, authenticated_client):
    with app.app_context():
        sub = Subscription.query.first()
        sub_id = sub.id

    res = authenticated_client.get(f"/edit-subscription/{sub_id}")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    assert 'id="appSidebar"' in html
    assert 'id="sidebarToggle"' in html
    assert 'data-nav="subscriptions"' in html


def test_sidebar_rendered_on_analytics(authenticated_client):
    res = authenticated_client.get("/spending-analytics")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    assert 'id="appSidebar"' in html
    assert 'id="sidebarToggle"' in html
    assert 'data-nav="analytics"' in html


def test_sidebar_rendered_on_profile(authenticated_client):
    res = authenticated_client.get("/profile")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    assert 'id="appSidebar"' in html
    assert 'id="sidebarToggle"' in html
    assert 'data-nav="profile"' in html


def test_sidebar_rendered_on_edit_profile(authenticated_client):
    res = authenticated_client.get("/profile/edit")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    assert 'id="appSidebar"' in html
    assert 'id="sidebarToggle"' in html
    assert 'data-nav="profile"' in html


def test_sidebar_rendered_on_settings(authenticated_client):
    res = authenticated_client.get("/settings")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    assert 'id="appSidebar"' in html
    assert 'id="sidebarToggle"' in html
    assert 'data-nav="settings"' in html


def test_sidebar_script_and_style_in_base(authenticated_client):
    res = authenticated_client.get("/dashboard")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    assert "sidebar.css" in html
    assert "sidebar.js" in html
    assert "smartSubscriptionAdvisor.sidebarCollapsed" in html
