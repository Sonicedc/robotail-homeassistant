"""Robotail automatic cleaning switch."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import RobotailError
from .coordinator import RobotailCoordinator
from .entity import RobotailEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator: RobotailCoordinator = entry.runtime_data
    async_add_entities(
        RobotailAutomaticCleaning(coordinator, serial) for serial in coordinator.data
    )


class RobotailAutomaticCleaning(RobotailEntity, SwitchEntity):
    """Enable automatic cleaning while retaining the configured delay."""

    _attr_translation_key = "automatic_cleaning"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:autorenew"

    def __init__(self, coordinator, serial) -> None:
        super().__init__(coordinator, serial)
        self._attr_unique_id = f"{serial}_automatic_cleaning"

    @property
    def is_on(self) -> bool | None:
        value = (self.robotail_data.get("config") or {}).get("sensorSwitch")
        if value in (1, "1"):
            return True
        if value in (0, "0"):
            return False
        return None

    async def _set_enabled(self, enabled: int) -> None:
        delay = (self.robotail_data.get("config") or {}).get("lazyTime")
        try:
            delay_number = float(delay)
        except (TypeError, ValueError):
            raise HomeAssistantError(
                "The automatic cleaning delay is unavailable"
            ) from None
        if not 1 <= delay_number <= 60 or delay_number != int(delay_number):
            raise HomeAssistantError("The automatic cleaning delay is unavailable")
        try:
            await self.coordinator.api.set_clean_delay(
                self.serial, int(delay_number), enabled
            )
        except RobotailError as err:
            raise HomeAssistantError(
                "Robotail could not change automatic cleaning"
            ) from err
        await self.coordinator.async_request_refresh()
        if not self.coordinator.last_update_success or self.is_on != bool(enabled):
            raise HomeAssistantError(
                "Robotail has not confirmed the automatic cleaning setting"
            )

    async def async_turn_on(self, **kwargs) -> None:
        await self._set_enabled(1)

    async def async_turn_off(self, **kwargs) -> None:
        await self._set_enabled(0)
