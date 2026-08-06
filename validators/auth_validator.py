"""Validation helpers for authentication-related requests.

Validation is kept separate from business logic so controllers can reject bad
input early, while services remain focused on domain behavior.
"""

import re

from exceptions.exceptions import ValidationException


class AuthValidator:
    """Validate registration, mobile numbers, login, and password reset inputs."""

    EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    MOBILE_REGEX = r"^[6-9]\d{9}$"

    @staticmethod
    def validate_mobile_number(mobile_number):
        """Validate mobile number (Must be 10 digits, numeric, starting with 6, 7, 8, or 9)."""
        mobile = (mobile_number or "").strip()
        if not mobile:
            raise ValidationException("Mobile number is required")
        if not re.match(AuthValidator.MOBILE_REGEX, mobile):
            raise ValidationException("Mobile number must be 10 digits starting with 6, 7, 8, or 9")
        return mobile

    @staticmethod
    def validate_email(email):
        """Validate email format."""
        clean_email = (email or "").strip()
        if not clean_email:
            raise ValidationException("Email is required")
        if not re.match(AuthValidator.EMAIL_REGEX, clean_email):
            raise ValidationException("Email format is invalid")
        return clean_email

    @staticmethod
    def validate_registration(data):
        """Validate all fields required for user registration."""
        username = (data.get("username") or "").strip()
        email = (data.get("email") or "").strip()
        mobile_number = (data.get("mobile_number") or "").strip()
        password = data.get("password") or ""
        confirm_password = data.get("confirm_password")

        if not username:
            raise ValidationException("Username is required")
        if len(username) < 3:
            raise ValidationException("Username must be at least 3 characters")

        AuthValidator.validate_email(email)
        AuthValidator.validate_mobile_number(mobile_number)

        if not password:
            raise ValidationException("Password is required")
        if len(password) < 6:
            raise ValidationException("Password must be at least 6 characters")

        if confirm_password is None:
            raise ValidationException("Confirm Password is required")
        if confirm_password != password:
            raise ValidationException("Passwords do not match")

    @staticmethod
    def validate_login(data):
        """Validate login fields."""
        email = (data.get("email") or "").strip()
        password = data.get("password") or ""

        if not email:
            raise ValidationException("Email is required")
        if not password:
            raise ValidationException("Password is required")

    @staticmethod
    def validate_forgot_password(data):
        """Validate forgot password request payload."""
        email = (data.get("email") or "").strip()
        AuthValidator.validate_email(email)

    @staticmethod
    def validate_reset_password(data):
        """Validate reset password request payload."""
        password = data.get("password") or ""
        confirm_password = data.get("confirm_password") or ""

        if not password:
            raise ValidationException("New Password is required")
        if len(password) < 6:
            raise ValidationException("Password must be at least 6 characters")
        if not confirm_password:
            raise ValidationException("Confirm Password is required")
        if confirm_password != password:
            raise ValidationException("Passwords do not match")


auth_validator = AuthValidator()
