"""Register the bundled VENTS Breezy dashboard card."""

from __future__ import annotations

import logging

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.lovelace.const import LOVELACE_DATA, MODE_STORAGE
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def async_register_card(hass: HomeAssistant, card_url: str) -> None:
    """Register the card as a Lovelace resource where possible."""
    lovelace_data = hass.data[LOVELACE_DATA]
    resources = lovelace_data.resources

    if (
        lovelace_data.resource_mode != MODE_STORAGE
        or not isinstance(resources, ResourceStorageCollection)
    ):
        # YAML resources cannot be modified at runtime. Extra JS keeps the card
        # automatic for those installations after a full frontend reload.
        add_extra_js_url(hass, card_url)
        return

    try:
        # This is important on releases where the resource collection is lazy:
        # touching async_items before loading could overwrite stored resources.
        await resources.async_get_info()

        base_url = card_url.partition("?")[0]
        for item in resources.async_items():
            if item.get("url", "").partition("?")[0] != base_url:
                continue
            if item.get("url") != card_url:
                await resources.async_update_item(
                    item["id"], {"res_type": "module", "url": card_url}
                )
            return

        await resources.async_create_item(
            {"res_type": "module", "url": card_url}
        )
    except Exception:  # noqa: BLE001 - UI failure must not break device setup
        _LOGGER.exception(
            "Could not add the VENTS Breezy card to Lovelace resources; "
            "falling back to frontend injection"
        )
        add_extra_js_url(hass, card_url)
