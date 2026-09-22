"""DataUpdateCoordinator for the Aduro H2 Pellet Stove integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AduroH2Api, AduroH2ConnectionError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class AduroH2Coordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls a single Aduro H2 stove and exposes its data to entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: AduroH2Api,
        update_interval: timedelta,
        device_info_data: dict[str, Any],
    ) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)
        self.api = api
        self.device_info_data = device_info_data

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.hass.async_add_executor_job(self._poll)
        except AduroH2ConnectionError as err:
            raise UpdateFailed(str(err)) from err

    def _poll(self) -> dict[str, Any]:
        if not self.api.host:
            self.device_info_data = self.api.discover()
        elif not self.device_info_data.get("version"):
            # Host is known (manual or persisted) but we never learned the
            # stove's type/version/build, e.g. an entry created before this
            # was persisted. Try once to fill it in without disturbing the
            # working host if broadcast discovery can't reach the stove.
            self._try_refresh_discovery_metadata()

        try:
            return self._fetch_all()
        except AduroH2ConnectionError:
            _LOGGER.debug("Communication with stove failed, rediscovering")
            self.device_info_data = self.api.discover()
            return self._fetch_all()

    def _try_refresh_discovery_metadata(self) -> None:
        manual_host = self.api.host
        try:
            self.device_info_data = self.api.discover()
        except AduroH2ConnectionError:
            _LOGGER.debug(
                "Could not refresh discovery metadata (broadcast likely can't "
                "reach the stove); keeping the configured host"
            )
        finally:
            self.api.host = manual_host

    def _fetch_all(self) -> dict[str, Any]:
        return {
            "status": self.api.get_status(),
            "operating": self.api.get_operating(),
            "consumption": self.api.get_consumption(),
            "network": self.api.get_network(),
            "discovery": self.device_info_data,
        }
