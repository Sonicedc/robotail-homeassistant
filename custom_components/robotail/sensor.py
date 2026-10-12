"""Robotail sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfMass, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    ATTR_CAT_ID,
    ATTR_CAT_NAME,
    ATTR_CONFIRMED,
    ATTR_EVENT_TYPE,
    ATTR_RECORD_ID,
)
from .coordinator import RobotailCoordinator
from .entity import RobotailEntity
from .visit import last_cat_name


def _find(data: dict[str, Any], *keys: str) -> Any:
    for section_name in ("usage", "config", "device"):
        section = data.get(section_name) or {}
        for key in keys:
            if key in section and section[key] is not None:
                return section[key]
    return None


def _visit(data: dict[str, Any], key: str) -> Any:
    return (data.get("latest_visit") or {}).get(key)


@dataclass(frozen=True, kw_only=True)
class RobotailSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]


SENSORS = (
    RobotailSensorDescription(
        key="last_cat",
        translation_key="last_cat",
        icon="mdi:cat",
        value_fn=last_cat_name,
    ),
    RobotailSensorDescription(
        key="last_visit",
        translation_key="last_visit",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: _event_datetime(_visit(data, "eventTime")),
    ),
    RobotailSensorDescription(
        key="last_weight",
        translation_key="last_weight",
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        device_class=SensorDeviceClass.WEIGHT,
        suggested_display_precision=2,
        value_fn=lambda data: _visit(data, "weight"),
    ),
    RobotailSensorDescription(
        key="last_duration",
        translation_key="last_duration",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        value_fn=lambda data: _visit(data, "costTime"),
    ),
    RobotailSensorDescription(
        key="usage_count",
        translation_key="usage_count",
        value_fn=lambda data: _find(
            data, "boxUseTimes", "useTimes", "usageCount", "times"
        ),
    ),
    RobotailSensorDescription(
        key="waste_drawer",
        translation_key="waste_drawer",
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda data: _find(
            data, "percentage", "fullPercent", "boxFullPercent", "fullness"
        ),
    ),
)


def _event_datetime(value: Any) -> datetime | None:
    if value in (None, "", 0, "0"):
        return None
    try:
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1000
        return datetime.fromtimestamp(timestamp).astimezone()
    except (TypeError, ValueError, OSError):
        try:
            return datetime.fromisoformat(str(value)).astimezone()
        except ValueError:
            return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator: RobotailCoordinator = entry.runtime_data
    async_add_entities(
        RobotailSensor(coordinator, serial, description)
        for serial in coordinator.data
        for description in SENSORS
    )


class RobotailSensor(RobotailEntity, SensorEntity):
    """A Robotail measurement."""

    entity_description: RobotailSensorDescription

    def __init__(self, coordinator, serial, description) -> None:
        super().__init__(coordinator, serial)
        self.entity_description = description
        self._attr_unique_id = f"{serial}_{description.key}"

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.robotail_data)

    @property
    def extra_state_attributes(self):
        if self.entity_description.key not in {
            "last_cat",
            "last_visit",
            "last_weight",
            "last_duration",
        }:
            return None
        visit = self.robotail_data.get("latest_visit") or {}
        return {
            ATTR_RECORD_ID: visit.get("recordId"),
            ATTR_EVENT_TYPE: visit.get("eventType"),
            ATTR_CONFIRMED: visit.get("confirmed"),
            ATTR_CAT_ID: visit.get("catInfoId") or visit.get("catId"),
            ATTR_CAT_NAME: last_cat_name(self.robotail_data),
        }
