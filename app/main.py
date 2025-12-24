# app/main.py
from __future__ import annotations

from flask import Flask

from app.database import engine
from app.models import Base
from app.routes.public import public_bp
from app.routes.admin import admin_bp
import os

def init_db():
    Base.metadata.create_all(bind=engine)


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static"
    )
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB
    app.config["SECRET_KEY"] = "dev-secret-change-me"

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)

    if os.environ.get("AUTO_CREATE_TABLES") == "1":
        init_db()

    return app


if __name__ == "__main__":
    init_db()
    app = create_app()
    app.run(debug=True)
