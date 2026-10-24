"""Small Breezy-specific adapter around pyEcoventV2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ecoventv2 import Fan

from .const import DEFAULT_NAME, DEFAULT_PASSWORD, DEFAULT_PORT


class BreezyConnectionError(Exception):
    """Raised when the fan does not answer a command."""


@dataclass(frozen=True, slots=True)
class BreezyState:
    """A stable snapshot of the values exposed to Home Assistant."""

    is_on: bool
    speed: str | None
    percentage: int | None
    timer_mode: str | None
    airflow: str | None
    heater_on: bool | None
    filter_needs_replacement: bool | None
    humidity: int | None
    serial: str
    model: str
    firmware: str | None
    panel_brightness: int | None = None
    panel_backlight_mode: str | None = None
    panel_display: str | None = None


class BreezyClient(Fan):
    """Adapt the general VENTS protocol client to the Breezy 160-E map."""

    states: Final = {0: "off", 1: "on", 2: "toggle"}
    speeds: Final = {
        0: "standby",
        1: "low",
        2: "medium",
        3: "high",
        0xFF: "manual",
    }
    timer_modes: Final = {0: "off", 1: "night", 2: "party"}
    statuses: Final = {0: "off", 1: "on"}
    airflows: Final = {
        0: "ventilation",
        1: "heat_recovery",
        2: "air_supply",
        3: "extract",
    }
    unit_types: Final = {0x1100: "VENTS Breezy 160-E"}
    panel_backlight_modes: Final = {0: "auto", 1: "manual"}
    panel_display_modes: Final = {0: "off", 1: "on", 2: "off_interval"}

    # Keep the map deliberately small. The upstream library polls a broad VENTS
    # register set by default; some Breezy firmware rejects unrelated registers.
    params: Final = {
        0x0001: ["state", states],
        0x0002: ["speed", speeds],
        0x0007: ["timer_mode", timer_modes],
        0x0025: ["humidity", None],
        0x0044: ["man_speed", None],
        0x0064: ["filter_timer_countdown", None],
        0x0065: ["filter_timer_reset", None],
        0x0068: ["heater_state", states],
        0x007C: ["device_search", None],
        0x0086: ["firmware", None],
        0x0088: ["filter_replacement_status", statuses],
        0x00B7: ["airflow", airflows],
        0x00B9: ["unit_type", unit_types],
        0x0400: ["panel_brightness", None],
        0x0402: ["panel_backlight_mode", panel_backlight_modes],
        0x0407: ["panel_display", panel_display_modes],
    }

    _POLL_PARAMETERS: Final = "0001000200070025004400640068007c0086008800b700b9"

    def __init__(
        self,
        host: str,
        password: str = DEFAULT_PASSWORD,
        *,
        name: str = DEFAULT_NAME,
        port: int = DEFAULT_PORT,
    ) -> None:
        """Initialize a Breezy client."""
        super().__init__(host, password=password, name=name, port=port)
        self._heater_state: str | None = None
        self._man_speed: int | None = None
        self._panel_brightness: int | None = None
        self._panel_backlight_mode: str | None = None
        self._panel_display: str | None = None

    def initialize(self) -> BreezyState:
        """Discover the controller ID and perform the first poll."""
        device_search_index = self.get_params_index("device_search")
        if device_search_index is None or not self.do_func(
            self.func["read"], hex(device_search_index).removeprefix("0x").zfill(4)
        ):
            raise BreezyConnectionError("The fan did not return its controller ID")
        if not self.device_search:
            raise BreezyConnectionError("The fan did not return its controller ID")
        self.id = self.device_search
        return self.update_state()

    def do_func(self, func: str, param: str, value: str = "") -> bool:
        """Run the upstream request while normalizing its transport failures."""
        try:
            return bool(super().do_func(func, param, value))
        except (AttributeError, KeyError, OSError, TypeError, ValueError):
            return False

    def update_state(self) -> BreezyState:
        """Poll only registers used by this integration."""
        if not self.do_func(self.func["read"], self._POLL_PARAMETERS):
            raise BreezyConnectionError("The fan did not answer the status request")
        # Read high-page rows individually: pyEcoventV2 0.9.26 resets the page
        # after each response value. Unsupported panel rows must not break the fan.
        for parameter in ("panel_brightness", "panel_backlight_mode", "panel_display"):
            setattr(self, f"_{parameter}", None)
            index = self.get_params_index(parameter)
            if not self.do_func(self.func["read"], f"{index:04x}"):
                setattr(self, f"_{parameter}", None)
        return self.snapshot()

    def write(self, parameter: str, value: str) -> None:
        """Write one semantic parameter and require a device response."""
        index, mapped_value = self.get_params_values(parameter, value)
        if index is None:
            raise ValueError(f"Unsupported Breezy parameter: {parameter}")

        encoded_value = (
            hex(mapped_value).removeprefix("0x").zfill(2)
            if mapped_value is not None
            else value
        )
        if not self.do_func(
            self.func["write_return"],
            hex(index).removeprefix("0x").zfill(4),
            encoded_value,
        ):
            raise BreezyConnectionError(f"The fan rejected {parameter}")

    def write_many(self, commands: list[tuple[str, str]]) -> None:
        """Apply a short sequence of commands."""
        for parameter, value in commands:
            self.write(parameter, value)

    @property
    def panel_brightness(self) -> int | None:
        """Return the manual panel brightness percentage."""
        return self._panel_brightness

    @panel_brightness.setter
    def panel_brightness(self, value: str) -> None:
        brightness = int(value, 16)
        self._panel_brightness = brightness if 1 <= brightness <= 100 else None

    @property
    def panel_backlight_mode(self) -> str | None:
        """Return whether backlighting follows the light sensor or a manual level."""
        return self._panel_backlight_mode

    @panel_backlight_mode.setter
    def panel_backlight_mode(self, value: str) -> None:
        self._panel_backlight_mode = self.panel_backlight_modes.get(int(value, 16))

    @property
    def panel_display(self) -> str | None:
        """Return the screen display setting, including its configured schedule."""
        return self._panel_display

    @panel_display.setter
    def panel_display(self, value: str) -> None:
        self._panel_display = self.panel_display_modes.get(int(value, 16))

    @property
    def heater_state(self) -> str | None:
        """Return whether the electric heater is enabled."""
        return self._heater_state

    @heater_state.setter
    def heater_state(self, value: str) -> None:
        self._heater_state = self.states.get(int(value, 16))

    @property
    def man_speed(self) -> int | None:
        """Return Breezy manual speed, which is natively a percentage."""
        return self._man_speed

    @man_speed.setter
    def man_speed(self, value: str) -> None:
        percentage = int(value, 16)
        self._man_speed = percentage if 0 <= percentage <= 100 else None

    def snapshot(self) -> BreezyState:
        """Return an immutable state snapshot without network I/O."""
        percentage: int | None
        if self.state == "off":
            percentage = 0
        elif self.speed == "low":
            percentage = 33
        elif self.speed == "medium":
            percentage = 67
        elif self.speed == "high":
            percentage = 100
        elif self.speed == "manual":
            percentage = self.man_speed
        else:
            percentage = None

        humidity = int(self.humidity) if self.humidity is not None else None
        return BreezyState(
            is_on=self.state == "on",
            speed=self.speed,
            percentage=percentage,
            timer_mode=self.timer_mode,
            airflow=self.airflow,
            heater_on=(
                None if self.heater_state is None else self.heater_state == "on"
            ),
            filter_needs_replacement=(
                None
                if self.filter_replacement_status is None
                else self.filter_replacement_status == "on"
            ),
            humidity=humidity,
            serial=self.id,
            model=self.unit_type or DEFAULT_NAME,
            firmware=self.firmware,
            panel_brightness=self.panel_brightness,
            panel_backlight_mode=self.panel_backlight_mode,
            panel_display=self.panel_display,
        )

    @staticmethod
    def manual_speed_hex(percentage: int) -> str:
        """Convert a Home Assistant percentage to the device's byte value."""
        # Breezy uses a direct 10-100 scale here, unlike older VENTO models
        # that use the entire 0-255 byte range.
        percentage = max(10, min(100, percentage))
        return hex(percentage).removeprefix("0x").zfill(2)
