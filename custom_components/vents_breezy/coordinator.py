"""Data coordinator for VENTS Breezy."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import BreezyClient, BreezyConnectionError, BreezyState
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class VentsBreezyCoordinator(DataUpdateCoordinator[BreezyState]):
    """Coordinate serialized access to the fan's UDP endpoint."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: BreezyClient,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=UPDATE_INTERVAL,
            always_update=False,
        )
        self.client = client
        self._device_lock = asyncio.Lock()

    async def _async_update_data(self) -> BreezyState:
        """Fetch the latest device state."""
        try:
            async with self._device_lock:
                return await self.hass.async_add_executor_job(self.client.update_state)
        except BreezyConnectionError as err:
            raise UpdateFailed(str(err)) from err

    async def async_write(self, commands: list[tuple[str, str]]) -> None:
        """Write commands, then refresh the shared state."""
        try:
            async with self._device_lock:
                await self.hass.async_add_executor_job(self.client.write_many, commands)
        except (BreezyConnectionError, ValueError) as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
            ) from err

        await self.async_request_refresh()
