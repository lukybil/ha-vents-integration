"""Diagnostics support for VENTS Breezy."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant

from . import VentsBreezyConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: VentsBreezyConfigEntry
) -> dict[str, Any]:
    """Return diagnostics with credentials removed."""
    state = entry.runtime_data.coordinator.data
    return {
        "config_entry": async_redact_data(dict(entry.data), {CONF_PASSWORD}),
        "state": {
            "is_on": state.is_on,
            "speed": state.speed,
            "percentage": state.percentage,
            "timer_mode": state.timer_mode,
            "airflow": state.airflow,
            "heater_on": state.heater_on,
            "filter_needs_replacement": state.filter_needs_replacement,
            "humidity": state.humidity,
            "serial": state.serial,
            "model": state.model,
            "firmware": state.firmware,
        },
    }
