"""Binary sensor platform for the Aduro H2 Pellet Stove integration."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AduroH2Coordinator
from .entity import AduroH2Entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Aduro H2 alarm binary sensor from a config entry."""
    coordinator: AduroH2Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AduroH2AlarmBinarySensor(coordinator)])


class AduroH2AlarmBinarySensor(AduroH2Entity, BinarySensorEntity):
    """Reflects the stove's off_on_alarm status flag."""

    _attr_translation_key = "alarm"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: AduroH2Coordinator) -> None:
        super().__init__(coordinator, "alarm")

    @property
    def is_on(self) -> bool | None:
        value = self.coordinator.data.get("status", {}).get("off_on_alarm")
        if value is None:
            return None
        return value not in ("0", 0)
