"""Focused regression tests for subscription ownership and authorization (IDOR protection)."""

from datetime import date
from pathlib import Path
import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

from config import Config
from database.db import db
from exceptions.error_handlers import register_error_handlers
from exceptions.exceptions import ResourceNotFoundException
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
def test_users_and_subscriptions(app):
    """Create User A with Subscription A and User B with Subscription B."""
    auth_service = AuthService()
    with app.app_context():
        # User A
        user_a = auth_service.register_user(
            username="user_alice",
            email="alice@example.com",
            mobile_number="9876543210",
            password="Password123!",
            occupation="Engineer",
            financial_preference="Money Saver",
        )
        auth_service.verify_email(user_a.verification_token)
        user_a_id = user_a.id

        sub_a = Subscription(
            user_id=user_a_id,
            service_name="Netflix",
            monthly_cost=499.0,
            category="Entertainment",
            start_date=date(2026, 9, 1),
            renewal_date=date(2026, 10, 1),
            billing_cycle="Monthly",
            usage_frequency="Daily",
            usage_hours=2.0,
            priority="High",
        )
        db.session.add(sub_a)

        # User B
        user_b = auth_service.register_user(
            username="user_bob",
            email="bob@example.com",
            mobile_number="9876543211",
            password="Password123!",
            occupation="Designer",
            financial_preference="Balanced",
        )
        auth_service.verify_email(user_b.verification_token)
        user_b_id = user_b.id

        sub_b = Subscription(
            user_id=user_b_id,
            service_name="Spotify",
            monthly_cost=119.0,
            category="Entertainment",
            start_date=date(2026, 9, 1),
            renewal_date=date(2026, 10, 1),
            billing_cycle="Monthly",
            usage_frequency="Weekly",
            usage_hours=1.0,
            priority="Medium",
        )
        db.session.add(sub_b)
        db.session.commit()

        sub_a_id = sub_a.id
        sub_b_id = sub_b.id

        # Generate JWT tokens using the production auth service
        token_a = auth_service.login_with_jwt("alice@example.com", "Password123!")["access_token"]
        token_b = auth_service.login_with_jwt("bob@example.com", "Password123!")["access_token"]

    return {
        "user_a_id": user_a_id,
        "user_b_id": user_b_id,
        "sub_a_id": sub_a_id,
        "sub_b_id": sub_b_id,
        "token_a": token_a,
        "token_b": token_b,
    }


def login_user(client, email, password="Password123!"):
    return client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )


def get_csrf_token(client):
    cookie = client.get_cookie("csrf_access_token")
    return cookie.value if cookie else ""


# -----------------------------------------------------------------------------
# 1 & 2. Owner can access their own subscription (Web)
# -----------------------------------------------------------------------------
def test_user_a_can_access_subscription_a(client, test_users_and_subscriptions):
    data = test_users_and_subscriptions
    login_user(client, "alice@example.com")

    res = client.get(f"/edit-subscription/{data['sub_a_id']}")
    assert res.status_code == 200
    assert "Netflix" in res.data.decode("utf-8")


def test_user_b_can_access_subscription_b(client, test_users_and_subscriptions):
    data = test_users_and_subscriptions
    login_user(client, "bob@example.com")

    res = client.get(f"/edit-subscription/{data['sub_b_id']}")
    assert res.status_code == 200
    assert "Spotify" in res.data.decode("utf-8")


# -----------------------------------------------------------------------------
# 5 & 6. User CANNOT access / view another user's subscription (Web IDOR)
# -----------------------------------------------------------------------------
def test_user_a_cannot_access_subscription_b(client, test_users_and_subscriptions):
    data = test_users_and_subscriptions
    login_user(client, "alice@example.com")

    # Accessing User B's subscription must be rejected with 404
    res = client.get(f"/edit-subscription/{data['sub_b_id']}")
    assert res.status_code == 404
    # No information about Spotify or Bob's subscription is leaked
    assert "Spotify" not in res.data.decode("utf-8")

    # Alias routes should also return 404
    res_alias = client.get(f"/subscriptions/{data['sub_b_id']}")
    assert res_alias.status_code == 404

    res_alias2 = client.get(f"/subscriptions/{data['sub_b_id']}/edit")
    assert res_alias2.status_code == 404


def test_user_b_cannot_access_subscription_a(client, test_users_and_subscriptions):
    data = test_users_and_subscriptions
    login_user(client, "bob@example.com")

    # Accessing User A's subscription must be rejected with 404
    res = client.get(f"/edit-subscription/{data['sub_a_id']}")
    assert res.status_code == 404
    # No information about Netflix or Alice's subscription is leaked
    assert "Netflix" not in res.data.decode("utf-8")


# -----------------------------------------------------------------------------
# 7 & 8. User CANNOT edit another user's subscription (Web POST IDOR)
# -----------------------------------------------------------------------------
def test_user_a_cannot_edit_subscription_b(app, client, test_users_and_subscriptions):
    data = test_users_and_subscriptions
    login_user(client, "alice@example.com")
    csrf_token = get_csrf_token(client)

    res = client.post(
        f"/edit-subscription/{data['sub_b_id']}",
        data={
            "csrf_token": csrf_token,
            "service_name": "Hacked Spotify",
            "monthly_cost": "999",
            "category": "Entertainment",
            "start_date": "2026-09-01",
            "billing_cycle": "Monthly",
            "usage_frequency": "Rarely",
            "usage_hours": "0",
        },
        headers={"X-CSRF-TOKEN": csrf_token},
    )
    assert res.status_code == 404

    # Confirm Subscription B remains unchanged in the database
    with app.app_context():
        sub_b = db.session.get(Subscription, data["sub_b_id"])
        assert sub_b.service_name == "Spotify"
        assert sub_b.monthly_cost == 119.0
        assert sub_b.user_id == data["user_b_id"]


def test_user_b_cannot_edit_subscription_a(app, client, test_users_and_subscriptions):
    data = test_users_and_subscriptions
    login_user(client, "bob@example.com")
    csrf_token = get_csrf_token(client)

    res = client.post(
        f"/edit-subscription/{data['sub_a_id']}",
        data={
            "csrf_token": csrf_token,
            "service_name": "Hacked Netflix",
            "monthly_cost": "10",
            "category": "Entertainment",
            "start_date": "2026-09-01",
            "billing_cycle": "Monthly",
            "usage_frequency": "Rarely",
            "usage_hours": "0",
        },
        headers={"X-CSRF-TOKEN": csrf_token},
    )
    assert res.status_code == 404

    # Confirm Subscription A remains unchanged in the database
    with app.app_context():
        sub_a = db.session.get(Subscription, data["sub_a_id"])
        assert sub_a.service_name == "Netflix"
        assert sub_a.monthly_cost == 499.0
        assert sub_a.user_id == data["user_a_id"]


# -----------------------------------------------------------------------------
# 9 & 10. User CANNOT delete another user's subscription (Web GET/POST IDOR)
# -----------------------------------------------------------------------------
def test_user_a_cannot_delete_subscription_b(app, client, test_users_and_subscriptions):
    data = test_users_and_subscriptions
    login_user(client, "alice@example.com")
    csrf_token = get_csrf_token(client)

    # 1. GET request is rejected (405 Method Not Allowed)
    res_get = client.get(f"/delete-subscription/{data['sub_b_id']}")
    assert res_get.status_code == 405

    # 2. POST request to delete another user's subscription must return 404
    res_post = client.post(
        f"/delete-subscription/{data['sub_b_id']}",
        data={"csrf_token": csrf_token},
        headers={"X-CSRF-TOKEN": csrf_token},
    )
    assert res_post.status_code == 404

    # Confirm Subscription B was NOT deleted
    with app.app_context():
        sub_b = db.session.get(Subscription, data["sub_b_id"])
        assert sub_b is not None
        assert sub_b.service_name == "Spotify"
        assert sub_b.user_id == data["user_b_id"]


def test_user_b_cannot_delete_subscription_a(app, client, test_users_and_subscriptions):
    data = test_users_and_subscriptions
    login_user(client, "bob@example.com")
    csrf_token = get_csrf_token(client)

    # 1. GET request is rejected (405 Method Not Allowed)
    res_get = client.get(f"/delete-subscription/{data['sub_a_id']}")
    assert res_get.status_code == 405

    # 2. POST request to delete another user's subscription must return 404
    res_post = client.post(
        f"/delete-subscription/{data['sub_a_id']}",
        data={"csrf_token": csrf_token},
        headers={"X-CSRF-TOKEN": csrf_token},
    )
    assert res_post.status_code == 404

    # Confirm Subscription A was NOT deleted
    with app.app_context():
        sub_a = db.session.get(Subscription, data["sub_a_id"])
        assert sub_a is not None
        assert sub_a.service_name == "Netflix"
        assert sub_a.user_id == data["user_a_id"]


# -----------------------------------------------------------------------------
# 11 & 12. User CANNOT update usage info for another user's subscription
# -----------------------------------------------------------------------------
def test_user_a_cannot_update_usage_for_subscription_b(app, client, test_users_and_subscriptions):
    data = test_users_and_subscriptions
    login_user(client, "alice@example.com")
    csrf_token = get_csrf_token(client)

    res = client.post(
        f"/subscriptions/{data['sub_b_id']}/usage",
        json={"usage_frequency": "Daily", "usage_hours": 10},
        headers={"X-Requested-With": "XMLHttpRequest", "X-CSRF-TOKEN": csrf_token},
    )
    assert res.status_code == 404

    # Confirm Subscription B usage was NOT modified
    with app.app_context():
        sub_b = db.session.get(Subscription, data["sub_b_id"])
        assert sub_b.usage_frequency == "Weekly"
        assert sub_b.usage_hours == 1.0


def test_user_b_cannot_update_usage_for_subscription_a(app, client, test_users_and_subscriptions):
    data = test_users_and_subscriptions
    login_user(client, "bob@example.com")
    csrf_token = get_csrf_token(client)

    res = client.post(
        f"/subscriptions/{data['sub_a_id']}/usage",
        json={"usage_frequency": "Rarely", "usage_hours": 0},
        headers={"X-Requested-With": "XMLHttpRequest", "X-CSRF-TOKEN": csrf_token},
    )
    assert res.status_code == 404

    # Confirm Subscription A usage was NOT modified
    with app.app_context():
        sub_a = db.session.get(Subscription, data["sub_a_id"])
        assert sub_a.usage_frequency == "Daily"
        assert sub_a.usage_hours == 2.0


# -----------------------------------------------------------------------------
# 13. API GET ownership is enforced
# -----------------------------------------------------------------------------
def test_api_get_ownership_enforcement(client, test_users_and_subscriptions):
    data = test_users_and_subscriptions

    # User A accesses Subscription A -> Success
    res = client.get(
        f"/api/subscriptions/{data['sub_a_id']}",
        headers={"Authorization": f"Bearer {data['token_a']}"},
    )
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["success"] is True
    assert json_data["data"]["subscription"]["service_name"] == "Netflix"

    # User A attempts to access Subscription B -> 404
    res_b = client.get(
        f"/api/subscriptions/{data['sub_b_id']}",
        headers={"Authorization": f"Bearer {data['token_a']}"},
    )
    assert res_b.status_code == 404
    assert res_b.get_json()["success"] is False

    # User B attempts to access Subscription A -> 404
    res_a = client.get(
        f"/api/subscriptions/{data['sub_a_id']}",
        headers={"Authorization": f"Bearer {data['token_b']}"},
    )
    assert res_a.status_code == 404
    assert res_a.get_json()["success"] is False


# -----------------------------------------------------------------------------
# 14. API PUT ownership is enforced (Security regression test)
# -----------------------------------------------------------------------------
def test_api_put_ownership_enforcement(app, client, test_users_and_subscriptions):
    data = test_users_and_subscriptions

    # User A tries to modify Subscription B
    res = client.put(
        f"/api/subscriptions/{data['sub_b_id']}",
        headers={"Authorization": f"Bearer {data['token_a']}"},
        json={
            "service_name": "Attacked Spotify",
            "monthly_cost": 1.0,
            "category": "Entertainment",
            "start_date": "2026-09-01",
            "billing_cycle": "Monthly",
            "usage_frequency": "Daily",
            "usage_hours": 1.0,
        },
    )
    assert res.status_code == 404
    assert res.get_json()["success"] is False

    # Verify Subscription B remains intact and uncompromised
    with app.app_context():
        sub_b = db.session.get(Subscription, data["sub_b_id"])
        assert sub_b.service_name == "Spotify"
        assert sub_b.monthly_cost == 119.0
        assert sub_b.user_id == data["user_b_id"]

    # Legitimate owner User B can update Subscription B
    res_valid = client.put(
        f"/api/subscriptions/{data['sub_b_id']}",
        headers={"Authorization": f"Bearer {data['token_b']}"},
        json={
            "service_name": "Spotify Family",
            "monthly_cost": 179.0,
            "category": "Entertainment",
            "start_date": "2026-09-01",
            "billing_cycle": "Monthly",
            "usage_frequency": "Daily",
            "usage_hours": 2.0,
        },
    )
    assert res_valid.status_code == 200
    with app.app_context():
        sub_b_updated = db.session.get(Subscription, data["sub_b_id"])
        assert sub_b_updated.service_name == "Spotify Family"
        assert sub_b_updated.monthly_cost == 179.0


# -----------------------------------------------------------------------------
# 15. API DELETE ownership is enforced (Security regression test)
# -----------------------------------------------------------------------------
def test_api_delete_ownership_enforcement(app, client, test_users_and_subscriptions):
    data = test_users_and_subscriptions

    # User A attempts to delete Subscription B
    res = client.delete(
        f"/api/subscriptions/{data['sub_b_id']}",
        headers={"Authorization": f"Bearer {data['token_a']}"},
    )
    assert res.status_code == 404
    assert res.get_json()["success"] is False

    # Verify Subscription B is STILL in the database
    with app.app_context():
        sub_b = db.session.get(Subscription, data["sub_b_id"])
        assert sub_b is not None
        assert sub_b.service_name == "Spotify"
        assert sub_b.user_id == data["user_b_id"]

    # Legitimate owner User A deletes Subscription A
    res_del = client.delete(
        f"/api/subscriptions/{data['sub_a_id']}",
        headers={"Authorization": f"Bearer {data['token_a']}"},
    )
    assert res_del.status_code == 200
    with app.app_context():
        assert db.session.get(Subscription, data["sub_a_id"]) is None


# -----------------------------------------------------------------------------
# Service Layer Direct Invocation Ownership Verification
# -----------------------------------------------------------------------------
def test_service_layer_direct_ownership_enforcement(app, test_users_and_subscriptions):
    data = test_users_and_subscriptions

    with app.app_context():
        user_a = db.session.get(User, data["user_a_id"])
        user_b = db.session.get(User, data["user_b_id"])

        # get_subscription_for_user
        with pytest.raises(ResourceNotFoundException):
            subscription_service.get_subscription_for_user(user_a, data["sub_b_id"])

        # update_subscription
        with pytest.raises(ResourceNotFoundException):
            subscription_service.update_subscription(
                user=user_a,
                subscription_id=data["sub_b_id"],
                service_name="Illegal update",
                monthly_cost=50.0,
                category="Entertainment",
                start_date="2026-09-01",
                billing_cycle="Monthly",
                usage_frequency="Daily",
                usage_hours=1.0,
            )

        # delete_subscription
        with pytest.raises(ResourceNotFoundException):
            subscription_service.delete_subscription(user_a, data["sub_b_id"])

        # update_subscription_usage
        with pytest.raises(ResourceNotFoundException):
            subscription_service.update_subscription_usage(
                user=user_a,
                subscription_id=data["sub_b_id"],
                usage_frequency="Daily",
                usage_hours=1.0,
            )


# -----------------------------------------------------------------------------
# Data Isolation & Listing Checks
# -----------------------------------------------------------------------------
def test_data_isolation_between_users(client, test_users_and_subscriptions):
    data = test_users_and_subscriptions

    # User A's API listing only returns User A's subscriptions
    res_a = client.get(
        "/api/subscriptions",
        headers={"Authorization": f"Bearer {data['token_a']}"},
    )
    subs_a = res_a.get_json()["data"]["subscriptions"]
    assert len(subs_a) == 1
    assert subs_a[0]["service_name"] == "Netflix"
    assert subs_a[0]["id"] == data["sub_a_id"]

    # User B's API listing only returns User B's subscriptions
    res_b = client.get(
        "/api/subscriptions",
        headers={"Authorization": f"Bearer {data['token_b']}"},
    )
    subs_b = res_b.get_json()["data"]["subscriptions"]
    assert len(subs_b) == 1
    assert subs_b[0]["service_name"] == "Spotify"
    assert subs_b[0]["id"] == data["sub_b_id"]
