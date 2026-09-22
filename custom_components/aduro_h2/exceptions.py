"""Translate api.py errors into Home Assistant exceptions for the UI."""
from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError

from .api import AduroH2CommandError, AduroH2ConnectionError, AduroH2Error


def to_home_assistant_error(err: AduroH2Error) -> HomeAssistantError:
    """Wrap an AduroH2Error so it surfaces as a readable HA error/notification."""
    if isinstance(err, AduroH2ConnectionError):
        return HomeAssistantError(f"Could not reach the stove: {err}")
    if isinstance(err, AduroH2CommandError):
        return HomeAssistantError(f"Stove rejected the command: {err}")
    return HomeAssistantError(str(err))
