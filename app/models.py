import bcrypt
from . import db
from datetime import datetime


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    phone_number = db.Column(db.String(10), unique=True)

    def __init__(
        self,
        email,
        password,
        first_name,
        last_name,
        phone_number,
    ):
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.phone_number = phone_number
        self.password = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    def check_password(self, password):
        return bcrypt.checkpw(
            password.encode("utf-8"),
            self.password.encode("utf-8"),
        )


class PredictionHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    prediction_type = db.Column(db.String(100), nullable=False)
    result = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now)

    def __init__(self, user_id, prediction_type, result):
        self.user_id = user_id
        self.prediction_type = prediction_type
        self.result = result


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    billing_address = db.Column(db.String(200), nullable=True)
    product_name = db.Column(db.String(50), nullable=False)
    total_amount = db.Column(db.Float, nullable=True)
    payment_status = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now)
    quantity = db.Column(db.Integer, nullable=True)

    user = db.relationship("User", backref=db.backref("payments", lazy=True))
