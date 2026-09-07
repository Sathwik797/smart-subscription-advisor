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
        is_ajax = (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or request.is_json
            or "application/json" in request.headers.get("Accept", "")
        )

        service_name = (request.form.get("service_name") or (request.get_json(silent=True) or {}).get("service_name", "")).strip()
        monthly_cost = request.form.get("monthly_cost") if not request.is_json else (request.get_json(silent=True) or {}).get("monthly_cost")
        category = request.form.get("category") if not request.is_json else (request.get_json(silent=True) or {}).get("category")
        start_date = request.form.get("start_date") if not request.is_json else (request.get_json(silent=True) or {}).get("start_date")
        billing_cycle = request.form.get("billing_cycle") if not request.is_json else (request.get_json(silent=True) or {}).get("billing_cycle")
        usage_frequency = request.form.get("usage_frequency") if not request.is_json else (request.get_json(silent=True) or {}).get("usage_frequency")
        usage_hours = request.form.get("usage_hours") if not request.is_json else (request.get_json(silent=True) or {}).get("usage_hours")

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

            if is_ajax:
                return {
                    "success": True,
                    "message": "Subscription added successfully!",
                    "subscription_id": subscription.id,
                    "service_name": subscription.service_name,
                    "redirect_url": url_for("auth.subscriptions"),
                }, 201

            flash("Subscription added successfully!", "success")
            return redirect(url_for("auth.subscriptions"))
        except ValidationException as exc:
            logger.warning("Subscription validation failed: %s", str(exc))
            if is_ajax or request.path.startswith("/api"):
                return {"success": False, "message": str(exc)}, 400
            flash(str(exc), "danger")
            return redirect(url_for("auth.add_subscription"))
        except ValueError:
            if is_ajax or request.path.startswith("/api"):
                return {"success": False, "message": "Please enter valid values in all fields."}, 400
            flash("Please enter valid values in all fields.", "danger")
            return redirect(url_for("auth.add_subscription"))

    return render_template("add_subscription.html")


def update_subscription_usage_controller(id):
    """Handle saving optional usage details after subscription creation."""
    is_ajax = (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.is_json
        or "application/json" in request.headers.get("Accept", "")
    )

    usage_frequency = request.form.get("usage_frequency") or (request.get_json(silent=True) or {}).get("usage_frequency")
    usage_hours = request.form.get("usage_hours") or (request.get_json(silent=True) or {}).get("usage_hours")

    try:
        subscription_service.update_subscription_usage(
            user=current_user,
            subscription_id=id,
            usage_frequency=usage_frequency,
            usage_hours=usage_hours,
        )
        logger.info("Subscription usage updated for id %s", id)
        flash("Usage details saved successfully!", "success")
        if is_ajax:
            return {
                "success": True,
                "message": "Usage details saved successfully!",
                "redirect_url": url_for("auth.subscriptions"),
            }, 200
        return redirect(url_for("auth.subscriptions"))
    except Exception as exc:
        logger.warning("Failed to update subscription usage: %s", str(exc))
        if is_ajax:
            return {"success": False, "message": str(exc)}, 400
        flash("Could not update usage details.", "danger")
        return redirect(url_for("auth.subscriptions"))


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

    summary = subscription_service.get_subscription_summary(current_user)

    return render_template(
        "subscriptions.html",
        subscriptions=paginated_subscriptions,
        search=search,
        category=category,
        sort=sort,
        summary=summary,
        **summary,
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


def spending_analytics():
    """Render the spending analytics view for the current user."""
    data = subscription_service.get_spending_analytics(current_user)
    return render_template("analytics.html", **data)

