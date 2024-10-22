"""Define fixtures accessible to all tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fakeredis import FakeRedis

from .helloworld import create_app

if TYPE_CHECKING:
    from flask import Flask
    from flask.testing import FlaskClient, FlaskCliRunner


@pytest.fixture
def redis_client() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def app() -> Flask:
    app = create_app()

    app.config.update(
        {
            "TESTING": True,
        },
    )

    return app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()


@pytest.fixture
def runner(app: Flask) -> FlaskCliRunner:
    return app.test_cli_runner()
