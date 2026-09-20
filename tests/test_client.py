"""Tests for the Breezy protocol adapter."""

import sys
from pathlib import Path
from types import ModuleType

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
