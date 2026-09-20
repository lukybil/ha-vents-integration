"""Switch platform for VENTS Breezy."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import VentsBreezyConfigEntry
from .coordinator import VentsBreezyCoordinator
from .entity import VentsBreezyEntity


async def async_setup_entry(
    hass: Any,
    entry: VentsBreezyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the heater switch."""
    async_add_entities([VentsBreezyHeaterSwitch(entry.runtime_data.coordinator)])


class VentsBreezyHeaterSwitch(VentsBreezyEntity, SwitchEntity):
    """Control the Breezy electric heater."""

    _attr_translation_key = "heater"
    _attr_icon = "mdi:heat-wave"

    def __init__(self, coordinator: VentsBreezyCoordinator) -> None:
        """Initialize the heater switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.data.serial}_heater"

    @property
    def is_on(self) -> bool | None:
        """Return whether the heater is enabled."""
        return self.coordinator.data.heater_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the heater."""
        await self.coordinator.async_write([("heater_state", "on")])

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the heater."""
        await self.coordinator.async_write([("heater_state", "off")])
