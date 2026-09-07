"""Protected API routes for subscription management using JWT."""

from flask import Blueprint

from controllers.api_controller import (
    api_analytics,
    api_intelligence,
    api_profile,
    api_subscriptions,
    create_api_subscription,
    delete_api_subscription,
    get_api_subscription,
    update_api_subscription,
)

api_subscriptions_bp = Blueprint("api_subscriptions", __name__)


@api_subscriptions_bp.route("/analytics", methods=["GET"])
def analytics():
    return api_analytics()


@api_subscriptions_bp.route("/intelligence", methods=["GET"])
def intelligence():
    return api_intelligence()


@api_subscriptions_bp.route("/profile", methods=["GET"])
def profile():
    return api_profile()


@api_subscriptions_bp.route("/subscriptions", methods=["GET"])
def subscriptions():
    return api_subscriptions()


@api_subscriptions_bp.route("/subscriptions", methods=["POST"])
def create_subscription():
    return create_api_subscription()


@api_subscriptions_bp.route("/subscriptions/<int:subscription_id>", methods=["GET"])
def get_subscription(subscription_id):
    return get_api_subscription(subscription_id)


@api_subscriptions_bp.route("/subscriptions/<int:subscription_id>", methods=["PUT"])
def update_subscription(subscription_id):
    return update_api_subscription(subscription_id)


@api_subscriptions_bp.route("/subscriptions/<int:subscription_id>", methods=["DELETE"])
def delete_subscription(subscription_id):
    return delete_api_subscription(subscription_id)
