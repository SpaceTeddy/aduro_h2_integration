"""The Aduro H2 Pellet Stove integration."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant

from .api import AduroH2Api
from .const import (
    CONF_ACTIVE_SMOKE_TEMP,
    CONF_DISCOVERY,
    CONF_PIN,
    CONF_SCAN_INTERVAL,
    CONF_SCAN_INTERVAL_OFF,
    CONF_SERIAL,
    DEFAULT_ACTIVE_SMOKE_TEMP,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL_OFF,
    DOMAIN,
)
from .coordinator import AduroH2Coordinator

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.BUTTON,
    Platform.NUMBER,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Aduro H2 from a config entry."""
    api = AduroH2Api(
        serial=entry.data[CONF_SERIAL],
        pin=entry.data[CONF_PIN],
        host=entry.data.get(CONF_HOST),
    )

    interval_on = timedelta(
        seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    interval_off = timedelta(
        seconds=entry.options.get(CONF_SCAN_INTERVAL_OFF, DEFAULT_SCAN_INTERVAL_OFF)
    )

    coordinator = AduroH2Coordinator(
        hass,
        api,
        interval_on,
        interval_off,
        entry.options.get(CONF_ACTIVE_SMOKE_TEMP, DEFAULT_ACTIVE_SMOKE_TEMP),
        device_info_data=entry.data.get(CONF_DISCOVERY) or {"serial": api.serial},
    )
    await coordinator.async_config_entry_first_refresh()

    # Persist freshly learned discovery metadata (type/version/build), e.g.
    # for entries created before this was stored, or after a rediscovery
    # found the stove on a new address, so restarts don't show "Unknown".
    if coordinator.device_info_data != entry.data.get(CONF_DISCOVERY):
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_DISCOVERY: coordinator.device_info_data}
        )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an Aduro H2 config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
