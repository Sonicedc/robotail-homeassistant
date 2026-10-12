"""Config flow for Robotail."""

from __future__ import annotations

import logging
import uuid

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .api import (
    RobotailApi,
    RobotailAuthError,
    RobotailConnectionError,
    RobotailError,
    normalize_account,
)
from .const import (
    ACCOUNT_TYPE_EMAIL,
    ACCOUNT_TYPE_PHONE,
    CONF_ACCOUNT_TYPE,
    CONF_AREA_CODE,
    CONF_COUNTRY_CODE,
    CONF_DEVICE_ID,
    DEFAULT_AREA_CODE,
    DEFAULT_COUNTRY_CODE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict) -> dict:
    """Validate credentials and return account metadata."""
    api = RobotailApi(async_get_clientsession(hass), device_id=data[CONF_DEVICE_ID])
    account = normalize_account(
        data[CONF_USERNAME], data[CONF_ACCOUNT_TYPE], data[CONF_AREA_CODE]
    )
    auth = await api.login(
        account,
        data[CONF_PASSWORD],
        data[CONF_ACCOUNT_TYPE],
        data[CONF_COUNTRY_CODE],
    )
    devices = await api.devices()
    return {"user_id": auth.user_id, "device_count": len(devices)}


class RobotailConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Robotail setup wizard."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Show account-sharing prerequisites before asking for credentials."""
        if user_input is not None:
            return await self.async_step_login()
        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

    async def async_step_login(self, user_input=None):
        """Collect and validate a normal Robotail login."""
        errors: dict[str, str] = {}
        placeholders = {"error_stage": "setup", "error_code": "unknown"}
        if user_input is not None:
            data = dict(user_input)
            data[CONF_USERNAME] = data[CONF_USERNAME].strip()
            data[CONF_AREA_CODE] = data[CONF_AREA_CODE].strip()
            data[CONF_COUNTRY_CODE] = data[CONF_COUNTRY_CODE].strip().upper()
            data[CONF_DEVICE_ID] = uuid.uuid4().hex
            try:
                info = await validate_input(self.hass, data)
            except RobotailConnectionError:
                errors["base"] = "cannot_connect"
            except RobotailError as err:
                if err.code is not None:
                    errors["base"] = "api_error"
                    placeholders = {
                        "error_stage": "signing in"
                        if err.path == "/user-service-rest/v2/user/login"
                        else "finding devices",
                        "error_code": str(err.code),
                    }
                    # Never log server messages, credentials, or response bodies.
                    _LOGGER.warning(
                        "Robotail setup failed while %s (API code %s)",
                        placeholders["error_stage"],
                        placeholders["error_code"],
                    )
                else:
                    errors["base"] = (
                        "invalid_auth"
                        if isinstance(err, RobotailAuthError)
                        else "unknown"
                    )
            else:
                unique = str(info.get("user_id") or data[CONF_USERNAME]).lower()
                await self.async_set_unique_id(unique)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=data[CONF_USERNAME], data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(
                    CONF_ACCOUNT_TYPE, default=ACCOUNT_TYPE_EMAIL
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[ACCOUNT_TYPE_EMAIL, ACCOUNT_TYPE_PHONE],
                        translation_key="account_type",
                    )
                ),
                vol.Required(CONF_AREA_CODE, default=DEFAULT_AREA_CODE): str,
                vol.Required(CONF_COUNTRY_CODE, default=DEFAULT_COUNTRY_CODE): str,
            }
        )
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(
                schema,
                {
                    key: value
                    for key, value in user_input.items()
                    if key != CONF_PASSWORD
                },
            )
        return self.async_show_form(
            step_id="login",
            data_schema=schema,
            errors=errors,
            description_placeholders=placeholders,
        )
