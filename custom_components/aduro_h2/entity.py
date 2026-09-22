"""Common base entity for the Aduro H2 Pellet Stove integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import AduroH2Coordinator


class AduroH2Entity(CoordinatorEntity[AduroH2Coordinator]):
    """Base entity tying every platform entity to the stove device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AduroH2Coordinator, unique_id_suffix: str) -> None:
        super().__init__(coordinator)
        serial = coordinator.api.serial
        self._attr_unique_id = f"{serial}_{unique_id_suffix}"
        info = coordinator.device_info_data
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            manufacturer=MANUFACTURER,
            name=f"Aduro {info.get('type') or 'H2'} {serial}",
            model=info.get("type"),
            sw_version=info.get("version"),
            hw_version=info.get("build"),
        )
