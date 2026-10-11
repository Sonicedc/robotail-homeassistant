"""Config flow for Robotail."""

from __future__ import annotations

import uuid

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .api import RobotailAuthError, RobotailConnectionError, RobotailError, RobotailApi
from .const import (
    ACCOUNT_TYPE_EMAIL,
    ACCOUNT_TYPE_PHONE,
    CONF_ACCOUNT_TYPE,
    CONF_AREA_CODE,
    CONF_DEVICE_ID,
    DEFAULT_AREA_CODE,
    DOMAIN,
)


async def validate_input(hass: HomeAssistant, data: dict) -> dict:
    """Validate credentials and return account metadata."""
    api = RobotailApi(
        async_get_clientsession(hass), device_id=data[CONF_DEVICE_ID]
    )
    auth = await api.login(
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
        data[CONF_ACCOUNT_TYPE],
        data[CONF_AREA_CODE],
    )
    devices = await api.devices()
    return {"user_id": auth.user_id, "device_count": len(devices)}


class RobotailConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Robotail setup wizard."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Collect and validate a normal Robotail login."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data = dict(user_input)
            data[CONF_USERNAME] = data[CONF_USERNAME].strip()
            data[CONF_AREA_CODE] = data[CONF_AREA_CODE].strip()
            data[CONF_DEVICE_ID] = uuid.uuid4().hex
            try:
                info = await validate_input(self.hass, data)
            except RobotailAuthError:
                errors["base"] = "invalid_auth"
            except RobotailConnectionError:
                errors["base"] = "cannot_connect"
            except RobotailError:
                errors["base"] = "unknown"
            else:
                unique = str(info.get("user_id") or data[CONF_USERNAME]).lower()
                await self.async_set_unique_id(unique)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=data[CONF_USERNAME], data=data
                )

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
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )
