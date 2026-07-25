"""Controller layer for JWT-based API requests.

These controllers receive HTTP requests, validate the incoming JSON payload,
and delegate the work to services so the business logic remains reusable.
"""

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from exceptions.exceptions import ValidationException
from logging_config.logger import logger
from services.auth_service import auth_service
from services.subscription_service import subscription_service
from validators.auth_validator import auth_validator
from validators.subscription_validator import subscription_validator


def json_success(message, data=None, status_code=200):
    """Return a consistent success payload for API responses."""
    payload = {"success": True, "message": message}
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status_code


def json_error(message, errors=None, status_code=400):
    """Return a consistent error payload for API responses."""
    payload = {"success": False, "message": message}
    if errors is not None:
        payload["errors"] = errors
    return jsonify(payload), status_code


def api_register():
    """Register a new user via the REST API."""
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""
    occupation = (payload.get("occupation") or "").strip()
    financial_preference = (payload.get("financial_preference") or "").strip()

    try:
        auth_validator.validate_registration(
        {
            "username": username,
            "email": email,
            "password": password,
            "confirm_password": payload.get("confirm_password"),
        }
    )

        user = auth_service.register_user(
        username=username,
        email=email,
        password=password,
        occupation=occupation,
        financial_preference=financial_preference,
    )

        logger.info("API registration completed successfully")
        return json_success("Registration successful", {"user": auth_service.get_user_profile_data(user.id)}, status_code=201)
    except ValidationException as exc:
        logger.warning("API registration validation failed: %s", str(exc))
        raise


def api_login():
    """Authenticate a user and issue a JWT access token."""
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""

    try:
        auth_validator.validate_login({"email": email, "password": password})
        token_data = auth_service.login_with_jwt(email, password)
    except ValidationException as exc:
        logger.warning("API login validation failed: %s", str(exc))
        raise

    logger.info("API login completed successfully")
    return json_success("Login successful", token_data, status_code=200)


@jwt_required()
def api_profile():
    """Return the authenticated user's profile via JWT."""
    user_id = get_jwt_identity()
    user_data = auth_service.get_user_profile_data(user_id)
    return json_success("Profile fetched successfully", {"user": user_data})


@jwt_required()
def api_subscriptions():
    """Return the current user's subscriptions via JWT."""
    user_id = get_jwt_identity()
    user = auth_service.get_user_by_id(user_id)

    subscriptions = subscription_service.get_user_subscriptions_for_api(user)
    return json_success("Subscriptions fetched successfully", {"subscriptions": subscriptions})


@jwt_required()
def create_api_subscription():
    """Create a subscription for the authenticated user via JWT."""
    payload = request.get_json(silent=True) or {}
    user_id = get_jwt_identity()
    user = auth_service.get_user_by_id(user_id)

    try:
        subscription_validator.validate_create(payload)
        subscription = subscription_service.add_subscription(
        user=user,
        service_name=payload.get("service_name", "").strip(),
        monthly_cost=payload.get("monthly_cost"),
        category=payload.get("category"),
        start_date=payload.get("start_date"),
        billing_cycle=payload.get("billing_cycle"),
        usage_frequency=payload.get("usage_frequency"),
        usage_hours=payload.get("usage_hours"),
    )

        logger.info("API subscription created")
        return json_success("Subscription created successfully", {"subscription": subscription_service.serialize_subscription(subscription)}, status_code=201)
    except ValidationException as exc:
        logger.warning("API subscription validation failed: %s", str(exc))
        raise


@jwt_required()
def update_api_subscription(subscription_id):
    """Update an existing subscription via JWT."""
    payload = request.get_json(silent=True) or {}
    user_id = get_jwt_identity()
    user = auth_service.get_user_by_id(user_id)

    try:
        subscription_validator.validate_update(payload)
        subscription = subscription_service.update_subscription(
        user=user,
        subscription_id=subscription_id,
        service_name=payload.get("service_name", "").strip(),
        monthly_cost=payload.get("monthly_cost"),
        category=payload.get("category"),
        start_date=payload.get("start_date"),
        billing_cycle=payload.get("billing_cycle"),
        usage_frequency=payload.get("usage_frequency"),
        usage_hours=payload.get("usage_hours"),
    )

        logger.info("API subscription updated")
        return json_success("Subscription updated successfully", {"subscription": subscription_service.serialize_subscription(subscription)})
    except ValidationException as exc:
        logger.warning("API subscription validation failed: %s", str(exc))
        raise


@jwt_required()
def delete_api_subscription(subscription_id):
    """Delete a subscription via JWT."""
    user_id = get_jwt_identity()
    user = auth_service.get_user_by_id(user_id)

    subscription_service.delete_subscription(subscription_id)
    logger.info("API subscription deleted")

    return json_success("Subscription deleted successfully", None, 200)
