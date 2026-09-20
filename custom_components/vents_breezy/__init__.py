"""The VENTS Breezy integration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant

from .client import BreezyClient
from .const import CARD_URL, CARD_VERSION, DEFAULT_PASSWORD
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


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register the dashboard card bundled with the integration."""
    card_path = Path(__file__).parent / "frontend" / "vents-breezy-card.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(card_path), False)]
    )
    add_extra_js_url(hass, f"{CARD_URL}?v={CARD_VERSION}")
    return True


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
