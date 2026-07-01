from database.db import db

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    service_name = db.Column(db.String(100), nullable=False)

    monthly_cost = db.Column(db.Float, nullable=False)

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