from decimal import Decimal
from database.db import db


class Subscription(db.Model):
    """Subscription model representing a user's tracked subscription.

    IMPORTANT SEMANTIC NOTE ON `monthly_cost`:
    This column stores the user-entered subscription amount for its selected `billing_cycle`.
    For example:
      - If billing_cycle is 'Monthly', monthly_cost stores the monthly charge (e.g. 499.00).
      - If billing_cycle is 'Yearly', monthly_cost stores the yearly charge (e.g. 1499.00).
    The column name `monthly_cost` is preserved for backward compatibility across existing
    database tables, migrations, and API contracts.
    To retrieve authoritative converted values, always use:
      - `subscription.monthly_equivalent` -> Decimal monthly cost equivalent
      - `subscription.yearly_equivalent`  -> Decimal yearly cost equivalent
    """
    id = db.Column(db.Integer, primary_key=True)

    service_name = db.Column(db.String(100), nullable=False)

    monthly_cost = db.Column(db.Numeric(10, 2), nullable=False)

    category = db.Column(db.String(50), nullable=False)

    start_date = db.Column(db.Date, nullable=False)

    renewal_date = db.Column(db.Date, nullable=False)
    
    billing_cycle = db.Column(
        db.String(20),
        nullable=False
    )

    # NEW FIELDS
    usage_frequency = db.Column(db.String(20), nullable=True)
    usage_hours = db.Column(db.Float, nullable=True)
    priority = db.Column(db.String(10), nullable=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )

    @property
    def cost_decimal(self) -> Decimal:
        """Return the stored subscription amount as a precise Decimal."""
        if self.monthly_cost is None:
            return Decimal("0.00")
        return Decimal(str(self.monthly_cost))

    @property
    def monthly_equivalent(self) -> Decimal:
        """
        Authoritative monthly cost equivalent based on billing cycle.

        Semantics:
        - Monthly: stored amount is monthly -> monthly_equivalent = stored amount
        - Yearly: stored amount is yearly -> monthly_equivalent = stored amount / 12
        - Quarterly: stored amount is quarterly -> monthly_equivalent = stored amount / 3
        - Weekly: stored amount is weekly -> monthly_equivalent = (stored amount * 52) / 12
        """
        cost = self.cost_decimal
        cycle = (self.billing_cycle or "Monthly").strip().capitalize()
        if cycle == "Yearly":
            return cost / Decimal("12")
        elif cycle == "Quarterly":
            return cost / Decimal("3")
        elif cycle == "Weekly":
            return (cost * Decimal("52")) / Decimal("12")
        return cost

    @property
    def yearly_equivalent(self) -> Decimal:
        """
        Authoritative yearly cost equivalent based on billing cycle.

        Semantics:
        - Monthly: stored amount is monthly -> yearly_equivalent = stored amount * 12
        - Yearly: stored amount is yearly -> yearly_equivalent = stored amount
        - Quarterly: stored amount is quarterly -> yearly_equivalent = stored amount * 4
        - Weekly: stored amount is weekly -> yearly_equivalent = stored amount * 52
        """
        cost = self.cost_decimal
        cycle = (self.billing_cycle or "Monthly").strip().capitalize()
        if cycle == "Yearly":
            return cost
        elif cycle == "Quarterly":
            return cost * Decimal("4")
        elif cycle == "Weekly":
            return cost * Decimal("52")
        return cost * Decimal("12")