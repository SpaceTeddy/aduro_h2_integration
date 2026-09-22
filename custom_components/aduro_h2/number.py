"""Number platform for the Aduro H2 Pellet Stove integration."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import AduroH2CommandError, AduroH2ConnectionError
from .const import DOMAIN, TEMP_MAX, TEMP_MIN, TEMP_STEP
from .coordinator import AduroH2Coordinator
from .entity import AduroH2Entity
from .exceptions import to_home_assistant_error


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Aduro H2 target temperature number from a config entry."""
    coordinator: AduroH2Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AduroH2TargetTemperature(coordinator)])


class AduroH2TargetTemperature(AduroH2Entity, NumberEntity):
    """Sets boiler.temp, the room-temperature setpoint used in temperature
    regulation mode (this stove has no hydronic boiler; despite the raw
    field name it regulates room temperature - see the room_temperature
    sensor in sensor.py for the corresponding readback field and sources).

    Writing a value also switches the stove into temperature mode
    (regulation.operation_mode = 1), matching the app's behavior - the
    setpoint has no effect while the stove regulates on heat level or wood.
    """

    _attr_translation_key = "target_temperature"
    _attr_icon = "mdi:home-thermometer"
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = TEMP_MIN
    _attr_native_max_value = TEMP_MAX
    _attr_native_step = TEMP_STEP
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator: AduroH2Coordinator) -> None:
        super().__init__(coordinator, "target_temperature")

    @property
    def native_value(self) -> float | None:
        boiler_ref = self.coordinator.data.get("operating", {}).get("boiler_ref")
        if boiler_ref is None:
            return None
        try:
            return float(boiler_ref)
        except ValueError:
            return None

    async def async_set_native_value(self, value: float) -> None:
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.api.set_temperature, value
            )
        except (AduroH2ConnectionError, AduroH2CommandError) as err:
            raise to_home_assistant_error(err) from err
        await self.coordinator.async_request_refresh()
