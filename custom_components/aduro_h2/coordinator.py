"""DataUpdateCoordinator for the Aduro H2 Pellet Stove integration."""
from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AduroH2Api, AduroH2ConnectionError
from .const import (
    DOMAIN,
    SHUTDOWN_STATES,
    SLOW_DATA_REFRESH_SECONDS,
    STARTUP_STATES,
    WOOD_STATES,
)

_LOGGER = logging.getLogger(__name__)


def stove_is_on(operating: dict[str, Any]) -> bool | None:
    """Whether the stove is running, from its operating data.

    Uses the STARTUP_STATES / SHUTDOWN_STATES classification of the `state`
    code, falling back to `power_pct != 0` for any state code in neither.
    Returns None if neither is conclusive.
    """
    state = operating.get("state")
    if state in STARTUP_STATES:
        return True
    if state in SHUTDOWN_STATES:
        return False

    power_pct = operating.get("power_pct")
    if power_pct is None:
        return None
    try:
        return float(power_pct) != 0
    except ValueError:
        return None


def stove_is_active(operating: dict[str, Any], smoke_temp_threshold: float) -> bool | None:
    """Whether the stove is burning, for choosing the poll interval.

    Smoke temperature at or above `smoke_temp_threshold` always counts as
    burning (a wood fire, or a stove still hot after shutdown). In wood mode
    (WOOD_STATES) the state code stays the same while the fire burns down,
    so below the threshold it counts as not burning. Otherwise falls back to
    stove_is_on(). Returns None if nothing is conclusive.
    """
    try:
        smoke_temp = float(operating["smoke_temp"])
    except (KeyError, TypeError, ValueError):
        smoke_temp = None

    if smoke_temp is not None and smoke_temp >= smoke_temp_threshold:
        return True
    if operating.get("state") in WOOD_STATES:
        return False if smoke_temp is not None else None
    return stove_is_on(operating)


class AduroH2Coordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls a single Aduro H2 stove and exposes its data to entities.

    The poll interval follows the stove's state (see stove_is_active):
    `interval_on` while it is burning (or that is unknown), `interval_off`
    while it is not. It
    also stays at `interval_on` while fast polling is requested, e.g. by the
    force fan switch whose smoke temperature safety check needs fresh data,
    or right after a start command before the stove reports running.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        api: AduroH2Api,
        interval_on: timedelta,
        interval_off: timedelta,
        active_smoke_temp: float,
        device_info_data: dict[str, Any],
    ) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=interval_on)
        self.api = api
        self.device_info_data = device_info_data
        self.interval_on = interval_on
        self.interval_off = interval_off
        self.active_smoke_temp = active_smoke_temp
        self.fast_polling = False
        self._fast_polls_remaining = 0
        self._slow_data: dict[str, Any] = {}
        self._slow_data_fetched_at: float | None = None

    def request_fast_polls(self, count: int = 1) -> None:
        """Poll at `interval_on` for the next `count` cycles regardless of state."""
        self._fast_polls_remaining = max(self._fast_polls_remaining, count)

    def invalidate_slow_data(self) -> None:
        """Re-fetch consumption/network data on the next poll."""
        self._slow_data_fetched_at = None

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self.hass.async_add_executor_job(self._poll)
        except AduroH2ConnectionError as err:
            raise UpdateFailed(str(err)) from err

        self._update_poll_interval(data)
        return data

    def _update_poll_interval(self, data: dict[str, Any]) -> None:
        if self._fast_polls_remaining > 0:
            self._fast_polls_remaining -= 1
            interval = self.interval_on
        elif self.fast_polling:
            interval = self.interval_on
        elif stove_is_active(data.get("operating", {}), self.active_smoke_temp) is False:
            interval = self.interval_off
        else:
            interval = self.interval_on

        if interval != self.update_interval:
            _LOGGER.debug("Switching poll interval to %s", interval)
            self.update_interval = interval

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
        data = {
            "status": self.api.get_status(),
            "operating": self.api.get_operating(),
        }
        now = time.monotonic()
        if (
            self._slow_data_fetched_at is None
            or now - self._slow_data_fetched_at >= SLOW_DATA_REFRESH_SECONDS
        ):
            self._slow_data = {
                "consumption": self.api.get_consumption(),
                "network": self.api.get_network(),
            }
            self._slow_data_fetched_at = now
        return {**data, **self._slow_data, "discovery": self.device_info_data}
