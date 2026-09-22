"""Switch platform for the Aduro H2 Pellet Stove integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .api import AduroH2CommandError, AduroH2ConnectionError
from .const import (
    DOMAIN,
    FORCE_FAN_KEEPALIVE_SECONDS,
    FORCE_FAN_MAX_DURATION_SECONDS,
    FORCE_FAN_SMOKE_TEMP_CUTOFF,
    SHUTDOWN_STATES,
    STARTUP_STATES,
)
from .coordinator import AduroH2Coordinator
from .entity import AduroH2Entity
from .exceptions import to_home_assistant_error

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Aduro H2 switches from a config entry."""
    coordinator: AduroH2Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [AduroH2PowerSwitch(coordinator), AduroH2ForceFanSwitch(coordinator)]
    )


class AduroH2PowerSwitch(AduroH2Entity, SwitchEntity):
    """Starts or stops pellet feed/ignition on the stove.

    "On" is determined by the stove's `state` code being one of the
    STARTUP_STATES (e.g. igniting, operating, wood burning) rather than one
    of the SHUTDOWN_STATES (idle, stopped, various fault states) - these
    classifications are reproduced from the independent NewImproved/Aduro
    integration for the same protocol, see const.py. Falls back to
    `power_pct != 0` for any state code not in either list.
    """

    _attr_translation_key = "power"
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator: AduroH2Coordinator) -> None:
        super().__init__(coordinator, "power")

    @property
    def is_on(self) -> bool | None:
        state = self.coordinator.data.get("operating", {}).get("state")
        if state in STARTUP_STATES:
            return True
        if state in SHUTDOWN_STATES:
            return False

        power_pct = self.coordinator.data.get("operating", {}).get("power_pct")
        if power_pct is None:
            return None
        try:
            return float(power_pct) != 0
        except ValueError:
            return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set_start_stop(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set_start_stop(False)

    async def _async_set_start_stop(self, start: bool) -> None:
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.api.set_start_stop, start
            )
        except (AduroH2ConnectionError, AduroH2CommandError) as err:
            raise to_home_assistant_error(err) from err
        await self.coordinator.async_request_refresh()


class AduroH2ForceFanSwitch(AduroH2Entity, SwitchEntity):
    """Overrides the fan on via the stove's manual mode.

    The stove drops manual mode if manual.keep_alive isn't resent
    periodically, so this re-sends it every FORCE_FAN_KEEPALIVE_SECONDS while
    on. It forces itself off if either FORCE_FAN_MAX_DURATION_SECONDS elapses
    (e.g. in case Home Assistant restarts and the keep-alive loop stops
    without a clean "off"; the stove's own keep-alive timeout is a second,
    independent safety net beyond this one) or the smoke temperature exceeds
    FORCE_FAN_SMOKE_TEMP_CUTOFF.
    """

    _attr_translation_key = "force_fan"
    _attr_icon = "mdi:fan"

    def __init__(self, coordinator: AduroH2Coordinator) -> None:
        super().__init__(coordinator, "force_fan")
        self._is_on = False
        self._started_at = None
        self._unsub_keepalive = None

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self._is_on or self._started_at is None:
            return {}
        running_seconds = (dt_util.utcnow() - self._started_at).total_seconds()
        return {
            "running_seconds": int(running_seconds),
            "auto_off_after_seconds": FORCE_FAN_MAX_DURATION_SECONDS,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.api.start_force_fan
            )
        except (AduroH2ConnectionError, AduroH2CommandError) as err:
            raise to_home_assistant_error(err) from err

        self._is_on = True
        self._started_at = dt_util.utcnow()
        self._unsub_keepalive = async_track_time_interval(
            self.hass,
            self._async_keepalive_tick,
            timedelta(seconds=FORCE_FAN_KEEPALIVE_SECONDS),
        )
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_stop()

    async def async_will_remove_from_hass(self) -> None:
        self._cancel_keepalive()
        await super().async_will_remove_from_hass()

    def _cancel_keepalive(self) -> None:
        if self._unsub_keepalive is not None:
            self._unsub_keepalive()
            self._unsub_keepalive = None

    async def _async_stop(self) -> None:
        self._cancel_keepalive()
        try:
            await self.hass.async_add_executor_job(self.coordinator.api.stop_force_fan)
        finally:
            # Clear local state even if the off-command failed - staying
            # "on" in the UI when we can't confirm the stove's state helps
            # no one, and the keep-alive loop is already cancelled.
            self._is_on = False
            self._started_at = None
            self.async_write_ha_state()

    async def _async_keepalive_tick(self, now: Any = None) -> None:
        if not self._is_on or self._started_at is None:
            return

        running_seconds = (dt_util.utcnow() - self._started_at).total_seconds()
        if running_seconds >= FORCE_FAN_MAX_DURATION_SECONDS:
            _LOGGER.warning(
                "Force fan safety auto-off after %s seconds",
                FORCE_FAN_MAX_DURATION_SECONDS,
            )
            await self._async_stop()
            return

        smoke_temp = self.coordinator.data.get("operating", {}).get("smoke_temp")
        if smoke_temp is not None:
            try:
                if float(smoke_temp) > FORCE_FAN_SMOKE_TEMP_CUTOFF:
                    _LOGGER.warning(
                        "Force fan safety auto-off: smoke temp %s°C exceeds cutoff (%s°C)",
                        smoke_temp,
                        FORCE_FAN_SMOKE_TEMP_CUTOFF,
                    )
                    await self._async_stop()
                    return
            except ValueError:
                pass

        try:
            await self.hass.async_add_executor_job(
                self.coordinator.api.keep_force_fan_alive
            )
        except (AduroH2ConnectionError, AduroH2CommandError):
            _LOGGER.warning(
                "Force fan keep-alive failed, will retry on next tick", exc_info=True
            )
