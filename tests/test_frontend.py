"""Packaging checks for the optional standalone dashboard card."""

import json
from pathlib import Path


def test_frontend_card_is_standalone() -> None:
    """The card remains usable but is not packaged inside the integration."""
    root = Path(__file__).parents[1]
    integration_dir = root / "custom_components" / "vents_breezy"
    manifest = json.loads((integration_dir / "manifest.json").read_text())
    init = (integration_dir / "__init__.py").read_text()
    constants = (integration_dir / "const.py").read_text()
    card = (root / "www" / "vents-breezy-card.js").read_text()

    assert not (integration_dir / "frontend").exists()
    assert not (integration_dir / "frontend_registration.py").exists()
    assert not {"frontend", "http", "lovelace"} & set(manifest["dependencies"])
    assert "CARD_URL" not in constants
    assert "StaticPathConfig" not in init
    assert "async_register_card" not in init
    assert "customElements.define(CARD_NAME, VentsBreezyCard)" in card
