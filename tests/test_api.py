"""Tests for the standalone Robotail API client."""

from __future__ import annotations

import hashlib

import pytest

from custom_components.robotail.api import (
    RobotailApi,
    RobotailAuthError,
    RobotailError,
    normalize_account,
)
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
    assert session.requests[0][2]["headers"]["User-Agent"] == "Robotail/1.0.1"


@pytest.mark.asyncio
async def test_http_access_denied_retains_status_and_stage():
    session = FakeSession([{"message": "Access denied"}], status=403)
    api = RobotailApi(session, device_id="device-id")

    with pytest.raises(RobotailAuthError) as caught:
        await api.login("12025550123", "password", ACCOUNT_TYPE_PHONE, "US")

    assert caught.value.code == "HTTP 403"
    assert caught.value.path == "/user-service-rest/v2/user/login"


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


@pytest.mark.asyncio
async def test_clean_delay_preserves_enabled_state_in_app_switch_payload():
    session = FakeSession([{"code": 0, "data": 1}])
    api = RobotailApi(session, device_id="device-id", token="access-token")
    await api.set_clean_delay("serial-number", 5, 0)
    method, url, kwargs = session.requests[0]
    assert method == "PUT"
    assert url.endswith("/box/config/switch/update")
    assert kwargs["json"] == {
        "functionType": 2,
        "controlSwitch": 0,
        "optionInt": 5,
        "serialNumber": "serial-number",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("minutes", [0, 61, 1.5, True])
async def test_invalid_delay_never_reaches_network(minutes):
    session = FakeSession([])
    api = RobotailApi(session, device_id="device-id", token="access-token")
    with pytest.raises(ValueError):
        await api.set_clean_delay("serial-number", minutes, 1)
    assert session.requests == []


@pytest.mark.asyncio
async def test_profile_and_im_routes():
    session = FakeSession(
        [
            {"code": 0, "data": [{"catInfoId": 10, "nickname": "Cat"}]},
            {"code": 0, "data": {"subTopic": "topic"}},
            {"code": 0, "data": [{"userId": "device-user", "userName": "serial"}]},
        ]
    )
    api = RobotailApi(session, device_id="device-id", token="access-token")
    assert len(await api.cats()) == 1
    assert (await api.im_login())["subTopic"] == "topic"
    assert len(await api.im_friends()) == 1
    assert session.requests[0][0] == "GET"
    assert session.requests[1][0] == "POST"
    assert session.requests[1][2]["json"] == {"type": 2}
    assert session.requests[2][0] == "GET"
