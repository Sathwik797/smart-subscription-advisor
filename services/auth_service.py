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
from services.otp_service import otp_service
from utils.insights_engine import generate_insight


class AuthService:
    """Encapsulate authentication and account-related business logic."""

    def __init__(self):
        self.user_repository = UserRepository()
        self.subscription_repository = SubscriptionRepository()
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

        if self.user_repository.get_user_by_mobile_number(mobile_number):
            logger.warning("Registration failed: mobile number already exists")
            raise ValidationException("An account with this mobile number already exists.")

        hashed_password = generate_password_hash(password)
        verification_token = secrets.token_urlsafe(32)
        verification_expiry = datetime.utcnow() + timedelta(hours=24)

        user = User(
            username=username,
            email=email,
            mobile_number=mobile_number,
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
        """Authenticate a user by email and password, enforcing email verification."""
        user = self.user_repository.get_user_by_email(email)
        if user and check_password_hash(user.password, password):
            if not user.email_verified:
                logger.warning("Authentication failed: unverified email")
                raise AuthenticationException("Please verify your email before logging in.")
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
        """Prepare dashboard statistics and insights for the current user."""
        subscriptions = self.subscription_repository.get_user_subscriptions(user.id)
        total_monthly = sum(sub.monthly_cost for sub in subscriptions)
        total_yearly = total_monthly * 12
        total_subscriptions = len(subscriptions)

        today = date.today()
        next_week = today + timedelta(days=7)
        upcoming_renewals = self.subscription_repository.get_upcoming_renewals(user.id, today, next_week)

        category_data = {}
        for sub in subscriptions:
            category_data[sub.category] = category_data.get(sub.category, 0) + sub.monthly_cost

        subscription_labels = [sub.service_name for sub in subscriptions]
        subscription_values = [sub.monthly_cost for sub in subscriptions]

        recommendations = []
        for sub in subscriptions:
            insight = generate_insight(subscription=sub, financial_preference=user.financial_preference)
            recommendations.append(insight)

        recommendations = sorted(recommendations, key=lambda item: item["score"], reverse=True)[:3]

        health_score = 100
        for sub in subscriptions:
            if sub.priority == "Low":
                health_score -= 15
            elif sub.priority == "Medium":
                health_score -= 5

            if sub.usage_frequency == "Rarely":
                health_score -= 10

            if sub.monthly_cost > 1000:
                health_score -= 5

        health_score = max(0, min(100, health_score))

        potential_monthly_savings = 0
        for sub in subscriptions:
            if sub.priority == "Low":
                potential_monthly_savings += sub.monthly_cost
            elif user.financial_preference == "Money Saver" and sub.usage_frequency == "Rarely":
                potential_monthly_savings += sub.monthly_cost

        potential_yearly_savings = potential_monthly_savings * 12

        return {
            "total_monthly": total_monthly,
            "total_yearly": total_yearly,
            "total_subscriptions": total_subscriptions,
            "upcoming_renewals": upcoming_renewals,
            "category_labels": list(category_data.keys()),
            "category_values": list(category_data.values()),
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
        total_monthly = sum(sub.monthly_cost for sub in subscriptions)
        total_yearly = total_monthly * 12
        return {
            "total_subscriptions": total_subscriptions,
            "total_monthly": total_monthly,
            "total_yearly": total_yearly,
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
