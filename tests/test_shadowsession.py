"""ShadowSession tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from flask_shadowsession import ShadowSession, ShadowSessionInterface

if TYPE_CHECKING:
    from fakeredis import FakeRedis
    from flask.testing import FlaskClient


def test_session_redis_none(client: FlaskClient) -> None:
    with pytest.raises(ValueError, match="redis instance must be set prior"), client.session_transaction() as session:
        session["value"] = 42


def test_session_redis_isinstance(client: FlaskClient, redis_client: FakeRedis) -> None:
    ShadowSessionInterface.redis = redis_client
    with client.session_transaction() as session:
        assert isinstance(session, ShadowSession)


def test_request_hello(client: FlaskClient, redis_client: FakeRedis) -> None:
    ShadowSessionInterface.redis = redis_client
    response = client.get("/hello")
    assert b"Hello, World!" in response.data


def test_session_set(client: FlaskClient, redis_client: FakeRedis) -> None:
    ShadowSessionInterface.redis = redis_client

    with client.session_transaction() as session:
        session.shadow["shadow_value"] = 43

    assert len(session.shadow) == 1


def test_session_set_reload(client: FlaskClient, redis_client: FakeRedis) -> None:
    ShadowSessionInterface.redis = redis_client

    with client.session_transaction() as session:
        session["session_value"] = 42
        session.shadow["shadow_value"] = 43

    # session's 'save_session' is called when context ends

    with client.session_transaction() as session:
        assert session["session_value"] == 42
        assert session.shadow["shadow_value"] == 43


def test_flash(client: FlaskClient, redis_client: FakeRedis) -> None:
    ShadowSessionInterface.redis = redis_client

    response = client.get("/flash")
    assert response.status_code == 200

    with client.session_transaction() as session:
        assert len(session.shadow) == 1
        # simulate 'get_flashed_messages' (which we can't use because the request context is different)
        flashes = session.pop("_flashes") if "_flashes" in session else []
        assert flashes == [("message", "This is a message")]

    assert len(session.shadow) == 0
