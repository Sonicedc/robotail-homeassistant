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
from .settings import delay_minutes


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
        try:
            async with self.coordinator.settings_lock:
                config = await self.coordinator.api.configuration(self.serial)
                minutes = delay_minutes(config.get("lazyTime"))
                if minutes is None or not 1 <= minutes <= 60 or minutes != int(minutes):
                    raise HomeAssistantError(
                        "Set a valid 1–60 minute delay before "
                        "toggling automatic cleaning"
                    )
                await self.coordinator.api.set_clean_delay(
                    self.serial, int(minutes), enabled
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
