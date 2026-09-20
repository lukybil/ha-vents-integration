"""Button platform for VENTS Breezy."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
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
    """Set up the filter reset button."""
    async_add_entities([VentsBreezyFilterResetButton(entry.runtime_data.coordinator)])


class VentsBreezyFilterResetButton(VentsBreezyEntity, ButtonEntity):
    """Reset the filter service timer."""

    _attr_translation_key = "reset_filter"
    _attr_icon = "mdi:air-filter"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: VentsBreezyCoordinator) -> None:
        """Initialize the reset button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.data.serial}_reset_filter"

    async def async_press(self) -> None:
        """Reset the filter timer."""
        await self.coordinator.async_write([("filter_timer_reset", "01")])
