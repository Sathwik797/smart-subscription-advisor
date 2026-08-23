"""Controller layer for authentication and account-related requests.

Controllers receive incoming HTTP requests, validate simple input, delegate
business work to services, and return the appropriate Flask response.
"""

from flask import flash, redirect, render_template, request, url_for
from flask_jwt_extended import create_access_token, set_access_cookies, unset_jwt_cookies

from exceptions.exceptions import AuthenticationException, ValidationException
from logging_config.logger import logger
from middleware.auth import current_user
from services.auth_service import auth_service
from validators.auth_validator import auth_validator


def register():
    """Handle user registration requests."""
    if request.method == "POST":
        username = request.form.get("username", "")
        email = request.form.get("email", "")
        mobile_number = request.form.get("mobile_number", "")
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        occupation = request.form.get("occupation", "")
        financial_preference = request.form.get("financial_preference", "")

        form_data = {
            "username": username,
            "email": email,
            "mobile_number": mobile_number,
            "occupation": occupation,
            "financial_preference": financial_preference,
        }

        try:
            auth_validator.validate_registration(
                {
                    "username": username,
                    "email": email,
                    "mobile_number": mobile_number,
                    "password": password,
                    "confirm_password": confirm_password,
                }
            )
            auth_service.register_user(
                username=username,
                email=email,
                mobile_number=mobile_number,
                password=password,
                occupation=occupation,
                financial_preference=financial_preference,
                base_url=request.host_url,
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
            return render_template("register.html", form_data=form_data, general_error=str(exc))

        logger.info("Registration request completed")
        flash("Registration successful! Please check your email to verify your account before logging in.", "success")
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
        except AuthenticationException as exc:
            logger.warning("Login failed: %s", str(exc))
            err_msg = str(exc)
            if "verify your email" in err_msg.lower():
                return render_template(
                    "login.html",
                    email=email,
                    login_error="Please verify your email before logging in.",
                    show_resend=True,
                    unverified_email=email,
                )
            return render_template(
                "login.html",
                email=email,
                login_error="Invalid email or password.",
            )

        logger.info("User login successful")
        flash("Login successful!", "success")
        response = redirect(url_for("auth.dashboard"))
        access_token = create_access_token(identity=str(user.id))
        set_access_cookies(response, access_token)
        return response

    return render_template("login.html")


def verify_email(token):
    """Handle verification URL link clicks."""
    try:
        auth_service.verify_email(token)
        flash("Email verified successfully! Please log in.", "success")
        return render_template("verification_status.html", success=True, message="Your email address has been verified successfully!")
    except ValidationException as exc:
        logger.warning("Verification endpoint failed: %s", str(exc))
        return render_template("verification_status.html", success=False, message=str(exc))


def resend_verification():
    """Handle resend verification email requests."""
    if request.method == "POST":
        email = request.form.get("email", "")
        try:
            auth_validator.validate_email(email)
            auth_service.resend_verification(email, base_url=request.host_url)
        except ValidationException as exc:
            flash(str(exc), "danger")
            return render_template("resend_verification.html", email=email)

        flash("If an unverified account with that email exists, a verification link has been sent.", "success")
        return redirect(url_for("auth.login"))

    email = request.args.get("email", "")
    return render_template("resend_verification.html", email=email)


def forgot_password():
    """Handle forgot password requests."""
    if request.method == "POST":
        email = request.form.get("email", "")
        try:
            auth_validator.validate_forgot_password({"email": email})
            auth_service.request_password_reset(email, base_url=request.host_url)
        except ValidationException as exc:
            flash(str(exc), "danger")
            return render_template("forgot_password.html", email=email)

        flash("If an account with that email exists, a password reset link has been sent.", "success")
        return redirect(url_for("auth.login"))

    return render_template("forgot_password.html")


def reset_password(token):
    """Handle password reset with token."""
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        try:
            auth_validator.validate_reset_password({"password": password, "confirm_password": confirm_password})
            auth_service.reset_password(token, password)
        except ValidationException as exc:
            flash(str(exc), "danger")
            return render_template("reset_password.html", token=token, reset_error=str(exc))

        flash("Password reset successful! Please log in with your new password.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", token=token)


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
    logger.info("User logout completed")
    flash("Logged out successfully.", "success")
    response = redirect(url_for("auth.login"))
    unset_jwt_cookies(response)
    return response
