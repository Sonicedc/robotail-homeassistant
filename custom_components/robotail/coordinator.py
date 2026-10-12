"""Robotail data coordinator."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import RobotailApi, RobotailError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class RobotailCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Fetch account devices and their latest measurements."""

    def __init__(self, hass: HomeAssistant, api: RobotailApi) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            devices = await self.api.devices()
            try:
                cats = await self.api.cats()
            except RobotailError:
                # Cat-profile access may be limited on shared accounts.
                # Measurements remain available even without identity metadata.
                cats = []

            async def fetch(device: dict[str, Any]) -> tuple[str, dict[str, Any]]:
                serial = str(device.get("serialNumber") or device.get("sn") or "")
                if not serial:
                    raise RobotailError("A device did not include a serial number")
                config, usage, events = await asyncio.gather(
                    self.api.configuration(serial),
                    self.api.usage(serial),
                    self.api.events(serial),
                )
                return serial, {
                    "device": device,
                    "config": config,
                    "usage": usage,
                    "events": events,
                    "cats": cats,
                    "latest_visit": next(
                        (row for row in events if str(row.get("eventType")) == "3"),
                        None,
                    ),
                }

            return dict(await asyncio.gather(*(fetch(item) for item in devices)))
        except RobotailError as err:
            raise UpdateFailed(str(err)) from err
