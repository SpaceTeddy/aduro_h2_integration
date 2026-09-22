"""Config flow for the Aduro H2 Pellet Stove integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .api import AduroH2Api, AduroH2ConnectionError
from .const import (
    CONF_DISCOVERY,
    CONF_PIN,
    CONF_SCAN_INTERVAL,
    CONF_SERIAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_HOST): str,
        vol.Required(CONF_SERIAL): str,
        vol.Required(CONF_PIN): str,
    }
)


class AduroH2ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for a single Aduro H2 stove."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            api = AduroH2Api(
                serial=user_input[CONF_SERIAL].strip(),
                pin=user_input[CONF_PIN].strip(),
                host=(user_input.get(CONF_HOST) or "").strip() or None,
            )
            try:
                discovery = await self.hass.async_add_executor_job(
                    self._validate, api
                )
            except AduroH2ConnectionError:
                _LOGGER.debug("Validation failed for %s", api.serial, exc_info=True)
                errors["base"] = "cannot_connect"
            else:
                serial = discovery.get("serial") or api.serial

                await self.async_set_unique_id(serial)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Aduro H2 ({serial})",
                    data={
                        CONF_HOST: api.host,
                        CONF_SERIAL: serial,
                        CONF_PIN: user_input[CONF_PIN].strip(),
                        CONF_DISCOVERY: discovery,
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    @staticmethod
    def _validate(api: AduroH2Api) -> dict[str, Any]:
        """Discover (if possible) and confirm serial/pin work, in an executor."""
        manual_host = api.host
        discovery: dict[str, Any] = {"serial": api.serial}
        try:
            discovery = api.discover()
        except AduroH2ConnectionError:
            # Broadcast discovery doesn't cross subnets/VLANs, so a manually
            # entered host is expected to fail discovery; only fatal if the
            # user didn't give us an address to fall back on.
            if not manual_host:
                raise
        if manual_host:
            api.host = manual_host

        # Raises AduroH2ConnectionError if the serial/pin/host combination
        # doesn't get a valid reply from the stove.
        api.get_status()
        return discovery

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> AduroH2OptionsFlow:
        return AduroH2OptionsFlow()


class AduroH2OptionsFlow(config_entries.OptionsFlow):
    """Lets the user change the polling interval after setup.

    `config_entry` is a read-only property inherited from OptionsFlow (it's
    resolved from `self.handler`, which the flow manager sets); assigning it
    ourselves in __init__ raises AttributeError on current HA versions.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): vol.All(
                    vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
