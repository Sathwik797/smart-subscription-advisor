"""Routing layer for subscription-related URLs.

Routes stay thin and delegate request handling to controller functions while
keeping the existing URL structure intact.
"""

from flask_login import login_required

from controllers.subscription_controller import (
    add_subscription as add_subscription_controller,
    delete_subscription as delete_subscription_controller,
    edit_subscription as edit_subscription_controller,
    export_csv as export_csv_controller,
    subscriptions as subscriptions_controller,
)
from routes.auth import auth


@auth.route("/add-subscription", methods=["GET", "POST"])
@login_required
def add_subscription():
    return add_subscription_controller()


@auth.route("/subscriptions")
@login_required
def subscriptions():
    return subscriptions_controller()


@auth.route("/export-csv")
@login_required
def export_csv():
    return export_csv_controller()


@auth.route("/edit-subscription/<int:id>", methods=["GET", "POST"])
@login_required
def edit_subscription(id):
    return edit_subscription_controller(id)


@auth.route("/delete-subscription/<int:id>")
@login_required
def delete_subscription(id):
    return delete_subscription_controller(id)
