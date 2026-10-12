"""Robotail automatic cleaning delay control."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTime
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
        RobotailCleanDelay(coordinator, serial) for serial in coordinator.data
    )


class RobotailCleanDelay(RobotailEntity, NumberEntity):
    """Change the delay while preserving the automatic-clean switch."""

    _attr_translation_key = "automatic_clean_delay"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 1
    _attr_native_max_value = 60
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator, serial) -> None:
        super().__init__(coordinator, serial)
        self._attr_unique_id = f"{serial}_automatic_clean_delay"

    @property
    def native_value(self) -> float | None:
        value = (self.robotail_data.get("config") or {}).get("lazyTime")
        return delay_minutes(value)

    async def async_set_native_value(self, value: float) -> None:
        if not 1 <= value <= 60 or value != int(value):
            raise HomeAssistantError("The cleaning delay must be 1–60 whole minutes")
        try:
            async with self.coordinator.settings_lock:
                config = await self.coordinator.api.configuration(self.serial)
                enabled = config.get("sensorSwitch")
                if enabled not in (0, 1, "0", "1"):
                    raise HomeAssistantError(
                        "The automatic cleaning setting is unavailable"
                    )
                await self.coordinator.api.set_clean_delay(
                    self.serial, int(value), int(enabled)
                )
        except RobotailError as err:
            raise HomeAssistantError(
                "Robotail could not change the cleaning delay"
            ) from err
        await self.coordinator.async_request_refresh()
        if not self.coordinator.last_update_success or self.native_value != value:
            raise HomeAssistantError("Robotail has not confirmed the cleaning delay")
