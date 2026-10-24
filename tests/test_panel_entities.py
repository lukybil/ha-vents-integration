"""Panel entity command tests with lightweight Home Assistant stand-ins."""

import asyncio
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def platforms(monkeypatch):
    """Load entity platforms without requiring a Home Assistant installation."""
    package_name = "custom_components.vents_breezy"
    root = Path(__file__).parents[1] / "custom_components" / "vents_breezy"
    package = sys.modules.get(package_name)
    if package is None:
        package = ModuleType(package_name)
        package.__path__ = [str(root)]
        monkeypatch.setitem(sys.modules, package_name, package)
    monkeypatch.setattr(package, "VentsBreezyConfigEntry", object, raising=False)

    class BaseEntity:
        def __init__(self, coordinator):
            self.coordinator = coordinator

    class SelectEntity:
        @property
        def options(self):
            return self._attr_options

    dependencies = {
        "homeassistant.components.number": {
            "NumberEntity": type("NumberEntity", (), {}),
            "NumberMode": SimpleNamespace(SLIDER="slider"),
        },
        "homeassistant.components.select": {"SelectEntity": SelectEntity},
        "homeassistant.const": {
            "PERCENTAGE": "%",
            "EntityCategory": SimpleNamespace(CONFIG="config"),
        },
        "homeassistant.helpers.entity_platform": {
            "AddConfigEntryEntitiesCallback": object,
        },
        f"{package_name}.entity": {"VentsBreezyEntity": BaseEntity},
        f"{package_name}.coordinator": {"VentsBreezyCoordinator": object},
    }
    for name, attributes in dependencies.items():
        module = ModuleType(name)
        module.__dict__.update(attributes)
        monkeypatch.setitem(sys.modules, name, module)

    modules = []
    for platform in ("number", "select"):
        spec = importlib.util.spec_from_file_location(
            f"{package_name}.{platform}", root / f"{platform}.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules.append(module)
    return modules


def test_panel_entity_setup_and_commands(platforms):
    """Panel controls register and leave ventilation and schedules alone."""
    number, select = platforms
    coordinator = SimpleNamespace(
        data=SimpleNamespace(
            serial="BREEZY123",
            panel_brightness=50,
            panel_backlight_mode="auto",
            panel_display="off_interval",
        ),
        async_write=AsyncMock(),
    )
    entry = SimpleNamespace(runtime_data=SimpleNamespace(coordinator=coordinator))
    entities = []
    asyncio.run(number.async_setup_entry(None, entry, entities.extend))
    asyncio.run(select.async_setup_entry(None, entry, entities.extend))
    assert len(entities) == 4  # Brightness, airflow, backlight, display.
    brightness, _, backlight, display = entities
    assert brightness.native_value == 50
    assert backlight.current_option == "auto"
    assert display.current_option == "off_interval"
    assert len({entity._attr_unique_id for entity in entities}) == 4

    for value, encoded in ((1, "01"), (50, "32"), (100, "64")):
        asyncio.run(brightness.async_set_native_value(value))
        coordinator.async_write.assert_awaited_with(
            [("panel_brightness", encoded), ("panel_backlight_mode", "manual")]
        )
    for entity, parameter, option in (
        (backlight, "panel_backlight_mode", "auto"),
        (display, "panel_display", "off"),
        (display, "panel_display", "on"),
        (display, "panel_display", "off_interval"),
    ):
        asyncio.run(entity.async_select_option(option))
        coordinator.async_write.assert_awaited_with([(parameter, option)])

    coordinator.async_write.reset_mock()
    for invalid in (0, 101, 25.5, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            asyncio.run(brightness.async_set_native_value(invalid))
    with pytest.raises(ValueError):
        asyncio.run(backlight.async_select_option("toggle"))
    with pytest.raises(ValueError):
        asyncio.run(display.async_select_option("invalid"))
    coordinator.async_write.assert_not_awaited()

    coordinator.data.panel_brightness = None
    coordinator.data.panel_backlight_mode = None
    coordinator.data.panel_display = None
    assert brightness.native_value is None
    assert backlight.current_option is None
    assert display.current_option is None
