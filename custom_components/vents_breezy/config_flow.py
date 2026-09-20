"""Config flow for VENTS Breezy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .client import BreezyClient, BreezyConnectionError
from .const import DEFAULT_NAME, DEFAULT_PASSWORD, DOMAIN


@dataclass(frozen=True, slots=True)
class BreezyInfo:
    """Validated device information."""

    serial: str
    title: str


async def async_validate_input(
    hass: HomeAssistant, user_input: dict[str, Any]
) -> BreezyInfo:
    """Validate the user input by connecting to the fan."""
    client = BreezyClient(
        user_input[CONF_HOST], user_input.get(CONF_PASSWORD, DEFAULT_PASSWORD)
    )
    state = await hass.async_add_executor_job(client.initialize)
    return BreezyInfo(serial=state.serial, title=state.model or DEFAULT_NAME)


class VentsBreezyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for VENTS Breezy."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await async_validate_input(self.hass, user_input)
            except (BreezyConnectionError, OSError, ValueError):
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(info.serial)
                self._abort_if_unique_id_configured(
                    updates={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PASSWORD: user_input.get(CONF_PASSWORD, DEFAULT_PASSWORD),
                    }
                )
                return self.async_create_entry(title=info.title, data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
