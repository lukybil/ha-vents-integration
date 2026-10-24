"""LED panel brightness control for VENTS Breezy."""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import VentsBreezyConfigEntry
from .coordinator import VentsBreezyCoordinator
from .entity import VentsBreezyEntity


async def async_setup_entry(
    hass: Any,
    entry: VentsBreezyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the panel brightness control."""
    async_add_entities([VentsBreezyPanelBrightness(entry.runtime_data.coordinator)])


class VentsBreezyPanelBrightness(VentsBreezyEntity, NumberEntity):
    """Adjust panel brightness independently of ventilation power and speed."""

    _attr_translation_key = "panel_brightness"
    _attr_icon = "mdi:brightness-6"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = 1
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator: VentsBreezyCoordinator) -> None:
        """Initialize panel brightness."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.data.serial}_panel_brightness"

    @property
    def native_value(self) -> int | None:
        """Return the manual brightness setting."""
        return self.coordinator.data.panel_brightness

    async def async_set_native_value(self, value: float) -> None:
        """Apply manual brightness without changing the display schedule."""
        if not 1 <= value <= 100 or not float(value).is_integer():
            raise ValueError(
                "Panel brightness must be a whole percentage from 1 to 100"
            )
        await self.coordinator.async_write(
            [
                ("panel_brightness", f"{int(value):02x}"),
                ("panel_backlight_mode", "manual"),
            ]
        )
