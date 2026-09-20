"""Airflow selection for VENTS Breezy."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import VentsBreezyConfigEntry
from .const import AIRFLOW_MODES
from .coordinator import VentsBreezyCoordinator
from .entity import VentsBreezyEntity


async def async_setup_entry(
    hass: Any,
    entry: VentsBreezyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up airflow selection."""
    async_add_entities([VentsBreezyAirflowSelect(entry.runtime_data.coordinator)])


class VentsBreezyAirflowSelect(VentsBreezyEntity, SelectEntity):
    """Select the unit's airflow path."""

    _attr_translation_key = "airflow_mode"
    _attr_icon = "mdi:swap-horizontal"
    _attr_options = AIRFLOW_MODES

    def __init__(self, coordinator: VentsBreezyCoordinator) -> None:
        """Initialize airflow selection."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.data.serial}_airflow"

    @property
    def current_option(self) -> str | None:
        """Return the selected airflow mode."""
        value = self.coordinator.data.airflow
        return value if value in self.options else None

    async def async_select_option(self, option: str) -> None:
        """Select an airflow mode."""
        if option not in self.options:
            raise ValueError(f"Unsupported airflow mode: {option}")
        await self.coordinator.async_write([("state", "on"), ("airflow", option)])
