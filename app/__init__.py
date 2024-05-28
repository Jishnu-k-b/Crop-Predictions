import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
from dotenv import load_dotenv

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__, static_url_path="/static")

    # Load environment variables from .env file
    load_dotenv()

    # Load configuration from Config class
    app.secret_key = os.getenv("SECRET_KEY")
    app.config.from_object("app.config.Config")

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)

    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()

    # Register routes
    from .routes import register_routes

    register_routes(app)

    return app
