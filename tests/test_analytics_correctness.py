"""Comprehensive test suite for Phase 3: Analytics Correctness & Spending Analytics.

Validates:
A. Empty subscriptions (graceful empty states, no errors)
B. One monthly subscription (₹499/month -> ₹499/mo, ₹5,988/yr)
C. One yearly subscription (₹1,200/year -> ₹100/mo, ₹1,200/yr)
D. Mixed monthly + yearly subscriptions (₹499/mo + ₹1,200/yr -> ₹599/mo)
E. Category totals equal authoritative monthly spending
F. Category percentages sum to 100.0% without division-by-zero
G. Subscription spending ranking (sorted by monthly-equivalent, not stored yearly amount)
H. Potential savings are billing-cycle aware
I. Dashboard vs Analytics financial consistency
J. IntelligenceService vs Analytics canonical contract alignment
K. Health score consistency
L. API / JSON serialization (GET /api/analytics returns valid JSON numbers)
M. Forward-looking projected schedule without fabricated historical transactions
N. Actual payment events based on renewal dates and billing cycles
O. No NaN, Infinity, or un-serializable Decimal values
"""

import math
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from dateutil.relativedelta import relativedelta
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from werkzeug.security import generate_password_hash

from config import Config
from database.db import db
from models.subscription import Subscription
from models.user import User
from routes.api import api
from routes.auth import auth
import routes.subscription  # noqa: F401
from services.auth_service import AuthService
from services.intelligence_service import intelligence_service
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
            username="analytics_user",
            email="analytics@example.com",
            password=generate_password_hash("Password123!"),
            mobile_number="9876543210",
            occupation="Professional",
            financial_preference="Balanced",
            email_verified=True,
        )
        db.session.add(test_user)
        db.session.commit()
        return test_user.id


def test_a_empty_subscriptions(app, user_id):
    """Test A: Zero subscriptions produces a valid, error-free analytics payload."""
    with app.app_context():
        user = db.session.get(User, user_id)
        data = subscription_service.get_spending_analytics(user)

        assert data["summary"]["total_monthly"] == 0.0
        assert data["summary"]["total_yearly"] == 0.0
        assert data["summary"]["avg_monthly"] == 0.0
        assert data["summary"]["potential_monthly_savings"] == 0.0
        assert data["summary"]["active_subscriptions"] == 0
        assert data["categories"] == []
        assert data["top_subscriptions"] == []
        assert data["billing_cycles"] == []
        assert len(data["spending_schedule"]["months"]) == 6
        assert data["spending_schedule"]["values"] == [0.0] * 6
        assert data["insights"] == []


def test_b_one_monthly_subscription(app, user_id):
    """Test B: One monthly subscription of ₹499/mo."""
    with app.app_context():
        user = db.session.get(User, user_id)
        subscription_service.add_subscription(
            user=user,
            service_name="Netflix",
            monthly_cost=Decimal("499.00"),
            category="Entertainment",
            start_date="2026-01-01",
            billing_cycle="Monthly",
        )

        data = subscription_service.get_spending_analytics(user)
        assert data["summary"]["total_monthly"] == 499.00
        assert data["summary"]["total_yearly"] == 5988.00
        assert data["summary"]["active_subscriptions"] == 1
        # Billed every month
        assert data["spending_schedule"]["values"] == [499.00] * 6


def test_c_one_yearly_subscription(app, user_id):
    """Test C: One yearly subscription of ₹1,200/yr."""
    with app.app_context():
        user = db.session.get(User, user_id)
        today = date.today()
        # Set renewal date 2 months from today
        ren_date = today + relativedelta(months=2)
        sub = Subscription(
            user_id=user.id,
            service_name="Annual SaaS",
            monthly_cost=Decimal("1200.00"),
            category="Productivity",
            billing_cycle="Yearly",
            start_date=today,
            renewal_date=ren_date,
        )
        db.session.add(sub)
        db.session.commit()

        data = subscription_service.get_spending_analytics(user)
        assert data["summary"]["total_monthly"] == 100.00
        assert data["summary"]["total_yearly"] == 1200.00

        # In top subscriptions, monthly_equivalent should be 100.00, not 1200.00
        assert len(data["top_subscriptions"]) == 1
        assert data["top_subscriptions"][0]["monthly_equivalent"] == 100.00
        assert data["top_subscriptions"][0]["yearly_cost"] == 1200.00

        # Schedule must show payment of ₹1,200 in the renewal month (month index 2)
        values = data["spending_schedule"]["values"]
        assert values[0] == 0.0
        assert values[1] == 0.0
        assert values[2] == 1200.00
        assert values[3] == 0.0
        assert values[4] == 0.0
        assert values[5] == 0.0


def test_d_mixed_monthly_and_yearly(app, user_id):
    """Test D: Mixed monthly + yearly subscriptions (₹499/mo + ₹1,200/yr -> ₹599/mo)."""
    with app.app_context():
        user = db.session.get(User, user_id)
        today = date.today()
        # Monthly subscription: ₹499
        sub1 = Subscription(
            user_id=user.id,
            service_name="Spotify",
            monthly_cost=Decimal("499.00"),
            category="Music",
            billing_cycle="Monthly",
            start_date=today,
            renewal_date=today + relativedelta(months=1),
        )
        # Yearly subscription: ₹1,200 (renews in month index 1)
        sub2 = Subscription(
            user_id=user.id,
            service_name="Annual Gym",
            monthly_cost=Decimal("1200.00"),
            category="Fitness",
            billing_cycle="Yearly",
            start_date=today,
            renewal_date=today + relativedelta(months=1),
        )
        db.session.add_all([sub1, sub2])
        db.session.commit()

        data = subscription_service.get_spending_analytics(user)
        assert data["summary"]["total_monthly"] == 599.00
        assert data["summary"]["total_yearly"] == 7188.00

        # Month 0: Monthly only = 499.00
        # Month 1: Monthly (499.00) + Yearly (1200.00) = 1699.00
        # Month 2: Monthly only = 499.00
        values = data["spending_schedule"]["values"]
        assert values[0] == 499.00
        assert values[1] == 1699.00
        assert values[2] == 499.00


def test_e_category_totals(app, user_id):
    """Test E: Category totals sum to the authoritative total monthly spending."""
    with app.app_context():
        user = db.session.get(User, user_id)
        s1 = Subscription(
            user_id=user.id,
            service_name="Sub A",
            monthly_cost=Decimal("300.00"),
            category="Entertainment",
            billing_cycle="Monthly",
            start_date=date.today(),
            renewal_date=date.today() + relativedelta(months=1),
        )
        s2 = Subscription(
            user_id=user.id,
            service_name="Sub B",
            monthly_cost=Decimal("2400.00"),
            category="Productivity",
            billing_cycle="Yearly",  # monthly_equivalent = 200.00
            start_date=date.today(),
            renewal_date=date.today() + relativedelta(years=1),
        )
        db.session.add_all([s1, s2])
        db.session.commit()

        data = subscription_service.get_spending_analytics(user)
        cat_sum = sum(c["monthly_amount"] for c in data["categories"])
        assert round(cat_sum, 2) == data["summary"]["total_monthly"]
        assert data["summary"]["total_monthly"] == 500.00


def test_f_category_percentages(app, user_id):
    """Test F: Category percentages sum to 100.0% without division-by-zero errors."""
    with app.app_context():
        user = db.session.get(User, user_id)
        s1 = Subscription(
            user_id=user.id,
            service_name="Sub A",
            monthly_cost=Decimal("600.00"),
            category="Entertainment",
            billing_cycle="Monthly",
            start_date=date.today(),
            renewal_date=date.today() + relativedelta(months=1),
        )
        s2 = Subscription(
            user_id=user.id,
            service_name="Sub B",
            monthly_cost=Decimal("400.00"),
            category="Utilities",
            billing_cycle="Monthly",
            start_date=date.today(),
            renewal_date=date.today() + relativedelta(months=1),
        )
        db.session.add_all([s1, s2])
        db.session.commit()

        data = subscription_service.get_spending_analytics(user)
        assert len(data["categories"]) == 2
        ent = next(c for c in data["categories"] if c["name"] == "Entertainment")
        util = next(c for c in data["categories"] if c["name"] == "Utilities")
        assert ent["percentage"] == 60.0
        assert util["percentage"] == 40.0
        assert sum(c["percentage"] for c in data["categories"]) == 100.0


def test_g_subscription_spending_ranking(app, user_id):
    """Test G: Subscriptions are ranked by monthly equivalent, not raw yearly amount."""
    with app.app_context():
        user = db.session.get(User, user_id)
        # Sub 1: Monthly ₹1,500/mo
        s1 = Subscription(
            user_id=user.id,
            service_name="Dedicated Server",
            monthly_cost=Decimal("1500.00"),
            category="Work",
            billing_cycle="Monthly",
            start_date=date.today(),
            renewal_date=date.today() + relativedelta(months=1),
        )
        # Sub 2: Yearly ₹12,000/yr (monthly equivalent ₹1,000/mo)
        s2 = Subscription(
            user_id=user.id,
            service_name="Annual Software License",
            monthly_cost=Decimal("12000.00"),
            category="Work",
            billing_cycle="Yearly",
            start_date=date.today(),
            renewal_date=date.today() + relativedelta(years=1),
        )
        db.session.add_all([s1, s2])
        db.session.commit()

        data = subscription_service.get_spending_analytics(user)
        top = data["top_subscriptions"]
        assert len(top) == 2
        # Dedicated Server (₹1,500/mo) MUST be ranked ahead of Annual Software (₹1,000/mo)
        assert top[0]["service_name"] == "Dedicated Server"
        assert top[0]["monthly_equivalent"] == 1500.00
        assert top[1]["service_name"] == "Annual Software License"
        assert top[1]["monthly_equivalent"] == 1000.00


def test_h_potential_savings_billing_cycle_aware(app, user_id):
    """Test H: Potential savings correctly converts yearly amounts to monthly equivalents."""
    with app.app_context():
        user = db.session.get(User, user_id)
        # Underutilized yearly subscription
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

        data = subscription_service.get_spending_analytics(user)
        # 12000 / 12 = 1000.00 monthly savings
        assert data["summary"]["potential_monthly_savings"] == 1000.00
        assert data["summary"]["potential_yearly_savings"] == 12000.00


def test_i_dashboard_vs_analytics_consistency(app, user_id):
    """Test I: Dashboard and Analytics produce identical financial totals."""
    with app.app_context():
        user = db.session.get(User, user_id)
        subscription_service.add_subscription(
            user=user,
            service_name="Streaming Pro",
            monthly_cost=Decimal("699.00"),
            category="Entertainment",
            start_date="2026-01-01",
            billing_cycle="Monthly",
        )
        subscription_service.add_subscription(
            user=user,
            service_name="Cloud Backup",
            monthly_cost=Decimal("3600.00"),
            category="Utilities",
            start_date="2026-01-01",
            billing_cycle="Yearly",
        )

        auth_svc = AuthService()
        dash = auth_svc.get_dashboard_data(user)
        analytics = subscription_service.get_spending_analytics(user)

        assert dash["total_monthly"] == analytics["summary"]["total_monthly"]
        assert dash["total_yearly"] == analytics["summary"]["total_yearly"]
        assert dash["total_subscriptions"] == analytics["summary"]["active_subscriptions"]
        assert dash["potential_monthly_savings"] == analytics["summary"]["potential_monthly_savings"]
        assert dash["potential_yearly_savings"] == analytics["summary"]["potential_yearly_savings"]


def test_j_intelligence_vs_analytics_consistency(app, user_id):
    """Test J: IntelligenceService context and Analytics data align strictly."""
    with app.app_context():
        user = db.session.get(User, user_id)
        subscription_service.add_subscription(
            user=user,
            service_name="Tool",
            monthly_cost=Decimal("500.00"),
            category="Productivity",
            start_date="2026-01-01",
            billing_cycle="Monthly",
        )

        intel = intelligence_service.build_intelligence_context(user)
        analytics = subscription_service.get_spending_analytics(user)

        assert intel["financial_summary"]["monthly_spending"] == analytics["summary"]["total_monthly"]
        assert intel["financial_summary"]["yearly_projection"] == analytics["summary"]["total_yearly"]
        assert intel["financial_summary"]["potential_monthly_savings"] == analytics["summary"]["potential_monthly_savings"]
        assert len(intel["categories"]) == len(analytics["categories"])


def test_k_health_score_data_consistency(app, user_id):
    """Test K: Health score is consistent and between 0 and 100."""
    with app.app_context():
        user = db.session.get(User, user_id)
        score_obj = intelligence_service.calculate_health_score(user)
        assert 0 <= score_obj["score"] <= 100


def test_l_api_analytics_serialization(client, app, user_id):
    """Test L: GET /api/analytics returns valid JSON with numbers and no Decimal errors."""
    with app.app_context():
        user = db.session.get(User, user_id)
        subscription_service.add_subscription(
            user=user,
            service_name="Dev Tool",
            monthly_cost=Decimal("899.50"),
            category="Productivity",
            start_date="2026-01-01",
            billing_cycle="Monthly",
        )
        token = create_access_token(identity=str(user.id))

    res = client.get(
        "/api/analytics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    payload = data["data"]

    # Verify numbers are serialized as float/int
    assert isinstance(payload["summary"]["total_monthly"], (int, float))
    assert payload["summary"]["total_monthly"] == 899.50
    assert isinstance(payload["spending_schedule"]["values"][0], (int, float))
    assert len(payload["categories"]) == 1
    assert isinstance(payload["categories"][0]["monthly_amount"], (int, float))


def test_m_no_fabricated_historical_data(app, user_id):
    """Test M: Schedule months are forward-looking next 6 months, not fake historical data."""
    with app.app_context():
        user = db.session.get(User, user_id)
        data = subscription_service.get_spending_analytics(user)
        months = data["spending_schedule"]["months"]
        today = date.today()
        expected_months = [(today + relativedelta(months=i)).strftime("%b") for i in range(6)]
        assert months == expected_months


def test_n_actual_payment_events_schedule(app, user_id):
    """Test N: 6-month schedule represents actual payment events based on cycle and renewal date."""
    with app.app_context():
        user = db.session.get(User, user_id)
        today = date.today()

        # Monthly: ₹300
        sub_monthly = Subscription(
            user_id=user.id,
            service_name="Monthly Sub",
            monthly_cost=Decimal("300.00"),
            category="Work",
            billing_cycle="Monthly",
            start_date=today,
            renewal_date=today + relativedelta(months=1),
        )
        # Yearly: ₹5,000, renews in month index 3
        sub_yearly = Subscription(
            user_id=user.id,
            service_name="Yearly Sub",
            monthly_cost=Decimal("5000.00"),
            category="Work",
            billing_cycle="Yearly",
            start_date=today,
            renewal_date=today + relativedelta(months=3),
        )
        db.session.add_all([sub_monthly, sub_yearly])
        db.session.commit()

        data = subscription_service.get_spending_analytics(user)
        vals = data["spending_schedule"]["values"]

        # Month 0: 300
        # Month 1: 300
        # Month 2: 300
        # Month 3: 300 + 5000 = 5300
        # Month 4: 300
        # Month 5: 300
        assert vals[0] == 300.00
        assert vals[1] == 300.00
        assert vals[2] == 300.00
        assert vals[3] == 5300.00
        assert vals[4] == 300.00
        assert vals[5] == 300.00


def test_o_no_nan_or_infinite_values(app, user_id):
    """Test O: All numeric fields in Analytics payload are finite numbers."""
    with app.app_context():
        user = db.session.get(User, user_id)
        subscription_service.add_subscription(
            user=user,
            service_name="Valid Sub",
            monthly_cost=Decimal("150.00"),
            category="Utilities",
            start_date="2026-01-01",
            billing_cycle="Monthly",
        )

        data = subscription_service.get_spending_analytics(user)

        def check_finite(obj):
            if isinstance(obj, float):
                assert not math.isnan(obj)
                assert not math.isinf(obj)
            elif isinstance(obj, dict):
                for v in obj.values():
                    check_finite(v)
            elif isinstance(obj, (list, tuple)):
                for v in obj:
                    check_finite(v)

        check_finite(data)
