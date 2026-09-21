"""The VENTS Breezy integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant

from .client import BreezyClient
from .const import DEFAULT_PASSWORD
from .coordinator import VentsBreezyCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.FAN,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


@dataclass(slots=True)
class VentsBreezyRuntimeData:
    """Runtime data for one config entry."""

    coordinator: VentsBreezyCoordinator


type VentsBreezyConfigEntry = ConfigEntry[VentsBreezyRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: VentsBreezyConfigEntry) -> bool:
    """Set up VENTS Breezy from a config entry."""
    client = BreezyClient(
        entry.data[CONF_HOST],
        entry.data.get(CONF_PASSWORD, DEFAULT_PASSWORD),
        name=entry.title,
    )
    if entry.unique_id is not None:
        client.id = entry.unique_id
    coordinator = VentsBreezyCoordinator(hass, client, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = VentsBreezyRuntimeData(coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: VentsBreezyConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
