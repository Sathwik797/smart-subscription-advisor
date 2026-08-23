"""Controller layer for subscription-related requests.

Controllers receive incoming HTTP requests, perform light input validation,
delegate business work to services, and return Flask responses.
"""

from flask import Response, flash, redirect, render_template, request, url_for
from middleware.auth import current_user

from exceptions.exceptions import ValidationException
from logging_config.logger import logger
from services.subscription_service import subscription_service
from validators.subscription_validator import subscription_validator


def add_subscription():
    """Handle adding a subscription for the current user."""
    if request.method == "POST":
        service_name = request.form.get("service_name", "").strip()
        monthly_cost = request.form.get("monthly_cost")
        category = request.form.get("category")
        start_date = request.form.get("start_date")
        billing_cycle = request.form.get("billing_cycle")
        usage_frequency = request.form.get("usage_frequency")
        usage_hours = request.form.get("usage_hours")

        try:
            subscription_validator.validate_create(
                {
                    "service_name": service_name,
                    "monthly_cost": monthly_cost,
                    "category": category,
                    "start_date": start_date,
                    "billing_cycle": billing_cycle,
                    "usage_frequency": usage_frequency,
                    "usage_hours": usage_hours,
                }
            )
            subscription = subscription_service.add_subscription(
                user=current_user,
                service_name=service_name,
                monthly_cost=monthly_cost,
                category=category,
                start_date=start_date,
                billing_cycle=billing_cycle,
                usage_frequency=usage_frequency,
                usage_hours=usage_hours,
            )
            logger.info("Subscription created")
            flash("Subscription added successfully!", "success")
            return redirect(url_for("auth.subscriptions"))
        except ValidationException as exc:
            logger.warning("Subscription validation failed: %s", str(exc))
            if request.path.startswith("/api") or request.is_json:
                raise
            flash(str(exc), "danger")
            return redirect(url_for("auth.add_subscription"))
        except ValueError:
            flash("Please enter valid values in all fields.", "danger")
            return redirect(url_for("auth.add_subscription"))

    return render_template("add_subscription.html")


def subscriptions():
    """List subscriptions for the current user with optional filtering."""
    search = request.args.get("search", "")
    category = request.args.get("category", "")
    sort = request.args.get("sort", "")
    page = request.args.get("page", 1, type=int)

    paginated_subscriptions = subscription_service.get_user_subscriptions(
        user=current_user,
        search=search,
        category=category,
        sort=sort,
        page=page,
    )

    return render_template(
        "subscriptions.html",
        subscriptions=paginated_subscriptions,
        search=search,
        category=category,
        sort=sort,
    )


def export_csv():
    """Export the current user's subscriptions as CSV."""
    csv_content = subscription_service.build_subscription_csv(current_user)
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=subscriptions.csv"},
    )


def edit_subscription(id):
    """Handle editing a subscription."""
    subscription = subscription_service.get_subscription_for_editing(id)

    if request.method == "POST":
        try:
            subscription_validator.validate_update(
                {
                    "service_name": request.form.get("service_name"),
                    "monthly_cost": request.form.get("monthly_cost"),
                    "category": request.form.get("category"),
                    "start_date": request.form.get("start_date"),
                    "billing_cycle": request.form.get("billing_cycle"),
                    "usage_frequency": request.form.get("usage_frequency"),
                    "usage_hours": request.form.get("usage_hours"),
                }
            )
            subscription = subscription_service.update_subscription(
                user=current_user,
                subscription_id=id,
                service_name=request.form.get("service_name", ""),
                monthly_cost=request.form.get("monthly_cost"),
                category=request.form.get("category"),
                start_date=request.form.get("start_date"),
                billing_cycle=request.form.get("billing_cycle"),
                usage_frequency=request.form.get("usage_frequency"),
                usage_hours=request.form.get("usage_hours"),
            )
            logger.info("Subscription updated")
            flash("Subscription updated successfully!", "success")
            return redirect(url_for("auth.subscriptions"))
        except ValidationException as exc:
            flash(str(exc), "danger")
            return redirect(url_for("auth.edit_subscription", id=id))

    insight = subscription_service.get_subscription_insight(current_user, subscription)
    return render_template(
        "edit_subscription.html",
        subscription=subscription,
        insight=insight,
    )


def delete_subscription(id):
    """Delete a subscription for the current user."""
    subscription_service.delete_subscription(id)
    logger.info("Subscription deleted")
    flash("Subscription deleted successfully!", "success")
    return redirect(url_for("auth.subscriptions"))
