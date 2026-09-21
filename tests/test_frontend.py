"""Packaging checks for the bundled dashboard card."""

import json
import re
from pathlib import Path


def test_frontend_bundle_is_packaged_and_versioned() -> None:
    """The resource URL, manifest, and browser bundle use one version."""
    integration_dir = (
        Path(__file__).parents[1] / "custom_components" / "vents_breezy"
    )
    manifest = json.loads((integration_dir / "manifest.json").read_text())
    constants = (integration_dir / "const.py").read_text()
    card = (integration_dir / "frontend" / "vents-breezy-card.js").read_text()

    version_match = re.search(r'^CARD_VERSION = "([^"]+)"$', constants, re.MULTILINE)

    assert version_match is not None
    assert version_match.group(1) == manifest["version"]
    assert f" {manifest['version']} " in card
    assert {"frontend", "http", "lovelace"} <= set(manifest["dependencies"])
    assert "customElements.define(CARD_NAME, VentsBreezyCard)" in card


def test_frontend_registration_avoids_the_startup_race() -> None:
    """The live module is registered before a legacy resource is inspected."""
    integration_dir = (
        Path(__file__).parents[1] / "custom_components" / "vents_breezy"
    )
    registration = (integration_dir / "frontend_registration.py").read_text()

    live_registration = "add_extra_js_url(hass, card_url)"
    legacy_resource_load = "await resources.async_get_info()"

    assert live_registration in registration
    assert legacy_resource_load in registration
    assert registration.index(live_registration) < registration.index(
        legacy_resource_load
    )
    assert 'await resources.async_delete_item(item["id"])' in registration
    assert "async_create_item" not in registration
