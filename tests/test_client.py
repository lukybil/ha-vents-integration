"""Tests for the Breezy protocol adapter."""

import sys
from pathlib import Path
from types import ModuleType

import pytest

# Keep these protocol tests lightweight: load the integration package as a
# namespace so importing client.py does not require a full Home Assistant test
# environment.
PACKAGE_NAME = "custom_components.vents_breezy"
package = ModuleType(PACKAGE_NAME)
package.__path__ = [
    str(Path(__file__).parents[1] / "custom_components" / "vents_breezy")
]
sys.modules.setdefault(PACKAGE_NAME, package)

from custom_components.vents_breezy.client import BreezyClient  # noqa: E402


def test_snapshot_maps_remote_state() -> None:
    """A protocol response is converted into a stable HA-facing snapshot."""
    client = BreezyClient("192.0.2.1")
    client.id = "BREEZY123456789"
    client.state = "01"
    client.speed = "03"
    client.timer_mode = "00"
    client.airflow = "03"
    client.heater_state = "01"
    client.filter_replacement_status = "01"
    client.humidity = "2d"
    client.unit_type = "1100"

    state = client.snapshot()

    assert state.is_on is True
    assert state.percentage == 100
    assert state.airflow == "extract"
    assert state.heater_on is True
    assert state.filter_needs_replacement is True
    assert state.humidity == 45
    assert state.model == "VENTS Breezy 160-E"


def test_write_maps_semantic_value(monkeypatch) -> None:
    """Semantic writes reuse the upstream protocol encoder."""
    client = BreezyClient("192.0.2.1")
    calls: list[tuple[str, str, str]] = []

    def fake_do_func(function: str, parameter: str, value: str = "") -> bool:
        calls.append((function, parameter, value))
        return True

    monkeypatch.setattr(client, "do_func", fake_do_func)
    client.write("airflow", "extract")

    assert calls == [(client.func["write_return"], "00b7", "03")]


def test_initialize_discovers_controller_id(monkeypatch) -> None:
    """Setup performs discovery before polling with the real controller ID."""
    client = BreezyClient("192.0.2.1")

    def fake_do_func(function: str, parameter: str, value: str = "") -> bool:
        if parameter == "007c":
            client.device_search = "425245455a5931323334353637383930"
        return True

    monkeypatch.setattr(client, "do_func", fake_do_func)

    state = client.initialize()

    assert state.serial == "BREEZY1234567890"


def test_manual_speed_encoding() -> None:
    """Percentage endpoints map to the device byte range."""
    assert BreezyClient.manual_speed_hex(1) == "0a"
    assert BreezyClient.manual_speed_hex(50) == "32"
    assert BreezyClient.manual_speed_hex(100) == "64"

    client = BreezyClient("192.0.2.1")
    client.man_speed = "32"
    assert client.man_speed == 50


@pytest.mark.parametrize("brightness", [1, 50, 100])
def test_panel_snapshot(brightness) -> None:
    """Panel values decode independently of fan power."""
    client = BreezyClient("192.0.2.1")
    client.state = "00"
    client.panel_brightness = f"{brightness:02x}"
    client.panel_backlight_mode = "01"
    client.panel_display = "02"
    state = client.snapshot()
    assert state.panel_brightness == brightness
    assert state.panel_backlight_mode == "manual"
    assert state.panel_display == "off_interval"
    assert state.is_on is False


def test_invalid_panel_values_are_unknown() -> None:
    """Out-of-range values never become usable control state."""
    client = BreezyClient("192.0.2.1")
    for value in ("00", "65", "ff"):
        client.panel_brightness = value
        assert client.snapshot().panel_brightness is None
    client.panel_backlight_mode = "02"  # Toggle is a command, not a mode.
    client.panel_display = "ff"
    assert client.snapshot().panel_backlight_mode is None
    assert client.snapshot().panel_display is None


def test_panel_protocol_frames(monkeypatch) -> None:
    """The real upstream encoder and parser handle each high-page panel row."""
    client = BreezyClient("192.0.2.1")
    calls = []
    responses = iter(["ff040032", "ff040201", "ff040702"])
    monkeypatch.setattr(client, "send", calls.append)

    def receive():
        # Header, protocol, 16-byte device ID, empty password, response function.
        return bytes.fromhex("fdfd0210" + "30" * 16 + "0006" + next(responses) + "0000")

    monkeypatch.setattr(client, "receive", receive)
    client.write_many(
        [
            ("panel_brightness", "32"),
            ("panel_backlight_mode", "manual"),
            ("panel_display", "off_interval"),
        ]
    )

    assert calls == ["03ff040032", "03ff040201", "03ff040702"]
    assert client.snapshot().panel_brightness == 50
    assert client.snapshot().panel_backlight_mode == "manual"
    assert client.snapshot().panel_display == "off_interval"


def test_optional_panel_reads_do_not_break_fan_poll(monkeypatch) -> None:
    """Failed or omitted optional data clears stale panel state only."""
    client = BreezyClient("192.0.2.1")
    client.panel_brightness = "32"
    client.panel_backlight_mode = "01"
    client.panel_display = "01"
    calls = []

    def read(function, parameter, value=""):
        calls.append(parameter)
        if parameter == client._POLL_PARAMETERS:
            client.state = "01"
            client.speed = "02"
            return True
        if parameter == "0407":
            client.panel_display = "00"
        return parameter != "0400"

    monkeypatch.setattr(client, "do_func", read)
    state = client.update_state()
    assert state.is_on is True
    assert state.percentage == 67
    assert state.panel_brightness is None
    assert state.panel_backlight_mode is None
    assert state.panel_display == "off"
    assert calls == [client._POLL_PARAMETERS, "0400", "0402", "0407"]
