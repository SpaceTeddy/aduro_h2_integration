"""Sensor platform for the Aduro H2 Pellet Stove integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, STATE_NAMES, SUBSTATE_NAMES, SUBSTATE_NAMES_BY_STATE
from .coordinator import AduroH2Coordinator
from .entity import AduroH2Entity


@dataclass(frozen=True, kw_only=True)
class AduroH2SensorDescription(SensorEntityDescription):
    """Describes an Aduro H2 sensor and how to read it from coordinator data."""

    group: str
    field: str
    attributes_field: str | None = None


SENSOR_DESCRIPTIONS: tuple[AduroH2SensorDescription, ...] = (
    # -- operating data ---------------------------------------------------
    AduroH2SensorDescription(
        # Despite the raw field name, this is room temperature, not boiler
        # water temperature - confirmed against the independent
        # NewImproved/Aduro integration (its own sensor docstring and its
        # German translation both label boiler_temp "Raumtemperatur"/room
        # temperature, and boiler_ref "Solltemperatur"/setpoint). This stove
        # has no hydronic boiler; it reuses the NBE protocol's boiler fields
        # for the room-temperature regulation loop (see the Mode select).
        key="room_temperature",
        translation_key="room_temperature",
        group="operating",
        field="boiler_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:home-thermometer-outline",
    ),
    AduroH2SensorDescription(
        key="shaft_temp",
        translation_key="shaft_temp",
        group="operating",
        field="shaft_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AduroH2SensorDescription(
        key="smoke_temp",
        translation_key="smoke_temp",
        group="operating",
        field="smoke_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AduroH2SensorDescription(
        key="power_kw",
        translation_key="power_kw",
        group="operating",
        field="power_kw",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AduroH2SensorDescription(
        key="power_pct",
        translation_key="power_pct",
        group="operating",
        field="power_pct",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fire",
    ),
    AduroH2SensorDescription(
        key="state",
        translation_key="state",
        group="operating",
        field="state",
        icon="mdi:state-machine",
    ),
    AduroH2SensorDescription(
        key="substate",
        translation_key="substate",
        group="operating",
        field="substate",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:state-machine",
    ),
    AduroH2SensorDescription(
        key="substate_remaining",
        translation_key="substate_remaining",
        group="status",
        field="substate_sec",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:timer-sand",
    ),
    AduroH2SensorDescription(
        key="operation_mode",
        translation_key="operation_mode",
        group="status",
        field="operation_mode",
        icon="mdi:tune",
    ),
    AduroH2SensorDescription(
        key="last_alarm",
        translation_key="last_alarm",
        group="status",
        field="off_on_alarm",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alarm-light-outline",
    ),
    AduroH2SensorDescription(
        key="oxygen",
        translation_key="oxygen",
        group="operating",
        field="oxygen",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:molecule",
    ),
    AduroH2SensorDescription(
        key="heatlevel_raw",
        translation_key="heatlevel_raw",
        group="status",
        field="regulation.fixed_power",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:fire",
    ),
    AduroH2SensorDescription(
        key="operating_time_stove",
        translation_key="operating_time_stove",
        group="operating",
        field="operating_time_stove",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    AduroH2SensorDescription(
        key="operating_time_auger",
        translation_key="operating_time_auger",
        group="operating",
        field="operating_time_auger",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    AduroH2SensorDescription(
        key="operating_time_ignition",
        translation_key="operating_time_ignition",
        group="operating",
        field="operating_time_ignition",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # -- consumption --------------------------------------------------------
    AduroH2SensorDescription(
        key="consumption_today",
        translation_key="consumption_today",
        group="consumption",
        field="today",
        native_unit_of_measurement="kg",
        state_class=SensorStateClass.TOTAL,
        icon="mdi:basket-fill",
    ),
    AduroH2SensorDescription(
        key="consumption_yesterday",
        translation_key="consumption_yesterday",
        group="consumption",
        field="yesterday",
        native_unit_of_measurement="kg",
        state_class=SensorStateClass.TOTAL,
        icon="mdi:basket-outline",
    ),
    AduroH2SensorDescription(
        key="consumption_month",
        translation_key="consumption_month",
        group="consumption",
        field="month",
        native_unit_of_measurement="kg",
        state_class=SensorStateClass.TOTAL,
        icon="mdi:basket-fill",
    ),
    AduroH2SensorDescription(
        key="consumption_year",
        translation_key="consumption_year",
        group="consumption",
        field="year",
        native_unit_of_measurement="kg",
        state_class=SensorStateClass.TOTAL,
        icon="mdi:basket-fill",
    ),
    # -- network --------------------------------------------------------
    AduroH2SensorDescription(
        key="rssi",
        translation_key="rssi",
        group="network",
        field="rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    AduroH2SensorDescription(
        key="stove_ip",
        translation_key="stove_ip",
        group="network",
        field="stove_ip",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:ip-network",
    ),
    AduroH2SensorDescription(
        key="router_ssid",
        translation_key="router_ssid",
        group="network",
        field="ssid",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:wifi",
    ),
    AduroH2SensorDescription(
        key="mac_address",
        translation_key="mac_address",
        group="network",
        field="mac",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:network-outline",
    ),
    # -- discovery / meta --------------------------------------------------
    AduroH2SensorDescription(
        key="stove_serial",
        translation_key="stove_serial",
        group="discovery",
        field="serial",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:identifier",
    ),
    AduroH2SensorDescription(
        key="nbe_type",
        translation_key="nbe_type",
        group="discovery",
        field="type",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:stove",
    ),
    AduroH2SensorDescription(
        key="sw_version",
        translation_key="sw_version",
        group="discovery",
        field="version",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chip",
    ),
    AduroH2SensorDescription(
        key="sw_build",
        translation_key="sw_build",
        group="discovery",
        field="build",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:wrench-outline",
    ),
    # -- full raw status, for templates/power users ----------------------
    AduroH2SensorDescription(
        key="raw_status",
        translation_key="raw_status",
        group="status",
        field="state",
        attributes_field="__all__",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:code-json",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Aduro H2 sensors from a config entry."""
    coordinator: AduroH2Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AduroH2Sensor(coordinator, description) for description in SENSOR_DESCRIPTIONS
    )


class AduroH2Sensor(AduroH2Entity, SensorEntity):
    """A single value read from one of the stove's data groups."""

    entity_description: AduroH2SensorDescription

    def __init__(
        self, coordinator: AduroH2Coordinator, description: AduroH2SensorDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        group = self.coordinator.data.get(self.entity_description.group, {})
        return group.get(self.entity_description.field)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attributes_field == "__all__":
            return dict(self.coordinator.data.get(self.entity_description.group, {}))

        if self.entity_description.key == "state":
            state = self.native_value
            if state is None:
                return None
            return {"description": STATE_NAMES.get(str(state), "Unknown")}

        if self.entity_description.key == "substate":
            state = self.coordinator.data.get("operating", {}).get("state")
            substate = self.native_value
            if substate is None:
                return None
            combined = SUBSTATE_NAMES_BY_STATE.get(f"{state}_{substate}")
            description = combined or SUBSTATE_NAMES.get(str(substate), "Unknown")
            return {"description": description}

        return None
