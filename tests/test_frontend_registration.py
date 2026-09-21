"""Execute registration against a lazy resource collection, without HA installed."""

import asyncio
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

CARD_URL = "/vents_breezy/vents-breezy-card.js?v=0.2.3"
OLD_URL = "/vents_breezy/vents-breezy-card.js?v=0.2.1"


class Resources:
    """Model HA's lazy read and res_type-write/type-read resource interface."""

    def __init__(self, items=()):
        self.items = [dict(item) for item in items]
        self.loaded = False
        self.writes = []
        self.fail = False

    async def async_get_info(self):
        if self.fail:
            raise OSError("Resource storage unavailable")
        self.loaded = True

    def async_items(self):
        assert self.loaded, "Resources must be loaded before inspection"
        return list(self.items)

    async def async_create_item(self, data):
        assert self.loaded
        self.writes.append("create")
        self.items.append(
            {"id": "new", "url": data["url"], "type": data["res_type"]}
        )

    async def async_update_item(self, item_id, data):
        self.writes.append("update")
        item = next(item for item in self.items if item["id"] == item_id)
        item.update(url=data["url"], type=data["res_type"])

    async def async_delete_item(self, item_id):
        self.writes.append("delete")
        self.items = [item for item in self.items if item["id"] != item_id]


@pytest.fixture
def register(monkeypatch):
    """Scope HA stand-ins to this test; import the real registration function."""
    exports = {
        "homeassistant": {},
        "homeassistant.components": {},
        "homeassistant.components.frontend": {
            "add_extra_js_url": lambda hass, url: hass.extra_urls.add(url)
        },
        "homeassistant.components.lovelace": {},
        "homeassistant.components.lovelace.const": {
            "LOVELACE_DATA": "lovelace",
            "MODE_STORAGE": "storage",
        },
        "homeassistant.components.lovelace.resources": {
            "ResourceStorageCollection": Resources
        },
        "homeassistant.core": {"HomeAssistant": SimpleNamespace},
    }
    for name, attrs in exports.items():
        module = ModuleType(name)
        module.__dict__.update(attrs)
        monkeypatch.setitem(sys.modules, name, module)
    path = (
        Path(__file__).parents[1]
        / "custom_components/vents_breezy/frontend_registration.py"
    )
    spec = importlib.util.spec_from_file_location("card_registration_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.async_register_card


def make_hass(resources, mode="storage"):
    return SimpleNamespace(
        data={"lovelace": SimpleNamespace(resources=resources, resource_mode=mode)},
        extra_urls=set(),
    )


def test_missing_resource_restored_and_retained_across_restart(register):
    """0.2.2's empty list must become a persistent module, with no repeated writes."""
    resources = Resources()
    hass = make_hass(resources)
    asyncio.run(register(hass, CARD_URL))
    assert hass.extra_urls == {CARD_URL}
    assert resources.items == [{"id": "new", "url": CARD_URL, "type": "module"}]

    restarted = Resources(resources.items)
    asyncio.run(register(make_hass(restarted), CARD_URL))
    assert restarted.items == resources.items
    assert restarted.writes == []


@pytest.mark.parametrize("url", [OLD_URL, CARD_URL])
@pytest.mark.parametrize("resource_type", ["js", "css", "module"])
def test_upgrade_repairs_version_and_type(register, url, resource_type):
    resources = Resources([{"id": "card", "url": url, "type": resource_type}])
    asyncio.run(register(make_hass(resources), CARD_URL))
    assert resources.items == [{"id": "card", "url": CARD_URL, "type": "module"}]


def test_duplicates_removed_after_repair_and_other_resources_preserved(register):
    other = {"id": "other", "url": "/local/other-card.js", "type": "module"}
    resources = Resources([
        {"id": "old", "url": OLD_URL, "type": "js"},
        other,
        {"id": "duplicate", "url": CARD_URL, "type": "module"},
    ])
    asyncio.run(register(make_hass(resources), CARD_URL))
    assert resources.items == [
        {"id": "old", "url": CARD_URL, "type": "module"}, other
    ]
    assert resources.writes == ["update", "delete"]


def test_yaml_resources_left_untouched(register):
    resources = Resources([{"url": OLD_URL, "type": "module"}])
    hass = make_hass(resources, mode="yaml")
    asyncio.run(register(hass, CARD_URL))
    assert hass.extra_urls == {CARD_URL}
    assert not resources.loaded
    assert resources.writes == []


def test_storage_failure_keeps_global_fallback_and_logs_action(register, caplog):
    resources = Resources()
    resources.fail = True
    hass = make_hass(resources)
    asyncio.run(register(hass, CARD_URL))
    assert hass.extra_urls == {CARD_URL}
    assert CARD_URL in caplog.text
    assert "JavaScript module" in caplog.text
