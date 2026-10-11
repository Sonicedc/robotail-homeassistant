"""Tests for the standalone Robotail API client."""

from __future__ import annotations

import hashlib

import pytest

from custom_components.robotail.api import RobotailApi, RobotailError, normalize_account
from custom_components.robotail.const import ACCOUNT_TYPE_EMAIL, ACCOUNT_TYPE_PHONE


def test_us_phone_account_is_prefixed_like_official_app():
    assert normalize_account("(252) 555-0041", "phone", "+1") == "12525550041"
    assert normalize_account("12525550041", "phone", "+1") == "12525550041"


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError("HTTP error checked before structured API error")
        return None

    async def json(self, **_):
        return self.payload


class FakeSession:
    def __init__(self, responses, status=200):
        self.responses = iter(responses)
        self.requests = []
        self.status = status

    def request(self, method, url, **kwargs):
        self.requests.append((method, url, kwargs))
        return FakeResponse(next(self.responses), self.status)


@pytest.mark.asyncio
async def test_login_hashes_password_and_reads_token():
    session = FakeSession(
        [
            {
                "code": 0,
                "data": {
                    "token": {
                        "token": "access-token",
                        "refreshToken": "refresh-token",
                        "expireAt": 123,
                    },
                    "user": {"userId": "42"},
                },
            }
        ]
    )
    api = RobotailApi(session, device_id="device-id")

    auth = await api.login("person@example.com", "password", ACCOUNT_TYPE_EMAIL, "US")

    assert auth.token == "access-token"
    assert auth.refresh_token == "refresh-token"
    body = session.requests[0][2]["json"]
    assert session.requests[0][0] == "PUT"
    assert body["accountType"] == 1
    assert (
        body["password"] == hashlib.md5(b"password", usedforsecurity=False).hexdigest()
    )
    assert body["areaCode"] == "US"
    assert "authorization" not in session.requests[0][2]["headers"]


@pytest.mark.asyncio
async def test_phone_login_uses_zero_and_preserves_http_400_api_error():
    session = FakeSession(
        [{"code": 2004, "message": "User does not exist"}], status=400
    )
    api = RobotailApi(session, device_id="device-id")

    with pytest.raises(RobotailError) as caught:
        await api.login("12025550123", "password", ACCOUNT_TYPE_PHONE, "US")

    assert caught.value.code == 2004
    assert caught.value.path == "/user-service-rest/v2/user/login"
    assert session.requests[0][2]["json"]["accountType"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("code", [1002, "1002", 1009])
async def test_invalid_request_is_not_reported_as_bad_credentials(code):
    session = FakeSession([{"code": code, "message": "Invalid fields"}])
    api = RobotailApi(session, device_id="device-id")

    with pytest.raises(RobotailError) as caught:
        await api.login("12025550123", "password", ACCOUNT_TYPE_PHONE, "US")

    assert type(caught.value) is RobotailError
    assert caught.value.code == code


@pytest.mark.asyncio
async def test_event_history_payload():
    session = FakeSession(
        [{"code": 0, "data": {"records": [{"eventType": 3, "weight": 4.1}]}}]
    )
    api = RobotailApi(session, device_id="device-id", token="access-token")

    records = await api.events("serial-number")

    assert records[0]["eventType"] == 3
    request = session.requests[0]
    assert request[2]["json"]["serialNumber"] == "serial-number"
    assert request[2]["headers"]["authorization"] == "access-token"
