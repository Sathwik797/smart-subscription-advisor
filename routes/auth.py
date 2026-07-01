from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import query
from models import subscription
from models.user import User
from database.db import db
from flask_login import login_user
from flask_login import login_required
from flask_login import logout_user
from flask_login import current_user
from models.subscription import Subscription
from database.db import db
from datetime import datetime
from sqlalchemy import func
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import csv
from io import StringIO
from flask import Response
from werkzeug.security import generate_password_hash, check_password_hash
from utils.recommendation_engine import (
    calculate_priority,
    get_recommendation
)
from utils.insights_engine import generate_insight
from utils.ai_insights import generate_subscription_insight
import random


auth = Blueprint('auth', __name__)

def generate_username_suggestions(username):
    suggestions = []
    tried = set()

    patterns = [
        lambda u: f"{u}_{random.randint(10,99)}",
        lambda u: f"{u}{random.randint(100,999)}",
        lambda u: f"{u}_dev",
        lambda u: f"{u}_pro",
        lambda u: f"{u}_ai",
        lambda u: f"{u}x",
        lambda u: f"{u}_{random.choice(['official', 'user', 'app'])}"
    ]

    while len(suggestions) < 3:

        candidate = random.choice(patterns)(username)

        if candidate in tried:
            continue

        tried.add(candidate)

        exists = User.query.filter_by(username=candidate).first()

        if not exists:
            suggestions.append(candidate)

    return suggestions

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        occupation = request.form["occupation"]
        financial_preference = request.form["financial_preference"]
        
        form_data = {
            "username": username,
            "email": email,
            "occupation": occupation,
            "financial_preference": financial_preference
        }
        
        # Check if username already exists
        existing_username = User.query.filter_by(username=username).first()

        if existing_username:

            suggestions = generate_username_suggestions(username)

            return render_template(
                "register.html",
                form_data=form_data,
                username_error=f'Username "{username}" is already taken.',
                suggestions=suggestions
            )
            
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("An account with this email already exists.", "danger")
            return redirect(url_for("auth.register"))
        
        user = User(
            username=username,
            email=email,
            password=hashed_password,
            occupation=occupation,
            financial_preference=financial_preference
        )
        
        db.session.add(user)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template('register.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for("auth.dashboard"))

        return render_template(
            "login.html",
            email=email,
            login_error="Invalid email or password."
        )

    return render_template('login.html')

@auth.route('/add-subscription', methods=['GET', 'POST'])
@login_required
def add_subscription():

    if request.method == "POST":

        # ----------------------------
        # Validate required fields
        # ----------------------------
        service_name = request.form.get("service_name", "").strip()
        monthly_cost = request.form.get("monthly_cost")
        category = request.form.get("category")
        start_date = request.form.get("start_date")
        billing_cycle = request.form.get("billing_cycle")
        usage_frequency = request.form.get("usage_frequency")
        usage_hours = request.form.get("usage_hours")

        if (
            not service_name or
            not monthly_cost or
            not category or
            not start_date or
            not billing_cycle or
            not usage_frequency or
            not usage_hours
        ):
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for("auth.add_subscription"))

        try:
            # ----------------------------
            # Convert values
            # ----------------------------
            monthly_cost = float(monthly_cost)

            start_date = datetime.strptime(
                start_date,
                "%Y-%m-%d"
            ).date()

            usage_hours = float(usage_hours)

            # ----------------------------
            # Calculate renewal date
            # ----------------------------
            if billing_cycle == "Monthly":
                renewal_date = start_date + relativedelta(months=1)
            else:
                renewal_date = start_date + relativedelta(years=1)

            # ----------------------------
            # Calculate Priority
            # ----------------------------
            priority_data = calculate_priority(
                occupation=current_user.occupation,
                financial_preference=current_user.financial_preference,
                category=category,
                monthly_cost=monthly_cost,
                usage_frequency=usage_frequency,
                usage_hours=usage_hours,
            )

            priority = priority_data["priority"]

            # ----------------------------
            # Create Subscription
            # ----------------------------
            subscription = Subscription(
                service_name=service_name,
                monthly_cost=monthly_cost,
                category=category,
                start_date=start_date,
                renewal_date=renewal_date,
                billing_cycle=billing_cycle,
                usage_frequency=usage_frequency,
                usage_hours=usage_hours,
                priority=priority,
                user_id=current_user.id
            )

            db.session.add(subscription)
            db.session.commit()

            flash("Subscription added successfully!", "success")
            return redirect(url_for("auth.subscriptions"))

        except ValueError:
            flash("Please enter valid values in all fields.", "danger")
            return redirect(url_for("auth.add_subscription"))

    return render_template("add_subscription.html")


@auth.route('/dashboard')
@login_required
def dashboard():

    # Get all subscriptions of current user
    subscriptions = Subscription.query.filter_by(
        user_id=current_user.id
    ).all()

    # Summary calculations
    total_monthly = sum(sub.monthly_cost for sub in subscriptions)
    total_yearly = total_monthly * 12
    total_subscriptions = len(subscriptions)

    # Upcoming renewals
    today = date.today()
    next_week = today + timedelta(days=7)

    upcoming_renewals = Subscription.query.filter(
        Subscription.user_id == current_user.id,
        Subscription.renewal_date >= today,
        Subscription.renewal_date <= next_week
    ).all()

    # -----------------------------
    # Category Pie Chart Data
    # -----------------------------
    category_data = {}

    for sub in subscriptions:
        category_data[sub.category] = (
            category_data.get(sub.category, 0)
            + sub.monthly_cost
        )

    # -----------------------------
    # Subscription Bar Chart Data
    # -----------------------------
    subscription_labels = []
    subscription_values = []

    for sub in subscriptions:
        subscription_labels.append(sub.service_name)
        subscription_values.append(sub.monthly_cost)

    # -----------------------------
    # Smart Recommendations
    # -----------------------------
    recommendations = []

    for sub in subscriptions:
        insight = generate_insight(
            subscription=sub,
            financial_preference=current_user.financial_preference
        )

        recommendations.append(insight)

    # Keep only the first 3 insights
    recommendations = sorted(
    recommendations,
    key=lambda x: x["score"],
    reverse=True
    )[:3]
    # -----------------------------
    # Health Score
    # -----------------------------
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

    # -----------------------------
    # Potential Savings
    # -----------------------------
    potential_monthly_savings = 0

    for sub in subscriptions:

        if sub.priority == "Low":
            potential_monthly_savings += sub.monthly_cost

        elif (
            current_user.financial_preference == "Money Saver"
            and sub.usage_frequency == "Rarely"
        ):
            potential_monthly_savings += sub.monthly_cost

    potential_yearly_savings = potential_monthly_savings * 12

    # -----------------------------
    # Render Template
    # -----------------------------
    return render_template(
        "dashboard.html",
        total_monthly=total_monthly,
        total_yearly=total_yearly,
        total_subscriptions=total_subscriptions,
        upcoming_renewals=upcoming_renewals,
        category_labels=list(category_data.keys()),
        category_values=list(category_data.values()),
        subscription_labels=subscription_labels,
        subscription_values=subscription_values,
        recommendations=recommendations,
        health_score=health_score,
        potential_monthly_savings=potential_monthly_savings,
        potential_yearly_savings=potential_yearly_savings
    )

@auth.route("/profile")
@login_required
def profile():

    subscriptions = Subscription.query.filter_by(
        user_id=current_user.id
    ).all()

    total_subscriptions = len(subscriptions)

    total_monthly = sum(
        sub.monthly_cost for sub in subscriptions
    )

    total_yearly = total_monthly * 12

    return render_template(
        "profile.html",
        total_subscriptions=total_subscriptions,
        total_monthly=total_monthly,
        total_yearly=total_yearly
    )

@auth.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        occupation = request.form.get("occupation")
        financial_preference = request.form.get("financial_preference")

        if not username:
            flash("Username cannot be empty.", "danger")
            return redirect(url_for("auth.edit_profile"))

        current_user.username = username
        current_user.occupation = occupation
        current_user.financial_preference = financial_preference

        db.session.commit()

        flash("Profile updated successfully!", "success")

        return redirect(url_for("auth.profile"))

    return render_template("edit_profile.html")

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    
    flash("Logged out successfully.", "success")
    
    return redirect(url_for("auth.login"))

@auth.route('/subscriptions')
@login_required
def subscriptions():

    search = request.args.get("search", "")
    category = request.args.get("category", "")
    sort = request.args.get("sort", "")

    query = Subscription.query.filter_by(user_id=current_user.id)

    if search:
        query = query.filter(
            Subscription.service_name.ilike(f"%{search}%")
        )

    if category:
        query = query.filter_by(category=category)

    if sort == "renewal":
        query = query.order_by(Subscription.renewal_date.asc())
    elif sort == "cost":
        query = query.order_by(Subscription.monthly_cost.desc())

    page = request.args.get("page", 1, type=int)

    subscriptions = query.paginate(
        page=page,
        per_page=10,
        error_out=False
    )
    
    
    return render_template(
        "subscriptions.html",
        subscriptions=subscriptions,
        search=search,
        category=category,
        sort=sort
    )

@auth.route('/export-csv')
@login_required
def export_csv():

    subscriptions = Subscription.query.filter_by(
        user_id=current_user.id
    ).all()

    output = StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        "Service Name",
        "Monthly Cost",
        "Category",
        "Start Date",
        "Renewal Date"
    ])

    # Data rows
    for sub in subscriptions:
        writer.writerow([
            sub.service_name,
            sub.monthly_cost,
            sub.category,
            sub.start_date,
            sub.renewal_date
        ])

    output.seek(0)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=subscriptions.csv"
        }
    )

@auth.route('/edit-subscription/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_subscription(id):

    subscription = Subscription.query.get_or_404(id)

    if request.method == "POST":

        subscription.service_name = request.form["service_name"]

        subscription.monthly_cost = float(request.form["monthly_cost"])

        subscription.category = request.form["category"]

        subscription.start_date = datetime.strptime(
            request.form["start_date"],
            "%Y-%m-%d"
        ).date()

        subscription.billing_cycle = request.form["billing_cycle"]

        # Calculate renewal date
        if subscription.billing_cycle == "Monthly":
            subscription.renewal_date = subscription.start_date + relativedelta(months=1)
        else:
            subscription.renewal_date = subscription.start_date + relativedelta(years=1)

        subscription.usage_frequency = request.form["usage_frequency"]

        subscription.usage_hours = float(request.form["usage_hours"])

        # ⭐ Automatically calculate priority
        priority_data = calculate_priority(
            occupation=current_user.occupation,
            financial_preference=current_user.financial_preference,
            category=subscription.category,
            monthly_cost=subscription.monthly_cost,
            usage_frequency=subscription.usage_frequency,
            usage_hours=subscription.usage_hours
        )

        subscription.priority = priority_data["priority"]


        db.session.commit()

        flash("Subscription updated successfully!", "success")

        return redirect(url_for("auth.subscriptions"))
    
    # Calculate Smart Subscription Insights
    priority_data = calculate_priority(
        occupation=current_user.occupation,
        financial_preference=current_user.financial_preference,
        category=subscription.category,
        monthly_cost=subscription.monthly_cost,
        usage_frequency=subscription.usage_frequency,
        usage_hours=subscription.usage_hours
    )

    return render_template(
        "edit_subscription.html",
        subscription=subscription,
        insight=priority_data,
    )

@auth.route('/delete-subscription/<int:id>')
@login_required
def delete_subscription(id):

    subscription = Subscription.query.get_or_404(id)

    db.session.delete(subscription)
    db.session.commit()
    flash("Subscription deleted successfully!", "success")
    
    return redirect(url_for('auth.subscriptions'))
