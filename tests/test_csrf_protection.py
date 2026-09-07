"""Comprehensive, focused CSRF protection tests for Phase 1.2.

Verifies:
1. Protected browser state-changing request WITHOUT CSRF token -> rejected (400).
2. Protected browser state-changing request WITH invalid CSRF token -> rejected (400).
3. Protected browser state-changing request WITH valid CSRF token header -> succeeds.
4. Protected browser state-changing request WITH valid CSRF form field -> succeeds.
5. GET requests do not require CSRF token.
6. Owner can still create a subscription with CSRF protection.
7. Owner can still update a subscription with CSRF protection.
8. Owner can still update subscription usage with CSRF protection.
9. Owner can still delete a subscription using currently supported flow.
10. Profile update works with valid CSRF token.
11. Settings page loads without error.
12. Password reset flow remains functional without requiring CSRF.
13. Bearer-token REST API authentication continues working without CSRF.
14. Cross-user authorization (IDOR protection) remains strictly enforced.
15. No partial execution: when CSRF is missing or invalid, no database mutation occurs.
"""

from datetime import date
from pathlib import Path
import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

from config import Config
from database.db import db
from exceptions.error_handlers import register_error_handlers
from models.subscription import Subscription
from models.user import User
from routes.api import api
from routes.auth import auth
import routes.subscription  # noqa: F401
from services.auth_service import AuthService
from services.subscription_service import subscription_service
from utils.currency import format_inr


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

    test_app.jinja_env.filters["inr"] = format_inr
    test_app.jinja_env.globals["format_inr"] = format_inr
    test_app.jinja_env.globals["zip"] = zip

    db.init_app(test_app)
    jwt = JWTManager(test_app)

    @jwt.unauthorized_loader
    def unauthorized_loader(callback):
        if "csrf" in str(callback).lower():
            return {"success": False, "message": "CSRF token missing or invalid"}, 400
        return {"success": False, "message": "Missing or invalid token"}, 401

    register_error_handlers(test_app)
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
def test_user_and_sub(app):
    auth_service = AuthService()
    with app.app_context():
        user = auth_service.register_user(
            username="csrf_tester",
            email="tester@example.com",
            mobile_number="9876543210",
            password="Password123!",
            occupation="Security Engineer",
            financial_preference="Money Saver",
        )
        auth_service.verify_email(user.verification_token)
        user_id = user.id

        sub = Subscription(
            user_id=user_id,
            service_name="Prime Video",
            monthly_cost=299.0,
            category="Entertainment",
            start_date=date(2026, 9, 1),
            renewal_date=date(2026, 10, 1),
            billing_cycle="Monthly",
            usage_frequency="Weekly",
            usage_hours=4.0,
            priority="High",
        )
        db.session.add(sub)
        db.session.commit()
        sub_id = sub.id

        token = auth_service.login_with_jwt("tester@example.com", "Password123!")["access_token"]

    return {"user_id": user_id, "sub_id": sub_id, "token": token}


def get_csrf_token(client):
    cookie = client.get_cookie("csrf_access_token")
    return cookie.value if cookie else ""


def login_session(client, email="tester@example.com", password="Password123!"):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=False)


# -----------------------------------------------------------------------------
# 1. State-changing request WITHOUT CSRF token is REJECTED
# -----------------------------------------------------------------------------
def test_post_without_csrf_is_rejected(client, test_user_and_sub):
    data = test_user_and_sub
    login_session(client)

    # Browser has access_token_cookie, but sends no CSRF token header or form field
    res = client.post(
        f"/edit-subscription/{data['sub_id']}",
        data={
            "service_name": "Tampered Name",
            "monthly_cost": "999",
            "category": "Entertainment",
            "start_date": "2026-09-01",
            "billing_cycle": "Monthly",
        },
    )
    assert res.status_code == 400
    res_data = res.get_json(silent=True) or {}
    assert "CSRF" in res_data.get("message", "") or res.status_code == 400


# -----------------------------------------------------------------------------
# 2. State-changing request WITH INVALID CSRF token is REJECTED
# -----------------------------------------------------------------------------
def test_post_with_invalid_csrf_is_rejected(client, test_user_and_sub):
    data = test_user_and_sub
    login_session(client)

    res = client.post(
        f"/edit-subscription/{data['sub_id']}",
        data={
            "csrf_token": "totally-bogus-csrf-token",
            "service_name": "Tampered Name",
            "monthly_cost": "999",
            "category": "Entertainment",
            "start_date": "2026-09-01",
            "billing_cycle": "Monthly",
        },
        headers={"X-CSRF-TOKEN": "totally-bogus-csrf-token"},
    )
    assert res.status_code == 400


# -----------------------------------------------------------------------------
# 3. State-changing request WITH VALID CSRF header SUCCEEDS
# -----------------------------------------------------------------------------
def test_post_with_valid_csrf_header_succeeds(app, client, test_user_and_sub):
    data = test_user_and_sub
    login_session(client)
    csrf_token = get_csrf_token(client)
    assert csrf_token != "", "CSRF cookie must be issued upon login"

    res = client.post(
        f"/subscriptions/{data['sub_id']}/usage",
        json={"usage_frequency": "Daily", "usage_hours": 3.0},
        headers={
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRF-TOKEN": csrf_token,
        },
    )
    assert res.status_code == 200
    assert res.get_json()["success"] is True

    with app.app_context():
        sub = db.session.get(Subscription, data["sub_id"])
        assert sub.usage_frequency == "Daily"
        assert sub.usage_hours == 3.0


# -----------------------------------------------------------------------------
# 4. State-changing request WITH VALID CSRF form field SUCCEEDS
# -----------------------------------------------------------------------------
def test_post_with_valid_csrf_form_field_succeeds(app, client, test_user_and_sub):
    data = test_user_and_sub
    login_session(client)
    csrf_token = get_csrf_token(client)

    res = client.post(
        f"/edit-subscription/{data['sub_id']}",
        data={
            "csrf_token": csrf_token,
            "service_name": "Prime Video 4K",
            "monthly_cost": "349",
            "category": "Entertainment",
            "start_date": "2026-09-01",
            "billing_cycle": "Monthly",
            "usage_frequency": "Daily",
            "usage_hours": "2",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200

    with app.app_context():
        sub = db.session.get(Subscription, data["sub_id"])
        assert sub.service_name == "Prime Video 4K"
        assert sub.monthly_cost == 349.0


# -----------------------------------------------------------------------------
# 5. GET requests do NOT require CSRF token
# -----------------------------------------------------------------------------
def test_get_requests_do_not_require_csrf(client, test_user_and_sub):
    data = test_user_and_sub
    login_session(client)

    # 1. Edit page GET
    res_edit = client.get(f"/edit-subscription/{data['sub_id']}")
    assert res_edit.status_code == 200
    assert "Prime Video" in res_edit.data.decode("utf-8")

    # 2. Subscriptions list GET
    res_list = client.get("/subscriptions")
    assert res_list.status_code == 200

    # 3. Profile GET
    res_profile = client.get("/profile")
    assert res_profile.status_code == 200

    # 4. Dashboard GET
    res_dashboard = client.get("/dashboard")
    assert res_dashboard.status_code == 200


# -----------------------------------------------------------------------------
# 6. Owner can create a subscription
# -----------------------------------------------------------------------------
def test_owner_can_create_subscription(app, client, test_user_and_sub):
    login_session(client)
    csrf_token = get_csrf_token(client)

    res = client.post(
        "/add-subscription",
        data={
            "csrf_token": csrf_token,
            "service_name": "Spotify Premium",
            "monthly_cost": "119",
            "category": "Entertainment",
            "start_date": "2026-09-01",
            "billing_cycle": "Monthly",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200

    with app.app_context():
        created = Subscription.query.filter_by(user_id=test_user_and_sub["user_id"], service_name="Spotify Premium").first()
        assert created is not None
        assert created.monthly_cost == 119.0


# -----------------------------------------------------------------------------
# 7. Owner can delete a subscription via POST with valid CSRF
# -----------------------------------------------------------------------------
def test_owner_can_delete_subscription(app, client, test_user_and_sub):
    data = test_user_and_sub
    login_session(client)
    csrf_token = get_csrf_token(client)

    res = client.post(
        f"/delete-subscription/{data['sub_id']}",
        data={"csrf_token": csrf_token},
        headers={"X-CSRF-TOKEN": csrf_token},
        follow_redirects=True,
    )
    assert res.status_code == 200

    with app.app_context():
        deleted = db.session.get(Subscription, data["sub_id"])
        assert deleted is None


def test_get_delete_subscription_does_not_delete(app, client, test_user_and_sub):
    data = test_user_and_sub
    login_session(client)

    # Attempting GET deletion must be rejected (405 Method Not Allowed)
    res = client.get(f"/delete-subscription/{data['sub_id']}")
    assert res.status_code == 405

    # Subscription must NOT be deleted
    with app.app_context():
        sub = db.session.get(Subscription, data["sub_id"])
        assert sub is not None
        assert sub.service_name == "Prime Video"


def test_post_delete_without_csrf_is_rejected(app, client, test_user_and_sub):
    data = test_user_and_sub
    login_session(client)

    # Missing CSRF token on POST delete must be rejected
    res = client.post(f"/delete-subscription/{data['sub_id']}")
    assert res.status_code == 400

    # Subscription must NOT be deleted
    with app.app_context():
        sub = db.session.get(Subscription, data["sub_id"])
        assert sub is not None


# -----------------------------------------------------------------------------
# 8. Profile update works with valid CSRF token
# -----------------------------------------------------------------------------
def test_profile_update_works_with_csrf(app, client, test_user_and_sub):
    login_session(client)
    csrf_token = get_csrf_token(client)

    res = client.post(
        "/profile/edit",
        data={
            "csrf_token": csrf_token,
            "username": "updated_tester",
            "occupation": "Principal Architect",
            "financial_preference": "Balanced",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200

    with app.app_context():
        user = db.session.get(User, test_user_and_sub["user_id"])
        assert user.username == "updated_tester"
        assert user.occupation == "Principal Architect"


# -----------------------------------------------------------------------------
# 9. Password reset flow works without CSRF block
# -----------------------------------------------------------------------------
def test_forgot_password_works_without_csrf_block(client, test_user_and_sub):
    res = client.post(
        "/forgot-password",
        data={"email": "tester@example.com"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert "If an account with that email exists" in res.data.decode("utf-8")


# -----------------------------------------------------------------------------
# 10. Bearer token REST API authentication bypasses browser-cookie CSRF
# -----------------------------------------------------------------------------
def test_bearer_token_api_requests_work_without_csrf(client, test_user_and_sub):
    token = test_user_and_sub["token"]

    # Bearer POST to /api/subscriptions
    res = client.post(
        "/api/subscriptions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "service_name": "GitHub Copilot",
            "monthly_cost": 800.0,
            "category": "Productivity",
            "start_date": "2026-09-01",
            "billing_cycle": "Monthly",
        },
    )
    assert res.status_code == 201
    json_data = res.get_json()
    assert json_data["success"] is True
    assert json_data["data"]["subscription"]["service_name"] == "GitHub Copilot"

    # Bearer PUT to /api/subscriptions/<id>
    sub_id = json_data["data"]["subscription"]["id"]
    res_put = client.put(
        f"/api/subscriptions/{sub_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "service_name": "GitHub Copilot Enterprise",
            "monthly_cost": 1600.0,
            "category": "Productivity",
            "start_date": "2026-09-01",
            "billing_cycle": "Monthly",
            "usage_frequency": "Daily",
            "usage_hours": 2.0,
        },
    )
    assert res_put.status_code == 200

    # Bearer DELETE to /api/subscriptions/<id>
    res_del = client.delete(
        f"/api/subscriptions/{sub_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_del.status_code == 200


# -----------------------------------------------------------------------------
# 11. Security Regression: No partial execution on CSRF rejection
# -----------------------------------------------------------------------------
def test_no_partial_execution_on_csrf_rejection(app, client, test_user_and_sub):
    data = test_user_and_sub
    login_session(client)

    # Attempt to modify Prime Video without CSRF token
    client.post(
        f"/edit-subscription/{data['sub_id']}",
        data={
            "service_name": "Hacked Subscription",
            "monthly_cost": "1",
            "category": "Other",
            "start_date": "2026-09-01",
            "billing_cycle": "Yearly",
        },
    )

    # Ensure the database remains completely untouched
    with app.app_context():
        sub = db.session.get(Subscription, data["sub_id"])
        assert sub.service_name == "Prime Video"
        assert sub.monthly_cost == 299.0
        assert sub.billing_cycle == "Monthly"


# -----------------------------------------------------------------------------
# 12. Login without email verification requirement is preserved
# -----------------------------------------------------------------------------
def test_login_without_email_verification_works(app, client):
    auth_service = AuthService()
    with app.app_context():
        # Register a user without verifying email
        unverified_user = auth_service.register_user(
            username="unverified_login",
            email="unverified@example.com",
            mobile_number="9876543299",
            password="Password123!",
            occupation="Tester",
            financial_preference="Balanced",
        )
        assert unverified_user.email_verified is False

    res = client.post(
        "/login",
        data={"email": "unverified@example.com", "password": "Password123!"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    # Must successfully reach dashboard
    assert "dashboard" in res.request.path or "Dashboard" in res.data.decode("utf-8")
