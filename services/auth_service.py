"""Service layer for authentication and account-related business logic.

Services contain the application's business rules and orchestrate repository
calls without directly handling HTTP requests.
"""

import random
import secrets
from datetime import datetime, date, timedelta

from flask_jwt_extended import create_access_token
from werkzeug.security import check_password_hash, generate_password_hash

from exceptions.exceptions import (
    AuthenticationException,
    BusinessLogicException,
    DatabaseException,
    ResourceNotFoundException,
    ValidationException,
)
from logging_config.logger import logger
from models.user import User
from repositories.subscription_repository import SubscriptionRepository
from repositories.user_repository import UserRepository
from services.email_service import email_service
from services.intelligence_service import IntelligenceService
from services.otp_service import otp_service
from utils.insights_engine import generate_insight


class AuthService:
    """Encapsulate authentication and account-related business logic."""

    def __init__(self):
        self.user_repository = UserRepository()
        self.subscription_repository = SubscriptionRepository()
        self.intelligence_service = IntelligenceService(self.subscription_repository)
        self.email_service = email_service
        self.otp_service = otp_service

    def generate_username_suggestions(self, username):
        """Generate alternative usernames when a chosen username is taken."""
        suggestions = []
        tried = set()

        patterns = [
            lambda u: f"{u}_{random.randint(10, 99)}",
            lambda u: f"{u}{random.randint(100, 999)}",
            lambda u: f"{u}_dev",
            lambda u: f"{u}_pro",
            lambda u: f"{u}_ai",
            lambda u: f"{u}x",
            lambda u: f"{u}_{random.choice(['official', 'user', 'app'])}",
        ]

        while len(suggestions) < 3:
            candidate = random.choice(patterns)(username)

            if candidate in tried:
                continue

            tried.add(candidate)

            if not self.user_repository.get_user_by_username(candidate):
                suggestions.append(candidate)

        return suggestions

    def register_user(self, username, email, mobile_number, password, occupation, financial_preference, base_url="http://localhost:5000"):
        """Create a new user account with email verification token."""
        if self.user_repository.get_user_by_username(username):
            logger.warning("Registration failed: username already exists")
            raise ValidationException(f'Username "{username}" is already taken.')

        if self.user_repository.get_user_by_email(email):
            logger.warning("Registration failed: email already exists")
            raise ValidationException("An account with this email already exists.")

        clean_mobile = (mobile_number or "").strip() or None
        if clean_mobile and self.user_repository.get_user_by_mobile_number(clean_mobile):
            logger.warning("Registration failed: mobile number already exists")
            raise ValidationException("An account with this mobile number already exists.")

        hashed_password = generate_password_hash(password)
        verification_token = secrets.token_urlsafe(32)
        verification_expiry = datetime.utcnow() + timedelta(hours=24)

        user = User(
            username=username,
            email=email,
            mobile_number=clean_mobile,
            password=hashed_password,
            occupation=occupation,
            financial_preference=financial_preference,
            email_verified=False,
            verification_token=verification_token,
            verification_token_expiry=verification_expiry,
        )
        try:
            self.user_repository.save_user(user)
            logger.info("Registration completed successfully")
        except Exception as exc:
            logger.error("Database failure while creating user account")
            raise DatabaseException("Unable to create user account") from exc

        verification_url = f"{base_url.rstrip('/')}/verify-email/{verification_token}"
        self.email_service.send_verification_email(email, verification_url)
        logger.info("Verification email sent")
        return user

    def verify_email(self, token):
        """Verify an email token, activate user account, and clear token."""
        if not token:
            logger.warning("Verification failed: empty token provided")
            raise ValidationException("Invalid or expired verification link.")

        user = self.user_repository.get_user_by_verification_token(token)
        if not user:
            logger.warning("Verification failed: token not found")
            raise ValidationException("Invalid or expired verification link.")

        if user.verification_token_expiry and user.verification_token_expiry < datetime.utcnow():
            logger.warning("Verification failed: token expired")
            raise ValidationException("Invalid or expired verification link.")

        user.email_verified = True
        user.verification_token = None
        user.verification_token_expiry = None
        self.user_repository.update_user(user)
        logger.info("Verification completed")
        return user

    def resend_verification(self, email, base_url="http://localhost:5000"):
        """Resend a new verification email for an unverified account."""
        user = self.user_repository.get_user_by_email(email)
        if not user or user.email_verified:
            logger.info("Resend verification requested for non-existent or already verified email")
            return True

        verification_token = secrets.token_urlsafe(32)
        user.verification_token = verification_token
        user.verification_token_expiry = datetime.utcnow() + timedelta(hours=24)
        self.user_repository.update_user(user)

        verification_url = f"{base_url.rstrip('/')}/verify-email/{verification_token}"
        self.email_service.send_verification_email(email, verification_url)
        logger.info("Resend verification email sent")
        return True

    def authenticate_user(self, email, password):
        """Authenticate a user by email and password."""
        user = self.user_repository.get_user_by_email(email)
        if user and check_password_hash(user.password, password):
            logger.info("User authenticated successfully")
            return user
        logger.warning("Authentication failed")
        raise AuthenticationException("Invalid email or password.")

    def request_password_reset(self, email, base_url="http://localhost:5000"):
        """Initiate password reset by generating reset token (30-min expiry)."""
        user = self.user_repository.get_user_by_email(email)
        if not user:
            logger.info("Password reset requested for non-existent email")
            return True

        reset_token = secrets.token_urlsafe(32)
        user.reset_token = reset_token
        user.reset_token_expiry = datetime.utcnow() + timedelta(minutes=30)
        self.user_repository.update_user(user)

        reset_url = f"{base_url.rstrip('/')}/reset-password/{reset_token}"
        self.email_service.send_password_reset_email(email, reset_url)
        logger.info("Password reset requested")
        return True

    def reset_password(self, token, new_password):
        """Reset user password using a valid reset token."""
        if not token:
            logger.warning("Password reset failed: empty token provided")
            raise ValidationException("Invalid or expired password reset link.")

        user = self.user_repository.get_user_by_reset_token(token)
        if not user or not user.reset_token_expiry or user.reset_token_expiry < datetime.utcnow():
            logger.warning("Password reset failed: invalid or expired token")
            raise ValidationException("Invalid or expired password reset link.")

        user.password = generate_password_hash(new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        self.user_repository.update_user(user)
        logger.info("Password reset completed")
        return user

    def get_dashboard_data(self, user):
        """Prepare dashboard statistics and insights for the current user using authoritative intelligence."""
        subscriptions = self.subscription_repository.get_user_subscriptions(user.id)
        intel = self.intelligence_service.build_intelligence_context(user)
        fin_summary = intel.get("financial_summary", {})

        total_monthly = float(fin_summary.get("monthly_spending", 0.0))
        total_yearly = float(fin_summary.get("yearly_projection", 0.0))
        potential_monthly_savings = float(fin_summary.get("potential_monthly_savings", 0.0))
        potential_yearly_savings = float(fin_summary.get("potential_yearly_savings", 0.0))
        total_subscriptions = len(subscriptions)

        today = date.today()
        next_week = today + timedelta(days=7)
        upcoming_renewals = self.subscription_repository.get_upcoming_renewals(user.id, today, next_week)

        # Category chart data using monthly equivalent
        category_labels = [cat["name"] for cat in intel.get("categories", [])]
        category_values = [float(cat["monthly_spending"]) for cat in intel.get("categories", [])]

        subscription_labels = [sub.service_name for sub in subscriptions]
        subscription_values = [float(round(sub.monthly_equivalent, 2)) for sub in subscriptions]

        recommendations = intel.get("recommendations", [])
        health_score = int(intel.get("health_score", {}).get("score", 100))

        return {
            "total_monthly": total_monthly,
            "total_yearly": total_yearly,
            "total_subscriptions": total_subscriptions,
            "upcoming_renewals": upcoming_renewals,
            "category_labels": category_labels,
            "category_values": category_values,
            "subscription_labels": subscription_labels,
            "subscription_values": subscription_values,
            "recommendations": recommendations,
            "health_score": health_score,
            "potential_monthly_savings": potential_monthly_savings,
            "potential_yearly_savings": potential_yearly_savings,
        }

    def get_profile_summary(self, user):
        """Prepare profile summary values for the current user."""
        subscriptions = self.subscription_repository.get_user_subscriptions(user.id)
        total_subscriptions = len(subscriptions)
        total_monthly_dec = sum(sub.monthly_equivalent for sub in subscriptions)
        total_yearly_dec = sum(sub.yearly_equivalent for sub in subscriptions)
        return {
            "total_subscriptions": total_subscriptions,
            "total_monthly": float(round(total_monthly_dec, 2)),
            "total_yearly": float(round(total_yearly_dec, 2)),
        }

    def update_profile(self, user, username, occupation, financial_preference):
        """Update the current user's profile details."""
        user.username = username
        user.occupation = occupation
        user.financial_preference = financial_preference
        self.user_repository.update_user(user)
        logger.info("Profile updated")
        return user

    def get_user_by_id(self, user_id):
        """Return a user by ID for JWT-based API requests."""
        return self.user_repository.get_user_by_id(user_id)

    def get_user_profile_data(self, user_id):
        """Build a safe JSON payload for a JWT-authenticated user profile."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise ResourceNotFoundException("User not found")

        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "mobile_number": user.mobile_number,
            "occupation": user.occupation,
            "financial_preference": user.financial_preference,
            "email_verified": user.email_verified,
        }

    def login_with_jwt(self, email, password):
        """Authenticate a user and issue a JWT access token for API use."""
        user = self.authenticate_user(email, password)
        if not user:
            raise AuthenticationException("Invalid email or password.")

        token = create_access_token(identity=str(user.id))
        logger.info("JWT access token issued")
        return {
            "access_token": token,
            "user": self.get_user_profile_data(user.id),
        }


auth_service = AuthService()
