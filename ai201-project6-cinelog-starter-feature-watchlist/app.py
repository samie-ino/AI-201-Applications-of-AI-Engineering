"""app.py — CineLog Flask application factory"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

db = SQLAlchemy()


def create_app(config=None):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///cinelog.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

    if config:
        app.config.update(config)

    db.init_app(app)

    from routes.films import films_bp
    from routes.collection import collection_bp
    from routes.watchlist.watchlist import watchlist_bp

    app.register_blueprint(films_bp, url_prefix="/films")
    app.register_blueprint(collection_bp, url_prefix="/collection")
    app.register_blueprint(watchlist_bp, url_prefix="/watchlist")

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    # Register this module under its import name too. Without this, code that
    # does `from app import db` (models.py, etc.) re-imports this file as a
    # second module named "app", creating a second SQLAlchemy() instance that
    # never gets init_app()'d — every DB route then 500s with "not registered
    # with this 'SQLAlchemy' instance".
    import sys
    sys.modules.setdefault("app", sys.modules["__main__"])

    app = create_app()
    app.run(debug=True)
