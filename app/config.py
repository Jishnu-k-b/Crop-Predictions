import os
import redis
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file


class Config:
    SECRET_KEY = os.getenv(
        "SECRET_KEY", "default_secret_key"
    )  # Default for development

    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///database.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Suppress warning messages

    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=15)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_TYPE = "redis"  # Use Redis for session storage
    SESSION_REDIS = redis.from_url("redis://localhost:6379")
    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True

    # Stripe configuration
    STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
