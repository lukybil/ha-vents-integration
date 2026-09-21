"""Register the bundled VENTS Breezy dashboard card."""

from __future__ import annotations

import logging

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.lovelace.const import LOVELACE_DATA, MODE_STORAGE
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def async_register_card(hass: HomeAssistant, card_url: str) -> None:
    """Register both the frontend module and the persistent dashboard resource.

    Extra modules are embedded in the initial HTML; they do not reliably reach
    a frontend that already loaded that document. Lovelace fetches its resource
    list separately, so keep a resource there even when extra JS is registered.
    The caller must register the static route before publishing either URL.
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
        # Load first: the collection is lazy, and inspecting it before loading
        # can miss existing entries. This also restores resources removed by 0.2.2.
        await resources.async_get_info()

        base_url = card_url.partition("?")[0]
        card_items = [
            item
            for item in resources.async_items()
            if item.get("url", "").partition("?")[0] == base_url
        ]
        if card_items:
            item = card_items[0]
            if item.get("url") != card_url or item.get("type") != "module":
                await resources.async_update_item(
                    item["id"], {"res_type": "module", "url": card_url}
                )
        else:
            await resources.async_create_item({"res_type": "module", "url": card_url})

        # Only remove duplicates after a valid module resource is in place.
        for item in card_items[1:]:
            await resources.async_delete_item(item["id"])
    except Exception:  # noqa: BLE001 - card registration must not break device setup
        _LOGGER.exception(
            "Could not register the VENTS Breezy Lovelace resource. "
            "The frontend module is registered, but dashboard loading may fail. "
            "Add %s as a JavaScript module in dashboard resources",
            card_url,
        )
