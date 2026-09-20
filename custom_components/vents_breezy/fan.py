"""Fan platform for VENTS Breezy."""

from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import VentsBreezyConfigEntry
from .const import PRESET_MODES, PRESET_NIGHT, PRESET_TURBO
from .coordinator import VentsBreezyCoordinator
from .entity import VentsBreezyEntity

_NAMED_PERCENTAGES = {"low": 33, "medium": 67, "high": 100}


async def async_setup_entry(
    hass: Any,
    entry: VentsBreezyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Breezy fan entity."""
    async_add_entities([VentsBreezyFan(entry.runtime_data.coordinator)])


class VentsBreezyFan(VentsBreezyEntity, FanEntity):
    """Representation of a VENTS Breezy fan."""

    _attr_name = None
    _attr_translation_key = "breezy"
    _attr_icon = "mdi:hvac"
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_preset_modes = PRESET_MODES
    _attr_speed_count = 100

    def __init__(self, coordinator: VentsBreezyCoordinator) -> None:
        """Initialize the fan entity."""
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.data.serial

    @property
    def is_on(self) -> bool:
        """Return whether the fan is on."""
        return self.coordinator.data.is_on

    @property
    def percentage(self) -> int | None:
        """Return the current fan speed percentage."""
        return self.coordinator.data.percentage

    @property
    def preset_mode(self) -> str | None:
        """Return the active timer preset."""
        if not self.coordinator.data.is_on:
            return None
        if self.coordinator.data.timer_mode == "night":
            return PRESET_NIGHT
        if self.coordinator.data.timer_mode == "party":
            return PRESET_TURBO
        return None

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan, optionally applying a speed or preset."""
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
            return
        if percentage is not None:
            await self.async_set_percentage(percentage)
            return
        await self.coordinator.async_write([("state", "on")])

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        await self.coordinator.async_write([("state", "off")])

    async def async_set_percentage(self, percentage: int) -> None:
        """Set a named remote speed or an arbitrary manual percentage."""
        if percentage <= 0:
            await self.async_turn_off()
            return

        commands: list[tuple[str, str]] = [("timer_mode", "off")]
        named_speed = next(
            (
                speed
                for speed, named_percentage in _NAMED_PERCENTAGES.items()
                if percentage == named_percentage
            ),
            None,
        )
        if named_speed is not None:
            commands.append(("speed", named_speed))
        else:
            commands.extend(
                [
                    ("speed", "manual"),
                    (
                        "man_speed",
                        self.coordinator.client.manual_speed_hex(percentage),
                    ),
                ]
            )
        commands.append(("state", "on"))
        await self.coordinator.async_write(commands)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set Night or Turbo, mirroring the two remote buttons."""
        if preset_mode not in PRESET_MODES:
            raise ValueError(f"Unsupported preset: {preset_mode}")
        timer_mode = "night" if preset_mode == PRESET_NIGHT else "party"
        await self.coordinator.async_write(
            [("state", "on"), ("timer_mode", timer_mode)]
        )
