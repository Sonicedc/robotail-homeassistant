"""Async client for the Robotail cloud API."""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from dataclasses import dataclass
from typing import Any

from aiohttp import ClientError, ClientSession

from .const import ACCOUNT_TYPE_VALUES, API_HOST, APP_ID, APP_KEY


class RobotailError(Exception):
    """Base Robotail API error."""

    def __init__(self, message: str, *, code=None, path: str | None = None):
        super().__init__(message)
        self.code = code
        self.path = path


class RobotailAuthError(RobotailError):
    """Robotail rejected the supplied credentials or token."""


class RobotailConnectionError(RobotailError):
    """Robotail could not be reached."""


def normalize_account(account: str, account_type: str, calling_code: str) -> str:
    """Match the official app's phone-account construction."""
    account = account.strip()
    if account_type != "phone":
        return account
    phone = re.sub(r"\D", "", account)
    prefix = re.sub(r"\D", "", calling_code)
    if prefix and not phone.startswith(prefix):
        phone = f"{prefix}{phone}"
    return phone


@dataclass(slots=True)
class RobotailAuth:
    """Authentication returned by Robotail."""

    token: str
    refresh_token: str | None = None
    expires_at: int | None = None
    user_id: str | None = None


class RobotailApi:
    """Minimal read-only Robotail API client."""

    def __init__(
        self,
        session: ClientSession,
        *,
        device_id: str,
        host: str = API_HOST,
        app_id: str = APP_ID,
        app_key: str = APP_KEY,
        token: str | None = None,
    ) -> None:
        self._session = session
        self._host = host.rstrip("/")
        self._app_id = app_id
        self._app_key = app_key
        self._device_id = device_id
        self.auth = RobotailAuth(token=token) if token else None

    def _headers(self, *, authenticated: bool = True) -> dict[str, str]:
        timestamp = int(time.time() * 1000)
        nonce = str(uuid.uuid4())[:10]
        material = f"{timestamp}{self._app_key}{nonce}{self._device_id}"
        digest = hashlib.md5(material.encode(), usedforsecurity=False).hexdigest()
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-UBT-AppId": self._app_id,
            "X-UBT-DeviceId": self._device_id,
            "X-UBT-Sign": f"{digest} {timestamp} {nonce} v2",
            # Robotail rejects the HomeAssistant-Robotail client header with 403.
            "User-Agent": "Robotail/1.0.1",
        }
        if authenticated:
            if self.auth is None or not self.auth.token:
                raise RobotailAuthError("No Robotail access token is available")
            headers["authorization"] = self.auth.token
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        authenticated: bool = True,
        json_body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> Any:
        try:
            async with self._session.request(
                method,
                f"{self._host}{path}",
                headers=self._headers(authenticated=authenticated),
                json=json_body,
                params=params,
                timeout=20,
            ) as response:
                if response.status in (401, 403):
                    raise RobotailAuthError(
                        "Robotail authentication failed",
                        code=f"HTTP {response.status}",
                        path=path,
                    )
                payload = await response.json(content_type=None)
                # The login endpoint returns structured errors with HTTP 400.
                # Read the envelope before treating that as a transport failure.
                if not isinstance(payload, dict) or payload.get("code") in (
                    None,
                    0,
                    200,
                    "0",
                    "200",
                ):
                    response.raise_for_status()
        except RobotailAuthError:
            raise
        except (ClientError, TimeoutError, json.JSONDecodeError) as err:
            raise RobotailConnectionError(str(err)) from err

        if not isinstance(payload, dict):
            raise RobotailError("Robotail returned an unexpected response")
        code = payload.get("code")
        if code not in (None, 0, 200, "0", "200"):
            message = str(payload.get("message") or "Robotail request failed")
            if str(code) in ("401", "403"):
                raise RobotailAuthError(message, code=code, path=path)
            raise RobotailError(message, code=code, path=path)
        return payload.get("data", payload)

    async def login(
        self, account: str, password: str, account_type: str, country_code: str
    ) -> RobotailAuth:
        """Authenticate using the same password flow as the official app."""
        password_hash = hashlib.md5(
            password.encode(), usedforsecurity=False
        ).hexdigest()
        data = await self._request(
            "PUT",
            "/user-service-rest/v2/user/login",
            authenticated=False,
            json_body={
                "account": account,
                "accountType": ACCOUNT_TYPE_VALUES[account_type],
                "password": password_hash,
                "areaCode": country_code.upper(),
            },
        )
        token_data = data.get("token", data) if isinstance(data, dict) else {}
        token = token_data.get("token") or token_data.get("accessToken")
        if not token:
            raise RobotailError("Login succeeded but no access token was returned")
        self.auth = RobotailAuth(
            token=token,
            refresh_token=token_data.get("refreshToken"),
            expires_at=token_data.get("expireAt") or token_data.get("expiresAt"),
            user_id=(data.get("user") or {}).get("userId")
            if isinstance(data, dict)
            else None,
        )
        return self.auth

    async def devices(self) -> list[dict[str, Any]]:
        data = await self._request(
            "GET", "/user-service-rest/v2/robot/common/device/list"
        )
        if isinstance(data, list):
            return data
        for key in ("records", "list", "devices"):
            if isinstance(data, dict) and isinstance(data.get(key), list):
                return data[key]
        return []

    async def configuration(self, serial: str) -> dict[str, Any]:
        data = await self._request(
            "GET",
            "/catbox-server/box/config/allConfig",
            params={"serialNumber": serial},
        )
        return data if isinstance(data, dict) else {}

    async def usage(self, serial: str) -> dict[str, Any]:
        data = await self._request(
            "GET",
            "/catbox-server/box/config/box-use-times",
            params={"serialNumber": serial},
        )
        return data if isinstance(data, dict) else {}

    async def events(self, serial: str, size: int = 30) -> list[dict[str, Any]]:
        data = await self._request(
            "POST",
            "/catbox-server/web/box/record/new",
            json_body={
                "serialNumber": serial,
                "eventTime": "0",
                "messageType": 0,
                "size": size,
            },
        )
        if isinstance(data, dict) and isinstance(data.get("records"), list):
            return data["records"]
        return data if isinstance(data, list) else []
