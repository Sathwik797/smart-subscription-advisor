"""Targeted tests for Subscription Management page redesign."""

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


def test_subscriptions_unauthenticated_redirect(client):
    res = client.get("/subscriptions")
    assert res.status_code == 302
    assert "/login" in res.headers.get("Location", "")


def test_subscriptions_authenticated_empty_state(app, client):
    auth_service = AuthService()
    with app.app_context():
        user = auth_service.register_user(
            username="sub_empty_user",
            email="sub_empty@example.com",
            mobile_number="9876599101",
            password="Password123!",
            occupation="Professional",
            financial_preference="Balanced",
        )
        auth_service.verify_email(user.verification_token)

    login_resp = client.post(
        "/login",
        data={"email": "sub_empty@example.com", "password": "Password123!"},
        follow_redirects=False,
    )
    assert login_resp.status_code in (200, 302)

    res = client.get("/subscriptions")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # Shell & Page Header
    assert "Smart Subscription Advisor" in html
    assert "SmartSub" not in html
    assert "SUBSCRIPTIONS" in html
    assert "My Subscriptions" in html
    assert "Manage, organize and monitor all your recurring subscriptions." in html
    assert "Export CSV" in html
    assert "Add Subscription" in html

    # Empty State Table & Sidebar
    assert "No subscriptions yet" in html
    assert "Start tracking your recurring expenses by adding your first subscription." in html
    assert "Not available yet" in html

    # Sidebar active navigation
    assert 'class="sidebar-nav-item active"' in html
    assert "Subscriptions" in html


def test_subscriptions_authenticated_with_data(app, client):
    auth_service = AuthService()
    with app.app_context():
        user = auth_service.register_user(
            username="sub_data_user",
            email="sub_data@example.com",
            mobile_number="9876599102",
            password="Password123!",
            occupation="Professional",
            financial_preference="Balanced",
        )
        auth_service.verify_email(user.verification_token)
        user_id = user.id

        # Add 3 subscriptions
        s1 = Subscription(
            user_id=user_id,
            service_name="Netflix",
            category="Entertainment",
            monthly_cost=649.0,
            billing_cycle="Monthly",
            start_date=date(2024, 1, 1),
            renewal_date=date(2026, 9, 14),
            priority="Medium"
        )
        s2 = Subscription(
            user_id=user_id,
            service_name="Amazon Prime",
            category="Shopping",
            monthly_cost=1499.0,
            billing_cycle="Yearly",
            start_date=date(2024, 1, 1),
            renewal_date=date(2026, 10, 2),
            priority="High"
        )
        s3 = Subscription(
            user_id=user_id,
            service_name="Spotify",
            category="Music",
            monthly_cost=119.0,
            billing_cycle="Monthly",
            start_date=date(2024, 1, 1),
            renewal_date=date(2026, 9, 18),
            priority="High"
        )
        db.session.add_all([s1, s2, s3])
        db.session.commit()

    login_resp = client.post(
        "/login",
        data={"email": "sub_data@example.com", "password": "Password123!"},
        follow_redirects=False,
    )
    assert login_resp.status_code in (200, 302)

    res = client.get("/subscriptions")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # Subscriptions in table
    assert "Netflix" in html
    assert "Amazon Prime" in html
    assert "Spotify" in html
    assert "Entertainment" in html
    assert "Shopping" in html
    assert "Music" in html
    assert "Active" in html

    # Rupee amounts
    assert "₹" in html
    assert "649" in html
    assert "1,499" in html
    assert "119" in html

    # Summary Card
    assert "Subscription Summary" in html
    assert "Most expensive" in html
    assert "Most affordable" in html
    assert "Average monthly cost" in html
    assert "Total categories" in html

    # Tips & AI
    assert "Subscription Tips" in html
    assert "Review unused subscriptions" in html
    assert "Get better recommendations" in html
    assert "Ask AI Advisor" in html

    # Actions
    assert "/edit-subscription/" in html
    assert "/delete-subscription/" in html


def test_subscriptions_csv_export(app, client):
    auth_service = AuthService()
    with app.app_context():
        user = auth_service.register_user(
            username="sub_csv_user",
            email="sub_csv@example.com",
            mobile_number="9876599103",
            password="Password123!",
            occupation="Professional",
            financial_preference="Balanced",
        )
        auth_service.verify_email(user.verification_token)
        user_id = user.id

        sub = Subscription(
            user_id=user_id,
            service_name="Canva Pro",
            category="Design",
            monthly_cost=499.0,
            billing_cycle="Monthly",
            start_date=date(2024, 1, 1),
            renewal_date=date(2026, 9, 22),
        )
        db.session.add(sub)
        db.session.commit()

    login_resp = client.post(
        "/login",
        data={"email": "sub_csv@example.com", "password": "Password123!"},
        follow_redirects=False,
    )
    assert login_resp.status_code in (200, 302)

    res = client.get("/export-csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("Content-Type", "")
    content = res.get_data(as_text=True)
    assert "Service Name,Monthly Cost,Category,Start Date,Renewal Date" in content
    assert "Canva Pro,499.0,Design" in content
