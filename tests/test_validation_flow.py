import os
from pathlib import Path
from unittest.mock import patch

import pytest
from flask import Flask

from controllers.auth_controller import register as auth_register
from controllers.subscription_controller import add_subscription as add_subscription_view
from exceptions.exceptions import ValidationException
from routes.auth import auth
import routes.subscription  # noqa: F401


from flask_jwt_extended import JWTManager

@pytest.fixture
def app():
    app = Flask(__name__, template_folder=str(Path(__file__).resolve().parents[1] / "templates"))
    app.secret_key = "test-secret-that-is-at-least-32-bytes-long"
    app.config["JWT_SECRET_KEY"] = "test-secret-that-is-at-least-32-bytes-long"
    JWTManager(app)
    app.register_blueprint(auth)
    return app




def test_auth_registration_invalid_payload_is_rejected_before_service(app):
    with app.test_request_context(
        "/register",
        method="POST",
        data={
            "username": "ab",
            "email": "user@example.com",
            "password": "password123",
        },
    ):
        with patch("controllers.auth_controller.auth_service.register_user", return_value=None) as mock_register:
            with patch("controllers.auth_controller.auth_service.generate_username_suggestions", return_value=[]) as mock_suggestions:
                response = auth_register()

        assert isinstance(response, str)
        mock_register.assert_not_called()
        mock_suggestions.assert_called_once_with("ab")


def test_subscription_creation_invalid_payload_is_rejected_before_service(app):
    with app.test_request_context(
        "/add-subscription",
        method="POST",
        data={
            "service_name": "Netflix",
            "monthly_cost": "-1",
            "category": "Entertainment",
            "start_date": "2024-01-01",
            "billing_cycle": "Monthly",
            "usage_frequency": "Often",
            "usage_hours": "5",
        },
    ):
        with patch("controllers.subscription_controller.subscription_service.add_subscription", return_value=None) as mock_add:
            response = add_subscription_view()

        assert response.status_code == 302
        mock_add.assert_not_called()


def test_auth_registration_missing_required_fields_is_rejected_before_service(app):
    with app.test_request_context(
        "/register",
        method="POST",
        data={
            "email": "user@example.com",
            "password": "password123",
        },
    ):
        with patch("controllers.auth_controller.auth_service.register_user", return_value=None) as mock_register:
            with patch("controllers.auth_controller.auth_service.generate_username_suggestions", return_value=[]) as mock_suggestions:
                response = auth_register()

        assert isinstance(response, str)
        mock_register.assert_not_called()
        mock_suggestions.assert_called_once_with("")


def test_api_registration_invalid_payload_raises_validation_exception(app):
    with app.test_request_context(
        "/api/register",
        method="POST",
        json={"username": "ab", "email": "user@example.com", "password": "password123"},
    ):
        with patch("controllers.api_controller.auth_service.register_user", return_value=None) as mock_register:
            with pytest.raises(ValidationException):
                from controllers.api_controller import api_register

                api_register()

        mock_register.assert_not_called()
