"""Targeted tests for Add Subscription page enhancements (Autocomplete, Default Billing Cycle, etc.)."""

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
def auth_user(app, client):
    auth_service = AuthService()
    with app.app_context():
        user = auth_service.register_user(
            username="addsub_user",
            email="addsub@example.com",
            mobile_number="9876543210",
            password="Password123!",
            occupation="Professional",
            financial_preference="Balanced"
        )
        auth_service.verify_email(user.verification_token)
        user_id = user.id

    client.post(
        "/login",
        data={"email": "addsub@example.com", "password": "Password123!"},
        follow_redirects=False
    )
    return user_id


def test_add_subscription_page_requires_auth(client):
    res = client.get("/add-subscription")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]


def test_add_subscription_page_loads_and_has_smart_autocomplete_elements(client, auth_user):
    res = client.get("/add-subscription")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # Autocomplete structure checks
    assert 'service-autocomplete-wrap' in html
    assert 'id="service-name"' in html
    assert 'id="serviceLogoIndicator"' in html
    assert 'id="serviceAutocompleteDropdown"' in html
    assert 'add_subscription.js' in html


def test_add_subscription_billing_cycle_defaults_to_monthly(client, auth_user):
    res = client.get("/add-subscription")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # Monthly is selected by default
    assert '<option value="Monthly" selected>' in html or '<option value="Monthly"\n' in html or 'value="Monthly" selected' in html
    assert 'value="Yearly"' in html


def test_add_subscription_form_submission_recognized_service(client, auth_user):
    # Test adding Netflix with Monthly billing cycle
    res = client.post(
        "/add-subscription",
        data={
            "service_name": "Netflix",
            "monthly_cost": "499",
            "category": "Entertainment",
            "start_date": "2026-09-01",
            "billing_cycle": "Monthly",
            "usage_frequency": "Daily",
            "usage_hours": "3"
        },
        follow_redirects=True
    )
    assert res.status_code == 200

    sub = Subscription.query.filter_by(user_id=auth_user, service_name="Netflix").first()
    assert sub is not None
    assert sub.monthly_cost == 499.0
    assert sub.category == "Entertainment"
    assert sub.billing_cycle == "Monthly"


def test_add_subscription_form_submission_unknown_service_and_yearly(client, auth_user):
    # Test adding an unknown service with Yearly billing cycle
    res = client.post(
        "/add-subscription",
        data={
            "service_name": "Custom Gym Pro",
            "monthly_cost": "1200",
            "category": "Fitness",
            "start_date": "2026-08-15",
            "billing_cycle": "Yearly",
            "usage_frequency": "Weekly",
            "usage_hours": "5"
        },
        follow_redirects=True
    )
    assert res.status_code == 200

    sub = Subscription.query.filter_by(user_id=auth_user, service_name="Custom Gym Pro").first()
    assert sub is not None
    assert sub.monthly_cost == 1200.0
    assert sub.category == "Fitness"
    assert sub.billing_cycle == "Yearly"


def test_add_subscription_branding_and_chatbot(client, auth_user):
    res = client.get("/add-subscription")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # Product name rule: Must NEVER contain "SmartSub"
    assert "SmartSub" not in html
    assert "Smart Subscription Advisor" in html

    # Chatbot inclusion
    assert "Ask AI" in html
    assert "chatbot-badge-tip" in html


def test_add_subscription_official_logos_exist_and_referenced():
    logos_dir = Path(__file__).resolve().parents[1] / "static" / "assets" / "logos" / "subscriptions"
    assert logos_dir.exists(), "Logos directory missing"

    required_logos = [
        "netflix.svg",
        "spotify.svg",
        "youtube.svg",
        "amazon.svg",
        "microsoft365.svg",
        "canva.svg",
        "chatgpt.svg",
        "disneyplus.svg",
        "applemusic.svg",
        "adobe.svg",
        "googleone.svg",
        "dropbox.svg",
        "notion.svg",
        "grammarly.svg",
        "linkedin.svg"
    ]

    for logo in required_logos:
        logo_path = logos_dir / logo
        assert logo_path.exists(), f"Logo asset {logo} not found"
        assert logo_path.stat().st_size > 0, f"Logo asset {logo} is empty"

    # Verify add_subscription.js references each logo asset
    js_path = Path(__file__).resolve().parents[1] / "static" / "js" / "add_subscription.js"
    js_content = js_path.read_text(encoding="utf-8")
    for logo in required_logos:
        assert f"/static/assets/logos/subscriptions/{logo}" in js_content, f"{logo} not referenced in add_subscription.js"

