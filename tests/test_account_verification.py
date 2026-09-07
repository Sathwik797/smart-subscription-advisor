"""Comprehensive test suite for Production Account Verification System."""

import logging
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager

from config import Config
from database.db import db
from exceptions.exceptions import AuthenticationException, ValidationException
from models.user import User
from routes.api.auth import api_auth
from routes.auth import auth
from services.auth_service import AuthService


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-that-is-at-least-32-bytes-long"
    JWT_SECRET_KEY = "test-secret-that-is-at-least-32-bytes-long"
    WTF_CSRF_ENABLED = False


@pytest.fixture
def app():
    app = Flask(__name__, template_folder=str(Path(__file__).resolve().parents[1] / "templates"))
    app.config.from_object(TestConfig)

    db.init_app(app)
    JWTManager(app)

    app.register_blueprint(auth)
    app.register_blueprint(api_auth, url_prefix="/api")

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def auth_service(app):
    return AuthService()


def test_registration_success_and_email_unverified_by_default(app, auth_service):
    with app.app_context():
        user = auth_service.register_user(
            username="john_doe",
            email="john@example.com",
            mobile_number="9876543210",
            password="Password123!",
            occupation="Software Developer",
            financial_preference="Money Saver",
        )

        assert user is not None
        assert user.email == "john@example.com"
        assert user.mobile_number == "9876543210"
        assert user.email_verified is False
        assert user.verification_token is not None
        assert user.verification_token_expiry > datetime.utcnow()


def test_duplicate_mobile_number_rejected(app, auth_service):
    with app.app_context():
        auth_service.register_user(
            username="user1",
            email="user1@example.com",
            mobile_number="9876543210",
            password="Password123!",
            occupation="Student",
            financial_preference="Balanced",
        )

        with pytest.raises(ValidationException) as exc_info:
            auth_service.register_user(
                username="user2",
                email="user2@example.com",
                mobile_number="9876543210",
                password="Password123!",
                occupation="Designer",
                financial_preference="Balanced",
            )
        assert "mobile number already exists" in str(exc_info.value)


def test_duplicate_email_rejected(app, auth_service):
    with app.app_context():
        auth_service.register_user(
            username="user1",
            email="user1@example.com",
            mobile_number="9876543210",
            password="Password123!",
            occupation="Student",
            financial_preference="Balanced",
        )

        with pytest.raises(ValidationException) as exc_info:
            auth_service.register_user(
                username="user2",
                email="user1@example.com",
                mobile_number="8876543210",
                password="Password123!",
                occupation="Designer",
                financial_preference="Balanced",
            )
        assert "email already exists" in str(exc_info.value)


def test_mobile_number_validation_formats(app):
    from validators.auth_validator import auth_validator

    # Valid mobile numbers starting with 6, 7, 8, 9
    for valid_mobile in ["6123456789", "7890123456", "8901234567", "9876543210"]:
        assert auth_validator.validate_mobile_number(valid_mobile) == valid_mobile

    # Invalid mobile numbers
    invalid_mobiles = [
        "5123456789",  # Starts with 5
        "987654321",   # 9 digits
        "98765432100", # 11 digits
        "98765abcde",  # Letters
        "",
    ]
    for invalid in invalid_mobiles:
        with pytest.raises(ValidationException):
            auth_validator.validate_mobile_number(invalid)


def test_unverified_user_can_login(app, auth_service):
    with app.app_context():
        user = auth_service.register_user(
            username="unverified_user",
            email="unverified@example.com",
            mobile_number="7876543210",
            password="Password123!",
            occupation="Student",
            financial_preference="Money Saver",
        )
        assert user.email_verified is False

        authenticated = auth_service.authenticate_user("unverified@example.com", "Password123!")
        assert authenticated is not None
        assert authenticated.id == user.id


def test_token_email_verification_flow(app, auth_service):
    with app.app_context():
        user = auth_service.register_user(
            username="verifiable_user",
            email="verify_me@example.com",
            mobile_number="6876543210",
            password="Password123!",
            occupation="Student",
            financial_preference="Money Saver",
        )

        token = user.verification_token
        verified_user = auth_service.verify_email(token)

        assert verified_user.email_verified is True
        assert verified_user.verification_token is None
        assert verified_user.verification_token_expiry is None

        # Post verification login should succeed!
        authenticated = auth_service.authenticate_user("verify_me@example.com", "Password123!")
        assert authenticated.id == verified_user.id


def test_expired_verification_token_rejected(app, auth_service):
    with app.app_context():
        user = auth_service.register_user(
            username="expired_token_user",
            email="expired@example.com",
            mobile_number="9988776655",
            password="Password123!",
            occupation="Student",
            financial_preference="Money Saver",
        )

        # Force expiry to the past
        user.verification_token_expiry = datetime.utcnow() - timedelta(hours=1)
        db.session.commit()

        with pytest.raises(ValidationException) as exc_info:
            auth_service.verify_email(user.verification_token)

        assert "Invalid or expired" in str(exc_info.value)


def test_resend_verification_email(app, auth_service):
    with app.app_context():
        user = auth_service.register_user(
            username="resend_user",
            email="resend@example.com",
            mobile_number="8899001122",
            password="Password123!",
            occupation="Student",
            financial_preference="Money Saver",
        )
        old_token = user.verification_token

        auth_service.resend_verification("resend@example.com")

        updated_user = User.query.filter_by(email="resend@example.com").first()
        assert updated_user.verification_token != old_token
        assert updated_user.verification_token_expiry > datetime.utcnow()


def test_forgot_and_reset_password_flow(app, auth_service):
    with app.app_context():
        user = auth_service.register_user(
            username="reset_user",
            email="reset@example.com",
            mobile_number="7788990011",
            password="OldPassword123!",
            occupation="Student",
            financial_preference="Money Saver",
        )
        auth_service.verify_email(user.verification_token)

        auth_service.request_password_reset("reset@example.com")
        updated_user = User.query.filter_by(email="reset@example.com").first()
        assert updated_user.reset_token is not None
        assert updated_user.reset_token_expiry > datetime.utcnow()

        # Perform password reset
        reset_token = updated_user.reset_token
        auth_service.reset_password(reset_token, "NewPassword123!")

        # Verify old password fails, new password succeeds
        with pytest.raises(AuthenticationException):
            auth_service.authenticate_user("reset@example.com", "OldPassword123!")

        new_auth = auth_service.authenticate_user("reset@example.com", "NewPassword123!")
        assert new_auth.id == user.id


def test_expired_reset_token_rejected(app, auth_service):
    with app.app_context():
        user = auth_service.register_user(
            username="expired_reset_user",
            email="expired_reset@example.com",
            mobile_number="6677889900",
            password="Password123!",
            occupation="Student",
            financial_preference="Money Saver",
        )

        auth_service.request_password_reset("expired_reset@example.com")
        updated_user = User.query.filter_by(email="expired_reset@example.com").first()
        updated_user.reset_token_expiry = datetime.utcnow() - timedelta(minutes=1)
        db.session.commit()

        with pytest.raises(ValidationException) as exc_info:
            auth_service.reset_password(updated_user.reset_token, "NewPassword123!")

        assert "Invalid or expired" in str(exc_info.value)


def test_logging_security_no_sensitive_data_leaked(caplog):
    caplog.set_level(logging.DEBUG)
    logger = logging.getLogger("subscription_assistant")

    secret_password = "SuperSecretPassword123!"
    secret_token = "ultra-secret-token-xyz-99"

    logger.info("Registration completed successfully")
    logger.info("Verification completed")

    for record in caplog.records:
        assert secret_password not in record.message
        assert secret_token not in record.message
