import os
import re
import pytz
import stripe
from datetime import timezone, datetime
import numpy as np
import pandas as pd

from sqlalchemy.exc import IntegrityError
from flask import make_response
from functools import wraps
from flask import (
    request,
    render_template,
    redirect,
    session,
    url_for,
    jsonify,
    flash,
)

from .config import Config

from .prediction_model import xgb_model, rf_model, gb_model, X, ferti, model

from .models import db, User, PredictionHistory, Payment

# email

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


stripe.api_key = Config.STRIPE_SECRET_KEY


def register_routes(app):
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

                if not (8 <= len(password) <= 100):
                    flash("Password must contain minimum 8 Characters.")
                    return redirect(url_for("login"))
                elif not re.search(r"[A-Z]", password):
                    flash("Password must contain at least one uppercase letter.")
                    return redirect(url_for("login"))
                elif not re.search(r"[a-z]", password):
                    flash("Password must contain at least one lowercase letter.")
                    return redirect(url_for("login"))
                elif not re.search(r"\d", password):
                    flash("Password must contain at least one digit.")
                    return redirect(url_for("login"))
                elif not re.search(r"[!@#$%^&*]", password):
                    flash("Password must contain at least one special character.")
                    return redirect(url_for("login"))
                elif password != confirm_password:
                    flash("Passwords do not match.")
                    return redirect(url_for("login"))

                new_user = User(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    phone_number=phone_number,
                    password=password,
                )
                db.session.add(new_user)
                db.session.commit()
                flash("Registration successful, please login to continue.")
                return redirect("login")
        except IntegrityError:
            flash("Email/Phone number already exists!")
            return render_template("signin.html")
        return render_template("signin.html")

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
                session.permanent = True
                flash("Login Success!")
                return redirect(url_for("index"))
            else:
                flash("Check your email and password.")
                return render_template("signin.html")
        return render_template("signin.html")

    @app.route("/logout")
    @nocache
    def logout():
        session.pop("email", None)
        session.clear()
        flash("You have been logged out.")
        return redirect(url_for("login"))

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

            def predict_yield_new(
                state, season, crop, area, rf_model, gb_model, xgb_model
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

    @app.route("/products")
    @nocache
    def products():
        try:
            if not session["email"]:
                return redirect(url_for("login"))
        except KeyError:
            return redirect(url_for("login"))
        return render_template("products.html")

    @app.route("/detail", methods=["GET", "POST"])
    @nocache
    def detail():
        try:
            if not session["email"]:
                return redirect(url_for("login"))
        except KeyError:
            return redirect(url_for("login"))
        message = request.args.get("message")
        if message:
            return render_template("detail.html", message=message)
        return render_template("detail.html")

    @app.route("/checkout", methods=["GET", "POST"])
    @nocache
    def checkout():
        if "email" not in session:
            return redirect(url_for("login"))
        else:
            customer_email = session["email"]

        price_id = request.form.get("stripe_id")
        quantity = request.form.get("quantity")

        try:
            # Create a Stripe Checkout session
            checkout_session = stripe.checkout.Session.create(
                customer_email=customer_email,
                line_items=[
                    {
                        "price": price_id,
                        "quantity": quantity,
                    }
                ],
                mode="payment",
                billing_address_collection="required",
                success_url=f"http://localhost:5000/payment/success?session_id={{CHECKOUT_SESSION_ID}}&email={customer_email}",
                cancel_url="http://localhost:5000/payment/failure?session_id={{CHECKOUT_SESSION_ID}}",
            )
            return redirect(checkout_session.url, code=303)
        except Exception as e:
            return str(e), 500

    @app.route("/payment/success", methods=["GET"])
    @nocache
    def payment_success():
        email = request.args.get("email")
        session_id = request.args.get("session_id")

        if not session_id or not email:
            flash("Payment failed, missing session_id or email.")
            return redirect(url_for("login"))

        checkout_session = stripe.checkout.Session.retrieve(session_id)

        status = checkout_session.get("payment_status")
        address = checkout_session.customer_details.address
        created_timestamp = checkout_session.created
        total_amount = checkout_session.amount_total / 100

        line_items = stripe.checkout.Session.list_line_items(session_id)
        for item in line_items.data:
            item_name = item.description
            quantity = item.quantity

        # Convert the timestamp to UTC
        payment_time_utc = datetime.fromtimestamp(created_timestamp, tz=timezone.utc)

        # Convert UTC to IST
        ist = pytz.timezone("Asia/Kolkata")
        payment_time = payment_time_utc.astimezone(ist)

        # mail for the recipient
        message = Mail(
            from_email="crop.prjct.test.123@gmail.com",
            to_emails=email,
            subject=f"Your payment of Rs.{total_amount} for {item_name} is successful",
            html_content=f"Order details:<br><ul> <li>Product: {item_name}</li> <li> Quantity: {quantity}</li> <li>Total amount paid: {total_amount}</li><ul> <br>Your order is now being processed, and we will notify you once it has been shipped. If you have any questions or need further assistance, feel free to contact us.",
        )
        try:
            sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
            response = sg.send(message)
            print(response.status_code)
        except Exception as e:
            print(e.message)

        user = User.query.filter_by(email=email).first()
        current_user_id = user.id

        if not current_user_id:
            return jsonify({"error": "User not found"}), 404

        billing_address = f"{address['line1']}, {address['city']}, {address['state']}, {address['postal_code']}, {address['country']}"
        existing_payment = Payment.query.filter_by(
            user_id=current_user_id, timestamp=payment_time, payment_status=status
        ).first()
        if not existing_payment:
            payment = Payment(
                user_id=current_user_id,
                payment_status=status,
                billing_address=billing_address,
                timestamp=payment_time,
                product_name=item_name,
                quantity=quantity,
                total_amount=total_amount,
            )
            db.session.add(payment)
            db.session.commit()

        flash(
            "Payment Successful, but something went wrong, please login again. Check your email for payment details!"
        )
        session["email"] = email
        return redirect(url_for("products"))

    @app.route("/payment/history")
    @nocache
    def payment_history():
        try:
            if not session["email"]:
                return redirect(url_for("login"))
        except KeyError:
            return redirect(url_for("login"))

        user = User.query.filter_by(email=session["email"]).first()
        payment_history = Payment.query.filter_by(user_id=user.id).all()

        payment_data = []
        for payment in payment_history:
            payment_data.append(
                {
                    "payment_status": payment.payment_status,
                    "billing_address": payment.billing_address,
                    "timestamp": payment.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "product_name": payment.product_name,
                    "quantity": payment.quantity,
                    "total_amount": payment.total_amount,
                }
            )
        return render_template("payment-history.html", payment_history=payment_data)

    @app.route("/payment/failure", methods=["GET"])
    @nocache
    def payment_failed():
        flash("False")
        return redirect(url_for("products"))
