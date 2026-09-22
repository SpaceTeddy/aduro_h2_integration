"""Select platform for the Aduro H2 Pellet Stove integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import AduroH2CommandError, AduroH2ConnectionError
from .const import DOMAIN, HEAT_LEVELS, OPERATION_MODES
from .coordinator import AduroH2Coordinator
from .entity import AduroH2Entity
from .exceptions import to_home_assistant_error

_POWER_TO_LEVEL = {str(power): level for level, power in HEAT_LEVELS.items()}
_MODE_VALUE_TO_NAME = {str(value): name for name, value in OPERATION_MODES.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Aduro H2 selects from a config entry."""
    coordinator: AduroH2Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [AduroH2HeatLevelSelect(coordinator), AduroH2ModeSelect(coordinator)]
    )


class AduroH2HeatLevelSelect(AduroH2Entity, SelectEntity):
    """Sets regulation.fixed_power to one of the stove's three heat levels."""

    _attr_translation_key = "heat_level"
    _attr_options = list(HEAT_LEVELS)
    _attr_icon = "mdi:fire"

    def __init__(self, coordinator: AduroH2Coordinator) -> None:
        super().__init__(coordinator, "heat_level")

    @property
    def current_option(self) -> str | None:
        fixed_power = self.coordinator.data.get("status", {}).get(
            "regulation.fixed_power"
        )
        if fixed_power is None:
            return None
        return _POWER_TO_LEVEL.get(str(fixed_power))

    async def async_select_option(self, option: str) -> None:
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.api.set_heatlevel, HEAT_LEVELS[option]
            )
        except (AduroH2ConnectionError, AduroH2CommandError) as err:
            raise to_home_assistant_error(err) from err
        await self.coordinator.async_request_refresh()


class AduroH2ModeSelect(AduroH2Entity, SelectEntity):
    """Sets regulation.operation_mode (what the stove regulates on)."""

    _attr_translation_key = "mode"
    _attr_options = list(OPERATION_MODES)
    _attr_icon = "mdi:tune"

    def __init__(self, coordinator: AduroH2Coordinator) -> None:
        super().__init__(coordinator, "mode")

    @property
    def current_option(self) -> str | None:
        mode = self.coordinator.data.get("status", {}).get("operation_mode")
        if mode is None:
            return None
        return _MODE_VALUE_TO_NAME.get(str(mode))

    async def async_select_option(self, option: str) -> None:
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.api.set_operation_mode, OPERATION_MODES[option]
            )
        except (AduroH2ConnectionError, AduroH2CommandError) as err:
            raise to_home_assistant_error(err) from err
        await self.coordinator.async_request_refresh()
