"""Comprehensive test suite for Phase 2: Financial & Data Correctness.

Validates:
A. Monthly calculation (₹499/month -> ₹499/mo, ₹5,988/yr)
B. Yearly calculation (₹1,499/year -> ₹124.916.../mo, ₹1,499/yr)
C. Mixed billing cycles (₹499/month + ₹1,200/year -> ₹599/mo)
D. Decimal precision (199.99, 499.50, 1299.75)
E. Dashboard, Analytics, and IntelligenceService consistency
F. Health score consistency between Dashboard and IntelligenceService
G. Zero subscriptions edge case
H. API JSON serialization (numeric types, no Decimal serialization crash)
I. Subscription CRUD with Numeric/Decimal values
J. Recommendation calculations stability
K. Indian Rupee (₹) formatting and Indian numbering system (₹1,24,999)
"""

from decimal import Decimal
from datetime import date, datetime
from pathlib import Path
import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from werkzeug.security import generate_password_hash

from config import Config
from database.db import db
from models.user import User
from models.subscription import Subscription
from routes.auth import auth
from routes.api import api
import routes.subscription  # noqa: F401
from utils.currency import format_inr
from services.subscription_service import subscription_service
from services.intelligence_service import intelligence_service
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
def user_id(app):
    with app.app_context():
        test_user = User(
            username="finance_user",
            email="finance@example.com",
            password=generate_password_hash("Password123!"),
            mobile_number="9876543210",
            occupation="Professional",
            financial_preference="Money Saver",
            email_verified=True,
        )
        db.session.add(test_user)
        db.session.commit()
        return test_user.id


def test_a_monthly_calculation(app, user_id):
    """Test A: Monthly subscription calculation (₹499/month -> monthly=499, yearly=5988)."""
    with app.app_context():
        user = db.session.get(User, user_id)
        sub = subscription_service.add_subscription(
            user=user,
            service_name="Netflix",
            monthly_cost=Decimal("499.00"),
            category="Entertainment",
            start_date="2026-01-01",
            billing_cycle="Monthly",
            usage_frequency="Daily",
            usage_hours=2.0,
        )

        assert isinstance(sub.monthly_equivalent, Decimal)
        assert isinstance(sub.yearly_equivalent, Decimal)
        assert sub.monthly_equivalent == Decimal("499.00")
        assert sub.yearly_equivalent == Decimal("5988.00")

        summary = subscription_service.get_subscription_summary(user)
        assert summary["monthly_spend"] == 499.00
        assert summary["projected_yearly"] == 5988.00


def test_b_yearly_calculation(app, user_id):
    """Test B: Yearly subscription calculation (₹1,499/year -> monthly=124.9166..., yearly=1499)."""
    with app.app_context():
        user = db.session.get(User, user_id)
        sub = subscription_service.add_subscription(
            user=user,
            service_name="Amazon Prime Annual",
            monthly_cost=Decimal("1499.00"),
            category="Entertainment",
            start_date="2026-01-01",
            billing_cycle="Yearly",
            usage_frequency="Weekly",
            usage_hours=5.0,
        )

        assert isinstance(sub.monthly_equivalent, Decimal)
        assert isinstance(sub.yearly_equivalent, Decimal)
        assert sub.yearly_equivalent == Decimal("1499.00")
        # Internal monthly equivalent must be high precision Decimal (1499 / 12 = 124.916666...)
        expected_monthly = Decimal("1499.00") / Decimal("12")
        assert sub.monthly_equivalent == expected_monthly
        assert round(sub.monthly_equivalent, 2) == Decimal("124.92")

        summary = subscription_service.get_subscription_summary(user)
        assert summary["monthly_spend"] == 124.92
        assert summary["projected_yearly"] == 1499.00


def test_c_mixed_billing_cycles(app, user_id):
    """Test C: Mixed billing cycles (₹499/month + ₹1,200/year -> monthly total = 499 + 100 = 599)."""
    with app.app_context():
        user = db.session.get(User, user_id)
        subscription_service.add_subscription(
            user=user,
            service_name="Spotify",
            monthly_cost=Decimal("499.00"),
            category="Entertainment",
            start_date="2026-01-01",
            billing_cycle="Monthly",
            usage_frequency="Daily",
            usage_hours=3.0,
        )
        subscription_service.add_subscription(
            user=user,
            service_name="Annual Cloud Backup",
            monthly_cost=Decimal("1200.00"),
            category="Productivity",
            start_date="2026-01-01",
            billing_cycle="Yearly",
            usage_frequency="Weekly",
            usage_hours=1.0,
        )

        intel = intelligence_service.build_intelligence_context(user)
        fin = intel["financial_summary"]

        # Expected: 499 + (1200 / 12) = 599.00
        assert fin["monthly_spending"] == 599.00
        # Expected yearly: (499 * 12) + 1200 = 5988 + 1200 = 7188.00
        assert fin["yearly_projection"] == 7188.00

        summary = subscription_service.get_subscription_summary(user)
        assert summary["monthly_spend"] == 599.00
        assert summary["projected_yearly"] == 7188.00


def test_d_decimal_precision(app, user_id):
    """Test D: Decimal precision with 199.99, 499.50, and 1299.75."""
    with app.app_context():
        user = db.session.get(User, user_id)
        subscription_service.add_subscription(
            user=user,
            service_name="Tier 1",
            monthly_cost=Decimal("199.99"),
            category="Utilities",
            start_date="2026-01-01",
            billing_cycle="Monthly",
        )
        subscription_service.add_subscription(
            user=user,
            service_name="Tier 2",
            monthly_cost=Decimal("499.50"),
            category="Utilities",
            start_date="2026-01-01",
            billing_cycle="Monthly",
        )
        subscription_service.add_subscription(
            user=user,
            service_name="Tier 3",
            monthly_cost=Decimal("1299.75"),
            category="Utilities",
            start_date="2026-01-01",
            billing_cycle="Monthly",
        )

        expected_sum = Decimal("199.99") + Decimal("499.50") + Decimal("1299.75")
        assert expected_sum == Decimal("1999.24")

        summary = subscription_service.get_subscription_summary(user)
        assert summary["monthly_spend"] == 1999.24
        assert summary["projected_yearly"] == float(round(expected_sum * Decimal("12"), 2))


def test_e_single_source_of_truth_consistency(app, user_id):
    """Test E: Consistency across Dashboard, Analytics, and IntelligenceService."""
    with app.app_context():
        user = db.session.get(User, user_id)
        subscription_service.add_subscription(
            user=user,
            service_name="Service A",
            monthly_cost=Decimal("300.00"),
            category="Entertainment",
            start_date="2026-01-01",
            billing_cycle="Monthly",
            usage_frequency="Rarely",
            usage_hours=0.5,
        )
        subscription_service.add_subscription(
            user=user,
            service_name="Service B",
            monthly_cost=Decimal("2400.00"),
            category="Productivity",
            start_date="2026-01-01",
            billing_cycle="Yearly",
            usage_frequency="Daily",
            usage_hours=4.0,
        )

        auth_svc = AuthService()
        dashboard_data = auth_svc.get_dashboard_data(user)
        analytics_data = subscription_service.get_spending_analytics(user)
        intel_data = intelligence_service.build_intelligence_context(user)
        fin = intel_data["financial_summary"]

        # Expected monthly: 300 + (2400 / 12) = 500.00
        # Expected yearly: (300 * 12) + 2400 = 6000.00
        assert dashboard_data["total_monthly"] == 500.00
        assert analytics_data["total_monthly"] == 500.00
        assert fin["monthly_spending"] == 500.00
        assert intel_data["total_monthly"] == 500.00

        assert dashboard_data["total_yearly"] == 6000.00
        assert analytics_data["total_yearly"] == 6000.00
        assert fin["yearly_projection"] == 6000.00
        assert intel_data["total_yearly"] == 6000.00

        # Potential savings consistency
        assert dashboard_data["potential_monthly_savings"] == analytics_data["potential_monthly_savings"]
        assert dashboard_data["potential_monthly_savings"] == fin["potential_monthly_savings"]


def test_f_health_score_consistency(app, user_id):
    """Test F: Health score consistency between Dashboard and IntelligenceService."""
    with app.app_context():
        user = db.session.get(User, user_id)
        subscription_service.add_subscription(
            user=user,
            service_name="Streaming",
            monthly_cost=Decimal("499.00"),
            category="Entertainment",
            start_date="2026-01-01",
            billing_cycle="Monthly",
            usage_frequency="Daily",
            usage_hours=3.0,
        )

        auth_svc = AuthService()
        dashboard_data = auth_svc.get_dashboard_data(user)
        intel_score = intelligence_service.calculate_health_score(user)
        intel_context = intelligence_service.build_intelligence_context(user)

        assert dashboard_data["health_score"] == intel_score["score"]
        assert dashboard_data["health_score"] == intel_context["health_score"]["score"]


def test_g_zero_subscriptions(app, user_id):
    """Test G: Zero subscriptions edge case produces valid structures without errors."""
    with app.app_context():
        user = db.session.get(User, user_id)
        auth_svc = AuthService()
        dashboard_data = auth_svc.get_dashboard_data(user)
        analytics_data = subscription_service.get_spending_analytics(user)
        summary = subscription_service.get_subscription_summary(user)
        intel = intelligence_service.build_intelligence_context(user)

        assert dashboard_data["total_monthly"] == 0.0
        assert dashboard_data["total_yearly"] == 0.0
        assert dashboard_data["total_subscriptions"] == 0

        assert analytics_data["total_monthly"] == 0.0
        assert analytics_data["total_yearly"] == 0.0
        assert analytics_data["total_subscriptions"] == 0

        assert summary["monthly_spend"] == 0.0
        assert summary["projected_yearly"] == 0.0
        assert summary["active_count"] == 0

        assert intel["financial_summary"]["monthly_spending"] == 0.0
        assert intel["financial_summary"]["yearly_projection"] == 0.0
        assert intel["health_score"]["score"] == 100


def test_h_api_serialization(client, app, user_id):
    """Test H: API serialization converts Decimals to valid JSON numbers."""
    with app.app_context():
        user = db.session.get(User, user_id)
        subscription_service.add_subscription(
            user=user,
            service_name="Pro Cloud",
            monthly_cost=Decimal("999.50"),
            category="Productivity",
            start_date="2026-01-01",
            billing_cycle="Monthly",
        )
        token = create_access_token(identity=str(user.id))

    res = client.get(
        "/api/subscriptions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    subs = data["data"]["subscriptions"]
    assert len(subs) == 1
    assert subs[0]["monthly_cost"] == 999.50
    assert subs[0]["monthly_equivalent"] == 999.50
    assert subs[0]["yearly_equivalent"] == 11994.00
    assert isinstance(subs[0]["monthly_cost"], (float, int))


def test_i_subscription_crud(app, user_id):
    """Test I: Subscription CRUD operations with Numeric/Decimal values."""
    with app.app_context():
        user = db.session.get(User, user_id)
        # Create
        sub = subscription_service.add_subscription(
            user=user,
            service_name="Cloud SaaS",
            monthly_cost="499.50",
            category="Work",
            start_date="2026-01-01",
            billing_cycle="Monthly",
            usage_frequency="Daily",
            usage_hours=2.0,
        )
        assert sub.id is not None
        assert sub.monthly_cost == Decimal("499.50")

        # Edit / Update
        updated = subscription_service.update_subscription(
            user=user,
            subscription_id=sub.id,
            service_name="Cloud SaaS Pro",
            monthly_cost="1200.00",
            category="Work",
            start_date="2026-01-01",
            billing_cycle="Yearly",
            usage_frequency="Weekly",
            usage_hours=1.0,
        )
        assert updated.service_name == "Cloud SaaS Pro"
        assert updated.monthly_cost == Decimal("1200.00")
        assert updated.monthly_equivalent == Decimal("100.00")
        assert updated.yearly_equivalent == Decimal("1200.00")

        # Delete
        subscription_service.delete_subscription(user, sub.id)
        subs = subscription_service.subscription_repository.get_user_subscriptions(user.id)
        assert len(subs) == 0


def test_j_recommendation_and_savings_calculations(app, user_id):
    """Test J: Recommendation savings calculation with billing cycle awareness."""
    with app.app_context():
        user = db.session.get(User, user_id)
        # Yearly subscription with low usage
        sub = subscription_service.add_subscription(
            user=user,
            service_name="Unused Annual Gym",
            monthly_cost=Decimal("12000.00"),
            category="Fitness",
            start_date="2026-01-01",
            billing_cycle="Yearly",
            usage_frequency="Rarely",
            usage_hours=0.25,
        )

        candidates = intelligence_service.generate_recommendation_candidates(user)
        # Should detect the low-usage subscription
        assert len(candidates) > 0
        gym_rec = next((c for c in candidates if c.get("subscription_id") == sub.id), None)
        assert gym_rec is not None
        # Savings should be based on monthly equivalent: 12000 / 12 = 1000.00
        assert gym_rec["estimated_savings"] == 1000.00


def test_k_inr_currency_formatting():
    """Test K: Standardized Indian Rupee formatting with Indian numbering system."""
    assert format_inr(499) == "₹499"
    assert format_inr(Decimal("499.00")) == "₹499"
    assert format_inr(1299) == "₹1,299"
    assert format_inr(12999) == "₹12,999"
    assert format_inr(124999) == "₹1,24,999"
    assert format_inr(199.99) == "₹199.99"
    assert format_inr(Decimal("499.50")) == "₹499.50"
    assert format_inr(1299.75) == "₹1,299.75"
    assert format_inr(None) == "₹—"
    assert format_inr("") == "₹—"
