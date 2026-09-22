"""Button platform for the Aduro H2 Pellet Stove integration."""
from __future__ import annotations

from collections.abc import Callable

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import AduroH2Api, AduroH2CommandError, AduroH2ConnectionError
from .const import DOMAIN
from .coordinator import AduroH2Coordinator
from .entity import AduroH2Entity
from .exceptions import to_home_assistant_error

BUTTONS: tuple[tuple[ButtonEntityDescription, Callable[[AduroH2Api], None]], ...] = (
    (
        ButtonEntityDescription(
            key="start",
            translation_key="start",
            icon="mdi:play",
        ),
        lambda api: api.set_start_stop(True),
    ),
    (
        ButtonEntityDescription(
            key="stop",
            translation_key="stop",
            icon="mdi:stop",
        ),
        lambda api: api.set_start_stop(False),
    ),
    (
        ButtonEntityDescription(
            key="force_auger",
            translation_key="force_auger",
            icon="mdi:screw-lag",
        ),
        lambda api: api.force_auger(),
    ),
    (
        ButtonEntityDescription(
            key="reset_alarm",
            translation_key="reset_alarm",
            icon="mdi:alarm-light-off",
        ),
        lambda api: api.reset_alarm(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Aduro H2 command buttons from a config entry."""
    coordinator: AduroH2Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [AduroH2Button(coordinator, description, action) for description, action in BUTTONS]
        + [AduroH2FetchDataButton(coordinator), AduroH2ResumeAfterWoodButton(coordinator)]
    )


class AduroH2Button(AduroH2Entity, ButtonEntity):
    """Fires a one-shot command against the stove."""

    def __init__(
        self,
        coordinator: AduroH2Coordinator,
        description: ButtonEntityDescription,
        action: Callable[[AduroH2Api], None],
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._action = action

    async def async_press(self) -> None:
        try:
            await self.hass.async_add_executor_job(self._action, self.coordinator.api)
        except (AduroH2ConnectionError, AduroH2CommandError) as err:
            raise to_home_assistant_error(err) from err
        await self.coordinator.async_request_refresh()


class AduroH2FetchDataButton(AduroH2Entity, ButtonEntity):
    """Forces an immediate poll instead of waiting for the next interval."""

    _attr_translation_key = "fetch_data"
    _attr_icon = "mdi:download"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: AduroH2Coordinator) -> None:
        super().__init__(coordinator, "fetch_data")

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()


class AduroH2ResumeAfterWoodButton(AduroH2Entity, ButtonEntity):
    """Sends misc.start to resume pellet operation out of wood mode (state 9)."""

    _attr_translation_key = "resume_after_wood"
    _attr_icon = "mdi:play-circle"

    def __init__(self, coordinator: AduroH2Coordinator) -> None:
        super().__init__(coordinator, "resume_after_wood")

    async def async_press(self) -> None:
        state = self.coordinator.data.get("operating", {}).get("state")
        if state != "9":
            raise ServiceValidationError(
                "The stove isn't in wood mode right now, so there is nothing to resume from."
            )
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.api.set_start_stop, True
            )
        except (AduroH2ConnectionError, AduroH2CommandError) as err:
            raise to_home_assistant_error(err) from err
        await self.coordinator.async_request_refresh()
