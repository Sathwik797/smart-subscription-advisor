"""Controller layer for authentication and account-related requests.

Controllers receive incoming HTTP requests, validate simple input, delegate
business work to services, and return the appropriate Flask response.
"""

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from exceptions.exceptions import AuthenticationException, ValidationException
from logging_config.logger import logger
from services.auth_service import auth_service
from validators.auth_validator import auth_validator


def register():
    """Handle user registration requests."""
    if request.method == "POST":
        username = request.form.get("username", "")
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        occupation = request.form.get("occupation", "")
        financial_preference = request.form.get("financial_preference", "")

        form_data = {
            "username": username,
            "email": email,
            "occupation": occupation,
            "financial_preference": financial_preference,
        }

        try:
            auth_validator.validate_registration(
                {
                    "username": username,
                    "email": email,
                    "password": password,
                    "confirm_password": request.form.get("confirm_password"),
                }
            )
            auth_service.register_user(
                username=username,
                email=email,
                password=password,
                occupation=occupation,
                financial_preference=financial_preference,
            )
        except ValidationException as exc:
            logger.warning("Registration failed: %s", str(exc))
            if request.path.startswith("/api") or request.is_json:
                raise
            if "Username" in str(exc):
                return render_template(
                    "register.html",
                    form_data=form_data,
                    username_error=str(exc),
                    suggestions=auth_service.generate_username_suggestions(username),
                )
            flash(str(exc), "danger")
            return redirect(url_for("auth.register"))

        logger.info("Registration completed successfully")
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


def login():
    """Handle user login requests."""
    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")

        try:
            auth_validator.validate_login({"email": email, "password": password})
            user = auth_service.authenticate_user(email, password)
        except AuthenticationException:
            logger.warning("Login failed")
            return render_template(
                "login.html",
                email=email,
                login_error="Invalid email or password.",
            )

        login_user(user)
        logger.info("User login successful")
        flash("Login successful!", "success")
        return redirect(url_for("auth.dashboard"))

    return render_template("login.html")


def dashboard():
    """Render the dashboard view for the current user."""
    data = auth_service.get_dashboard_data(current_user)
    return render_template(
        "dashboard.html",
        total_monthly=data["total_monthly"],
        total_yearly=data["total_yearly"],
        total_subscriptions=data["total_subscriptions"],
        upcoming_renewals=data["upcoming_renewals"],
        category_labels=data["category_labels"],
        category_values=data["category_values"],
        subscription_labels=data["subscription_labels"],
        subscription_values=data["subscription_values"],
        recommendations=data["recommendations"],
        health_score=data["health_score"],
        potential_monthly_savings=data["potential_monthly_savings"],
        potential_yearly_savings=data["potential_yearly_savings"],
    )


def profile():
    """Render the profile summary page."""
    data = auth_service.get_profile_summary(current_user)
    return render_template(
        "profile.html",
        total_subscriptions=data["total_subscriptions"],
        total_monthly=data["total_monthly"],
        total_yearly=data["total_yearly"],
    )


def edit_profile():
    """Handle profile updates."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        occupation = request.form.get("occupation")
        financial_preference = request.form.get("financial_preference")

        if not username:
            flash("Username cannot be empty.", "danger")
            return redirect(url_for("auth.edit_profile"))

        auth_service.update_profile(
            user=current_user,
            username=username,
            occupation=occupation,
            financial_preference=financial_preference,
        )

        flash("Profile updated successfully!", "success")
        return redirect(url_for("auth.profile"))

    return render_template("edit_profile.html")


def logout():
    """Handle user logout requests."""
    logout_user()
    logger.info("User logout completed")
    flash("Logged out successfully.", "success")
    return redirect(url_for("auth.login"))


