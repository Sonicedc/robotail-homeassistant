"""Base entities for Robotail."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RobotailCoordinator


class RobotailEntity(CoordinatorEntity[RobotailCoordinator]):
    """Base class tied to one Robotail litter box."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: RobotailCoordinator, serial: str) -> None:
        super().__init__(coordinator)
        self.serial = serial
        device = coordinator.data[serial]["device"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            name=device.get("robotName")
            or device.get("deviceName")
            or device.get("name")
            or f"Robotail {serial[-4:]}",
            manufacturer="Robotail",
            model=device.get("model") or device.get("productName") or "UCAT",
            serial_number=serial,
            sw_version=device.get("version") or device.get("firmwareVersion"),
        )

    @property
    def robotail_data(self) -> dict[str, Any]:
        return self.coordinator.data[self.serial]

