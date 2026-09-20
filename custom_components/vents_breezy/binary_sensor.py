"""Binary sensor platform for VENTS Breezy."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import VentsBreezyConfigEntry
from .coordinator import VentsBreezyCoordinator
from .entity import VentsBreezyEntity


async def async_setup_entry(
    hass: Any,
    entry: VentsBreezyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up filter status."""
    async_add_entities([VentsBreezyFilterSensor(entry.runtime_data.coordinator)])


class VentsBreezyFilterSensor(VentsBreezyEntity, BinarySensorEntity):
    """Report whether the filter requires replacement."""

    _attr_translation_key = "filter"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: VentsBreezyCoordinator) -> None:
        """Initialize filter status."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.data.serial}_filter"

    @property
    def is_on(self) -> bool | None:
        """Return true when the filter needs replacement."""
        return self.coordinator.data.filter_needs_replacement
