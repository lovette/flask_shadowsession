"""Simple Flask app for testing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask import Flask, flash

from flask_shadowsession import ShadowSessionInterface

if TYPE_CHECKING:
    from collections.abc import Mapping

# Based on:
# https://flask.palletsprojects.com/en/3.0.x/testing/
# https://flask.palletsprojects.com/en/3.0.x/tutorial/factory/

# This key is used by SecureCookieSessionInterface:get_signing_serializer to sign cookies
APP_SECRET_KEY = "blah"  # noqa: S105


def create_app(test_config: Mapping | None = None) -> Flask:
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        SECRET_KEY=APP_SECRET_KEY,
    )

    # app.session will be an instance of this interface
    app.session_interface = ShadowSessionInterface()

    @app.route("/hello")
    def _hello() -> str:
        return "Hello, World!"

    @app.route("/flash")
    def _flash() -> str:
        flash("This is a message")
        return "Consider yourself flashed"

    return app
