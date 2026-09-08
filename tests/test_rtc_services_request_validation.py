# SPDX-License-Identifier: MIT
"""Regression coverage for malformed RTC service request bodies."""

import sqlite3

import pytest
from flask import Flask


@pytest.fixture()
def client(tmp_path):
    import rtc_services

    db_path = tmp_path / "rtc_services.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE agents (
            id INTEGER PRIMARY KEY,
            agent_name TEXT NOT NULL,
            api_key TEXT NOT NULL,
            rtc_balance REAL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE earnings (
            id INTEGER PRIMARY KEY,
            agent_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            reason TEXT DEFAULT '',
            created_at REAL NOT NULL
        )
        """
    )
    conn.execute(
        "INSERT INTO agents (id, agent_name, api_key, rtc_balance) VALUES (?, ?, ?, ?)",
        (1, "payer", "secret", 100.0),
    )
    conn.commit()
    conn.close()

    app = Flask(__name__)
    app.config["TESTING"] = True
    rtc_services.init_app(app, db_path)
    return app.test_client()


@pytest.mark.parametrize("endpoint", ["/api/rtc/pay", "/api/rtc/redeem", "/api/rtc/use"])
@pytest.mark.parametrize("body", [["not", "an", "object"], "text", 1])
def test_rtc_service_routes_reject_non_object_json(client, endpoint, body):
    headers = {"X-API-Key": "secret"} if endpoint == "/api/rtc/pay" else {}

    response = client.post(endpoint, json=body, headers=headers)

    assert response.status_code == 400
    assert response.get_json() == {"error": "JSON object required"}


def test_rtc_pay_rejects_non_string_service_key(client):
    response = client.post(
        "/api/rtc/pay",
        json={"service_key": ["pro_api_day"]},
        headers={"X-API-Key": "secret"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "service_key must be a string"}


@pytest.mark.parametrize("endpoint", ["/api/rtc/redeem", "/api/rtc/use"])
def test_token_routes_reject_non_string_service_token(client, endpoint):
    response = client.post(endpoint, json={"service_token": ["token"]})

    assert response.status_code == 400
    assert response.get_json() == {"error": "service_token must be a string"}
