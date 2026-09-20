"""Shared VENTS Breezy entity support."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import VentsBreezyCoordinator


class VentsBreezyEntity(CoordinatorEntity[VentsBreezyCoordinator]):
    """Base entity for a Breezy unit."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: VentsBreezyCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        state = coordinator.data
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, state.serial)},
            manufacturer="VENTS",
            model=state.model,
            name=coordinator.client.name,
            serial_number=state.serial,
            sw_version=state.firmware,
        )
