"""Robotail Home Assistant integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import RobotailApi, RobotailAuthError, RobotailConnectionError
from .const import (
    CONF_ACCOUNT_TYPE,
    CONF_AREA_CODE,
    CONF_DEVICE_ID,
    DOMAIN,
    EVENT_CAT_VISIT,
    PLATFORMS,
)
from .coordinator import RobotailCoordinator

type RobotailConfigEntry = ConfigEntry[RobotailCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: RobotailConfigEntry) -> bool:
    """Set up Robotail from a config entry."""
    api = RobotailApi(
        async_get_clientsession(hass), device_id=entry.data[CONF_DEVICE_ID]
    )
    try:
        await api.login(
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            entry.data[CONF_ACCOUNT_TYPE],
            entry.data[CONF_AREA_CODE],
        )
    except RobotailAuthError as err:
        raise ConfigEntryAuthFailed from err
    except RobotailConnectionError as err:
        raise ConfigEntryNotReady from err
    coordinator = RobotailCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    previous: dict[str, str | None] = {}

    def fire_new_visits() -> None:
        for serial, data in coordinator.data.items():
            visit = data.get("latest_visit") or {}
            record_id = str(visit.get("recordId") or "") or None
            if serial not in previous:
                previous[serial] = record_id
            elif record_id and previous[serial] != record_id:
                previous[serial] = record_id
                hass.bus.async_fire(
                    EVENT_CAT_VISIT,
                    {
                        "serial_number": serial,
                        "record_id": record_id,
                        "weight": visit.get("weight"),
                        "duration": visit.get("costTime"),
                        "event_time": visit.get("eventTime"),
                    },
                )

    entry.async_on_unload(coordinator.async_add_listener(fire_new_visits))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RobotailConfigEntry) -> bool:
    """Unload Robotail."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
