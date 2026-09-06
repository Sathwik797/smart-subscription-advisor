"""Targeted tests for Spending Analytics page."""

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
from datetime import datetime


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


def test_spending_analytics_unauthenticated_redirect(client):
    res = client.get("/spending-analytics")
    assert res.status_code == 302
    assert "/login" in res.headers.get("Location", "")


def test_spending_analytics_authenticated_empty_state(app, client):
    auth_service = AuthService()
    with app.app_context():
        user = auth_service.register_user(
            username="analyst_empty",
            email="analyst_empty@example.com",
            mobile_number="9876599001",
            password="Password123!",
            occupation="Professional",
            financial_preference="Balanced",
        )
        auth_service.verify_email(user.verification_token)

    # Login to acquire session / cookies
    login_resp = client.post(
        "/login",
        data={"email": "analyst_empty@example.com", "password": "Password123!"},
        follow_redirects=False,
    )
    assert login_resp.status_code in (200, 302)

    res = client.get("/spending-analytics")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    assert "SPENDING ANALYTICS" in html
    assert "Understand your subscription spending" in html
    assert "No spending data yet" in html
    assert "No category data yet" in html
    assert "No subscriptions yet" in html
    assert "Smart Subscription Advisor" in html
    assert "SmartSub" not in html


def test_spending_analytics_with_subscriptions(app, client):
    auth_service = AuthService()
    with app.app_context():
        user = auth_service.register_user(
            username="analyst_sub",
            email="analyst_sub@example.com",
            mobile_number="9876599002",
            password="Password123!",
            occupation="Professional",
            financial_preference="Balanced",
        )
        auth_service.verify_email(user.verification_token)
        user_id = user.id

        sub1 = Subscription(
            user_id=user_id,
            service_name="Netflix",
            category="Entertainment",
            monthly_cost=649.0,
            billing_cycle="Monthly",
            start_date=datetime.now().date(),
            renewal_date=datetime.now().date()
        )
        sub2 = Subscription(
            user_id=user_id,
            service_name="Amazon Prime",
            category="Shopping",
            monthly_cost=1499.0,
            billing_cycle="Yearly",
            start_date=datetime.now().date(),
            renewal_date=datetime.now().date()
        )
        db.session.add_all([sub1, sub2])
        db.session.commit()

    login_resp = client.post(
        "/login",
        data={"email": "analyst_sub@example.com", "password": "Password123!"},
        follow_redirects=False,
    )
    assert login_resp.status_code in (200, 302)

    res = client.get("/spending-analytics")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    assert "Netflix" in html
    assert "Amazon Prime" in html
    assert "Entertainment" in html
    assert "Shopping" in html
    assert "Pro Tip" in html
    assert "₹" in html
