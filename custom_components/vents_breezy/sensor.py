"""Sensor platform for VENTS Breezy."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import VentsBreezyConfigEntry
from .coordinator import VentsBreezyCoordinator
from .entity import VentsBreezyEntity


async def async_setup_entry(
    hass: Any,
    entry: VentsBreezyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Breezy sensors."""
    async_add_entities([VentsBreezyHumiditySensor(entry.runtime_data.coordinator)])


class VentsBreezyHumiditySensor(VentsBreezyEntity, SensorEntity):
    """Report relative humidity measured by the unit."""

    _attr_translation_key = "humidity"
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator: VentsBreezyCoordinator) -> None:
        """Initialize the humidity sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.data.serial}_humidity"

    @property
    def native_value(self) -> int | None:
        """Return the relative humidity."""
        return self.coordinator.data.humidity
