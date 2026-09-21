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
