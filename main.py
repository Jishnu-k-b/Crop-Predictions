import bcrypt
import re
import numpy as np
import pandas as pd
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import timedelta, datetime
from sqlalchemy.exc import IntegrityError
from flask import make_response
from functools import wraps
from flask import (
    Flask,
    request,
    render_template,
    redirect,
    session,
    url_for,
)

from prediction_model import xgb_model, rf_model, gb_model, X, ferti, model

app = Flask(__name__, static_url_path="/static")
CORS(app)

app.secret_key = "secret_key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=15)


db = SQLAlchemy(app)


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


with app.app_context():
    db.create_all()


def nocache(view):
    @wraps(view)
    def no_cache(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "-1"
        return response

    return no_cache


@app.route("/")
@nocache
def index():
    return render_template("index.html")


# index page
@app.route("/dashboard")
@nocache
def dashboard():
    try:
        if not session["email"]:
            return redirect(url_for("login"))
    except KeyError:
        return redirect(url_for("login"))
    user = User.query.filter_by(email=session["email"]).first()
    prediction_history = PredictionHistory.query.filter_by(user_id=user.id).all()

    # Prepare prediction history data to pass to the template
    history_data = []
    for prediction in prediction_history:
        history_data.append(
            {
                "prediction_type": prediction.prediction_type,
                "result": prediction.result,
                "timestamp": prediction.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return render_template(
        "dashboard.html",
        user=user,
        prediction_history=history_data,
    )


@app.route("/register", methods=["GET", "POST"])
@nocache
def register():
    try:
        if request.method == "POST":
            first_name = request.form["first_name"]
            last_name = request.form["last_name"]
            phone_number = request.form["phone_number"]
            email = request.form["email"]
            password = request.form["password"]
            confirm_password = request.form["confirm_password"]

            # Password validation
            if not (8 <= len(password) <= 100):
                return render_template(
                    "sign-in-or-up.html",
                    reg_error="Password must contain minimum 8 Characters.",
                )
            elif not re.search(r"[A-Z]", password):
                return render_template(
                    "sign-in-or-up.html",
                    reg_error="Password must contain at least one uppercase letter.",
                )
            elif not re.search(r"[a-z]", password):
                return render_template(
                    "sign-in-or-up.html",
                    reg_error="Password must contain at least one lowercase letter.",
                )
            elif not re.search(r"\d", password):
                return render_template(
                    "sign-in-or-up.html",
                    reg_error="Password must contain at least one digit.",
                )
            elif not re.search(r"[!@#$%^&*]", password):
                return render_template(
                    "sign-in-or-up.html",
                    reg_error="Password must contain at least one special character.",
                )

            if password != confirm_password:
                return render_template(
                    "sign-in-or-up.html", reg_error="Passwords do not match."
                )

            new_user = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                password=password,
            )
            db.session.add(new_user)
            db.session.commit()
            return redirect("login")
    except IntegrityError:
        return render_template(
            "sign-in-or-up.html",
            reg_error="Email/Phone number already exists",
        )
    return render_template("sign-in-or-up.html")


@app.route("/login", methods=["GET", "POST"])
@nocache
def login():
    if "email" in session:
        return redirect(url_for("index"))
    if request.method == "POST":
        email = request.form["user_email"]
        password = request.form["user_password"]

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session["first_name"] = user.first_name
            session["last_name"] = user.last_name
            session["email"] = user.email
            return render_template("index.html")
        else:
            return render_template(
                "sign-in-or-up.html",
                login_error="Check your email and password.",
            )
    return render_template("sign-in-or-up.html")


@app.route("/logout")
@nocache
def logout():
    session.pop("email", None)
    return redirect("/login")


@app.route("/predict")
@nocache
def predict():
    try:
        if not session["email"]:
            return redirect(url_for("login"))
    except KeyError:
        return redirect(url_for("login"))
    return render_template("predict.html")


@app.route("/predict_crop", methods=["POST", "GET"])
@nocache
def predict_crop():
    try:
        if not session["email"]:
            return redirect(url_for("login"))
    except KeyError:
        return redirect(url_for("login"))
    if request.method == "POST":
        state = request.form["state"]
        season = request.form["season"]
        crop = request.form["crop"]
        area = float(request.form["area"])

        def preprocess_input(state, season, crop, area):
            input_data = pd.DataFrame(
                {
                    "State": [state],
                    "Season": [season],
                    "Crop": [crop],
                    "Area": [area],
                }
            )
            input_data = pd.get_dummies(
                input_data,
                columns=["State", "Season", "Crop"],
            )
            input_data = input_data.reindex(columns=X.columns, fill_value=0)
            return input_data

        # Function to predict yield for a new combination of State, Season, Crop,
        # and Area
        def predict_yield_new(
            state,
            season,
            crop,
            area,
            rf_model,
            gb_model,
            xgb_model,
        ):
            input_data = preprocess_input(state, season, crop, area)
            rf_yield = rf_model.predict(input_data)
            gb_yield = gb_model.predict(input_data)
            xgb_yield = xgb_model.predict(input_data)
            average_yield = np.mean([rf_yield, gb_yield, xgb_yield])
            return average_yield

        predicted_yield = predict_yield_new(
            state, season, crop, area, rf_model, gb_model, xgb_model
        )
        user = User.query.filter_by(email=session["email"]).first()
        prediction = PredictionHistory(
            user_id=user.id,
            prediction_type="Crop yield prediction",
            result=str(predicted_yield),
        )
        db.session.add(prediction)
        db.session.commit()
        return render_template(
            "result.html",
            predicted_yield=predicted_yield,
        )
    return render_template("predict_crop.html")


@app.route("/predict_ferti")
@nocache
def predict_ferti():
    return render_template("predict_fert.html")


@app.route("/predict_fert", methods=["POST"])
@nocache
def predict_fert():
    try:
        if not session["email"]:
            return redirect(url_for("login"))
    except KeyError:
        return redirect(url_for("login"))
    temp = request.form.get("temp")
    humi = request.form.get("humid")
    mois = request.form.get("mois")
    soil = request.form.get("soil")
    crop = request.form.get("crop")
    nitro = request.form.get("nitro")
    pota = request.form.get("pota")
    phosp = request.form.get("phos")
    input = [
        int(temp),
        int(humi),
        int(mois),
        int(soil),
        int(crop),
        int(nitro),
        int(pota),
        int(phosp),
    ]

    result = ferti.classes_[model.predict([input])]
    result_string = ", ".join(map(str, result))
    user = User.query.filter_by(email=session["email"]).first()
    prediction = PredictionHistory(
        user_id=user.id,
        prediction_type="Fertilizer prediction",
        result=result_string,
    )
    db.session.add(prediction)
    db.session.commit()

    return render_template(
        "result.html",
        x=("Predicted Fertilizer is {}".format(result)),
    )


if __name__ == "__main__":
    app.run(debug=True)
