# SPDX-License-Identifier: MIT

import sqlite3

import pytest
from flask import Flask

from bottube_x402 import init_app


def _create_app(tmp_path):
    db_path = tmp_path / "bottube.sqlite3"
    with sqlite3.connect(db_path) as db:
        db.execute(
            """
            CREATE TABLE agents (
                id INTEGER PRIMARY KEY,
                agent_name TEXT,
                display_name TEXT,
                api_key TEXT,
                coinbase_address TEXT,
                coinbase_wallet_created INTEGER DEFAULT 0
            )
            """
        )
        db.execute(
            "INSERT INTO agents (id, agent_name, display_name, api_key) VALUES (?, ?, ?, ?)",
            (1, "alice", "Alice", "secret"),
        )

    app = Flask(__name__)
    init_app(app, db_path)
    return app


@pytest.mark.parametrize("body", [["not", "an", "object"], "text", 42])
def test_coinbase_wallet_rejects_non_object_json(tmp_path, body):
    client = _create_app(tmp_path).test_client()

    response = client.post(
        "/api/agents/me/coinbase-wallet",
        json=body,
        headers={"Authorization": "Bearer secret"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "JSON object required"}


@pytest.mark.parametrize("address", [["0x123"], {"address": "0x123"}, False, 0])
def test_coinbase_wallet_rejects_non_string_address(tmp_path, address):
    client = _create_app(tmp_path).test_client()

    response = client.post(
        "/api/agents/me/coinbase-wallet",
        json={"coinbase_address": address},
        headers={"Authorization": "Bearer secret"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "coinbase_address must be a string"}


def test_coinbase_wallet_accepts_valid_manual_address(tmp_path):
    client = _create_app(tmp_path).test_client()
    address = "0x" + "1" * 40

    response = client.post(
        "/api/agents/me/coinbase-wallet",
        json={"coinbase_address": address},
        headers={"Authorization": "Bearer secret"},
    )

    assert response.status_code == 200
    assert response.get_json()["coinbase_address"] == address


def test_coinbase_wallet_checks_auth_before_json_shape(tmp_path):
    client = _create_app(tmp_path).test_client()

    response = client.post("/api/agents/me/coinbase-wallet", json=["invalid"])

    assert response.status_code == 401
    assert response.get_json() == {"error": "API key required"}
