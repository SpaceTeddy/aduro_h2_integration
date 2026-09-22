"""Thin synchronous wrapper around pyduro.

All calls in here are blocking (they open a UDP socket and wait for a
response), so callers must run them in an executor.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from pyduro.actions import STATUS_PARAMS, discover, raw
from pyduro.actions import set as pyduro_set

from .const import DEFAULT_CLOUD_ADDRESS

# Snapshot the parameter names once at import time. STATUS_PARAMS is a module
# level dict owned by pyduro and must not be mutated (the original script did,
# which made every consumer share the exact same dict instance).
STATUS_PARAM_KEYS: tuple[str, ...] = tuple(STATUS_PARAMS.keys())


class AduroH2Error(Exception):
    """Base error for all stove communication problems."""


class AduroH2ConnectionError(AduroH2Error):
    """Raised when the stove could not be reached or replied unexpectedly."""


class AduroH2CommandError(AduroH2Error):
    """Raised when the stove rejected a command."""


class AduroH2Api:
    """Blocking client for a single Aduro/NBE stove."""

    def __init__(self, serial: str, pin: str, host: str | None = None) -> None:
        self.serial = serial
        self.pin = pin
        self.host = host

    # -- discovery -----------------------------------------------------

    def discover(self) -> dict[str, Any]:
        """Broadcast-discover the stove and remember its address."""
        try:
            response = discover.run()
            payload = response.parse_payload()
        except Exception as err:  # pyduro raises plain/broad exceptions
            raise AduroH2ConnectionError("Stove discovery failed") from err

        if not isinstance(payload, dict) or "IP" not in payload:
            raise AduroH2ConnectionError("Stove discovery returned no data")

        ip = payload.get("IP") or ""
        if not ip or ip == "0.0.0.0":
            ip = DEFAULT_CLOUD_ADDRESS
        self.host = ip

        return {
            "serial": payload.get("Serial") or self.serial,
            "ip": ip,
            "type": payload.get("Type"),
            "version": payload.get("Ver"),
            "build": payload.get("Build"),
            "lang": payload.get("Lang"),
        }

    # -- reads -----------------------------------------------------------

    def get_status(self) -> dict[str, str]:
        """Fetch the full status frame (function 11, payload '*').

        pyduro's STATUS_PARAMS list is a reverse-engineered, best-effort
        mapping and may be shorter than what a given stove/firmware actually
        sends. Values beyond the known names are kept as "unknown_<index>"
        instead of being silently dropped by zip(), so nothing the stove
        reports is lost - useful for spotting fields pyduro doesn't name yet.
        """
        values = self._raw(11, "*").split(",")
        status = dict(zip(STATUS_PARAM_KEYS, values))
        for index in range(len(STATUS_PARAM_KEYS), len(values)):
            status[f"unknown_{index}"] = values[index]
        return status

    def get_operating(self) -> dict[str, str]:
        """Fetch the operating-data frame (function 11, payload '001*').

        The field offsets below are undocumented and were reverse engineered
        against the stove's raw NBE responses; there is no vendor spec for
        them.
        """
        data = self._raw(11, "001*").split(",")
        if len(data) < 122:
            raise AduroH2ConnectionError("Unexpected operating data length")

        timestamp = data[94]
        return {
            "boiler_temp": data[0],
            "boiler_ref": data[1],
            "substate": data[5],
            "state": data[6],
            "oxygen": data[26],
            "power_kw": data[31],
            "shaft_temp": data[35],
            "power_pct": data[36],
            "smoke_temp": data[37],
            "internet_uptime": data[38],
            "router_ssid": data[68],
            "date_stove": f"{timestamp[0:5]}/20{timestamp[6:8]}",
            "time_stove": timestamp[9:],
            "operating_time_auger": data[119],
            "operating_time_ignition": data[120],
            "operating_time_stove": data[121],
        }

    def get_consumption(self) -> dict[str, str]:
        """Fetch today/yesterday/month/year pellet consumption."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Each response is "<prefix>=<comma separated values>"; the prefix
        # length is fixed per function so it can be sliced off directly.
        days = self._raw(6, "total_days")[len("total_days="):].split(",")
        months = self._raw(6, "total_months")[len("total_months="):].split(",")
        years = self._raw(6, "total_years")[len("total_years="):].split(",")

        return {
            "today": days[today.day - 1],
            "yesterday": days[yesterday.day - 1],
            "month": months[today.month - 1],
            "year": years[-1],
        }

    def get_network(self) -> dict[str, str]:
        """Fetch WiFi/network info (function 1, path 'wifi.router')."""
        data = self._raw(1, "wifi.router").split(",")
        if len(data) < 10:
            raise AduroH2ConnectionError("Unexpected network data length")

        return {
            "ssid": data[0][len("router="):],
            "stove_ip": data[4],
            "router_ip": data[5],
            "rssi": data[6],
            "mac": data[9],
        }

    # -- commands ----------------------------------------------------------

    def set_heatlevel(self, fixed_power: int) -> None:
        # The stove only applies regulation.fixed_power while it's actually
        # regulating on heat level; switch it back to that mode first, or the
        # value is silently ignored while in temperature/wood mode.
        self._set("regulation.operation_mode", 0)
        self._set("regulation.fixed_power", fixed_power)

    def set_temperature(self, temperature: float) -> None:
        # Same as set_heatlevel: the target only takes effect in temperature
        # regulation mode, so switch to it first.
        self._set("regulation.operation_mode", 1)
        self._set("boiler.temp", temperature)

    def set_operation_mode(self, mode: int) -> None:
        self._set("regulation.operation_mode", mode)

    def set_start_stop(self, start: bool) -> None:
        self._set("misc.start" if start else "misc.stop", 1)

    def force_auger(self) -> None:
        self._set("auger.forced_run", 1)

    def reset_alarm(self) -> None:
        self._set("misc.reset_alarm", 1)

    def start_force_fan(self) -> None:
        self._set("manual.manual_mode", 1)
        self._set("manual.output_std", 2)

    def keep_force_fan_alive(self) -> None:
        # The stove drops manual mode if this isn't resent periodically.
        self._set("manual.keep_alive", 1)

    def stop_force_fan(self) -> None:
        self._set("manual.manual_mode", 0)

    # -- internals -----------------------------------------------------

    def _raw(self, function_id: int, payload: str) -> str:
        if not self.host:
            raise AduroH2ConnectionError("No stove address known; discover() first")
        try:
            response = raw.run(
                burner_address=self.host,
                serial=self.serial,
                pin_code=self.pin,
                function_id=function_id,
                payload=payload,
            )
        except Exception as err:
            raise AduroH2ConnectionError(f"Communication with stove failed: {err}") from err
        if response is None:
            raise AduroH2ConnectionError("No response from stove")
        return response.payload

    def _set(self, path: str, value: Any) -> None:
        if not self.host:
            raise AduroH2ConnectionError("No stove address known; discover() first")
        try:
            response = pyduro_set.run(
                burner_address=self.host,
                serial=self.serial,
                pin_code=self.pin,
                path=path,
                value=value,
            )
        except Exception as err:
            raise AduroH2ConnectionError(f"Communication with stove failed: {err}") from err
        if response is None:
            raise AduroH2ConnectionError("No response from stove")

        result = response.parse_payload()
        if result not in ("", None):
            raise AduroH2CommandError(f"Stove rejected '{path}={value}': {result}")
