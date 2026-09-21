"""Register the bundled VENTS Breezy dashboard card."""

from __future__ import annotations

import logging

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.lovelace.const import LOVELACE_DATA, MODE_STORAGE
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def async_register_card(hass: HomeAssistant, card_url: str) -> None:
    """Register the card and remove the legacy persisted resource.

    Persisted Lovelace resources are loaded before custom integrations finish
    setting up. That lets the browser request the card before its static HTTP
    route exists, leaving the custom element undefined for the whole page
    session. Frontend module registration happens after the route is ready and
    also notifies already-open frontends.
    """
    add_extra_js_url(hass, card_url)

    lovelace_data = hass.data[LOVELACE_DATA]
    resources = lovelace_data.resources

    if (
        lovelace_data.resource_mode != MODE_STORAGE
        or not isinstance(resources, ResourceStorageCollection)
    ):
        return

    try:
        # Version 0.2.1 automatically created this resource. Remove it so future
        # startups cannot race the integration's static-path registration.
        await resources.async_get_info()

        base_url = card_url.partition("?")[0]
        legacy_items = [
            item
            for item in resources.async_items()
            if item.get("url", "").partition("?")[0] == base_url
        ]
        for item in legacy_items:
            await resources.async_delete_item(item["id"])
    except Exception:  # noqa: BLE001 - cleanup must not break device setup
        _LOGGER.exception(
            "Could not remove the legacy VENTS Breezy Lovelace resource; "
            "the card is still registered through the frontend"
        )
