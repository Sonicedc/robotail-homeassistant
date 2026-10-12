"""Robotail binary sensors."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import RobotailCoordinator
from .entity import RobotailEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator: RobotailCoordinator = entry.runtime_data
    async_add_entities(
        RobotailOnlineBinarySensor(coordinator, serial) for serial in coordinator.data
    )


class RobotailOnlineBinarySensor(RobotailEntity, BinarySensorEntity):
    """Whether Robotail reports a box online."""

    _attr_translation_key = "online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: RobotailCoordinator, serial: str) -> None:
        super().__init__(coordinator, serial)
        self._attr_unique_id = f"{serial}_online"

    @property
    def is_on(self) -> bool | None:
        value = self.robotail_data.get("online_status")
        if value is None:
            return None
        if value in (1, "1"):
            return True
        if value in (0, "0"):
            return False
        return None
