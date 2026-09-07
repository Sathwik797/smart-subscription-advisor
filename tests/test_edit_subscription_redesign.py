"""Targeted tests for Edit Subscription page redesign."""

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
    test_app.jinja_env.globals['zip'] = zip

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
def auth_user_and_sub(app, client):
    auth_service = AuthService()
    with app.app_context():
        user = auth_service.register_user(
            username="editsub_user",
            email="editsub@example.com",
            mobile_number="9876543210",
            password="Password123!",
            occupation="Professional",
            financial_preference="Balanced"
        )
        auth_service.verify_email(user.verification_token)
        user_id = user.id

        sub = Subscription(
            user_id=user_id,
            service_name="Amazon Prime",
            monthly_cost=249.0,
            category="Entertainment",
            start_date=date(2026, 9, 6),
            renewal_date=date(2026, 10, 6),
            billing_cycle="Monthly",
            usage_frequency="Daily",
            usage_hours=1.0,
            priority="Low"
        )
        db.session.add(sub)
        db.session.commit()
        sub_id = sub.id

    client.post(
        "/login",
        data={"email": "editsub@example.com", "password": "Password123!"},
        follow_redirects=False
    )
    return user_id, sub_id


def test_edit_subscription_requires_auth(client):
    res = client.get("/edit-subscription/1")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]


def test_edit_subscription_page_loads_and_has_reference_hierarchy(client, auth_user_and_sub):
    user_id, sub_id = auth_user_and_sub
    res = client.get(f"/edit-subscription/{sub_id}")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # Product Branding
    assert "SmartSub" not in html
    assert "Smart Subscription Advisor" in html

    # Page Header
    assert "SUBSCRIPTION WORKSPACE" in html
    assert "Edit Subscription" in html
    assert "Back to Subscriptions" in html

    # Left Card: Subscription Details & Usage & Value
    assert "Subscription Details" in html
    assert 'name="service_name"' in html
    assert 'value="Amazon Prime"' in html
    assert 'name="monthly_cost"' in html
    assert 'name="billing_cycle"' in html
    assert 'name="start_date"' in html
    assert 'name="category"' in html
    assert "Usage &amp; Value" in html or "Usage & Value" in html
    assert 'name="usage_frequency"' in html
    assert 'name="usage_hours"' in html
    assert "Usage guide:" in html
    assert "Save Changes" in html

    # Right Card: ONLY Subscription Snapshot (Quick Tips and Secure by design REMOVED)
    assert "Subscription Snapshot" in html
    assert "Quick tips" not in html
    assert "Quick Tips" not in html
    assert "Secure by design" not in html
    assert "Current priority" in html
    assert "Stay in control" in html

    # Full-width Bottom Card: Smart Subscription Insights
    assert "Smart Subscription Insights" in html
    assert "Subscription score" in html
    assert "Why this matters" in html
    assert "Recommendation" in html

    # Chatbot inclusion
    assert "Ask AI" in html
    assert "chatbot-badge-tip" in html


def test_edit_subscription_form_submission_updates_db(client, auth_user_and_sub):
    user_id, sub_id = auth_user_and_sub
    cookie = client.get_cookie("csrf_access_token")
    csrf_token = cookie.value if cookie else ""
    res = client.post(
        f"/edit-subscription/{sub_id}",
        data={
            "csrf_token": csrf_token,
            "service_name": "Amazon Prime Video",
            "monthly_cost": "299",
            "category": "Entertainment",
            "start_date": "2026-09-01",
            "billing_cycle": "Yearly",
            "usage_frequency": "Weekly",
            "usage_hours": "5"
        },
        follow_redirects=True
    )
    assert res.status_code == 200

    updated = db.session.get(Subscription, sub_id)
    assert updated is not None
    assert updated.service_name == "Amazon Prime Video"
    assert updated.monthly_cost == 299.0
    assert updated.billing_cycle == "Yearly"
    assert updated.usage_frequency == "Weekly"
    assert updated.usage_hours == 5.0
