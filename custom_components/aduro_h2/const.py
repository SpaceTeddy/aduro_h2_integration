"""Constants for the Aduro H2 Pellet Stove integration."""
from __future__ import annotations

DOMAIN = "aduro_h2"
MANUFACTURER = "Aduro"

CONF_SERIAL = "serial"
CONF_PIN = "pin"
# Polling interval while the stove is running. Keeps the original
# "scan_interval" key so existing option entries carry over unchanged.
CONF_SCAN_INTERVAL = "scan_interval"
# Polling interval while the stove is off/stopped.
CONF_SCAN_INTERVAL_OFF = "scan_interval_off"

# Stores the dict returned by AduroH2Api.discover() (serial/ip/type/version/
# build/lang) in the config entry, so device info survives restarts without
# needing a fresh broadcast discovery every time.
CONF_DISCOVERY = "discovery"

DEFAULT_SCAN_INTERVAL = 60
DEFAULT_SCAN_INTERVAL_OFF = 300
MIN_SCAN_INTERVAL = 20
MAX_SCAN_INTERVAL = 600
MAX_SCAN_INTERVAL_OFF = 3600

# Fallback address used by the official Aduro/NBE app when the stove is not
# reachable on the local network (e.g. it lost its DHCP lease).
DEFAULT_CLOUD_ADDRESS = "apprelay20.stokercloud.dk"

# regulation.fixed_power values accepted by the stove for the three heat levels
# exposed by the original script/app.
HEAT_LEVELS: dict[str, int] = {"low": 10, "medium": 50, "high": 100}

# regulation.operation_mode values: which quantity the stove is regulating on.
OPERATION_MODES: dict[str, int] = {"heat_level": 0, "temperature": 1, "wood": 2}

TEMP_MIN = 5
TEMP_MAX = 35
TEMP_STEP = 1

# How long a forced fan override (manual.manual_mode) is allowed to run
# before it's automatically cancelled, so a missed "off" (e.g. HA restart)
# can't leave the stove stuck out of automatic control indefinitely.
FORCE_FAN_MAX_DURATION_SECONDS = 600
# The stove drops a manual-mode command if it isn't refreshed periodically.
FORCE_FAN_KEEPALIVE_SECONDS = 20
# Auto-off if smoke temperature exceeds this while forcing the fan (from the
# same NewImproved/Aduro reference used for the state tables below).
FORCE_FAN_SMOKE_TEMP_CUTOFF = 320

# The following state/substate code tables, and the STARTUP_STATES /
# SHUTDOWN_STATES classification, are not documented by the vendor. They are
# reproduced (with attribution) from the independent, reverse-engineered
# NewImproved/Aduro Home Assistant integration for the same NBE protocol
# family: https://github.com/NewImproved/Aduro (custom_components/aduro/const.py)
STATE_NAMES: dict[str, str] = {
    "0": "Operating",
    "2": "Operating (startup)",
    "4": "Operating (startup)",
    "5": "Operating",
    "6": "Stopped",
    "9": "Stopped (wood burning)",
    "11": "Stopped (dropshaft hot)",
    "13": "Stopped (failed ignition)",
    "14": "Off",
    "15": "Stopped (bad smoke sensor)",
    "17": "Stopped (bad dropshaft sensor)",
    "18": "Stopped (check burner yellow)",
    "19": "Stopped (bad external auger output)",
    "20": "Stopped (no fuel)",
    "23": "Stopped (by timer)",
    "24": "Operating (air damper closed)",
    "28": "Stopped (door open)",
    "32": "Operating (power III)",
    "33": "Stopped (CO sensor defect)",
    "34": "Stopped (check burn cup)",
    "35": "Stopped (no power consumption for fan)",
}

SUBSTATE_NAMES: dict[str, str] = {
    "0": "Waiting",
    "2": "Ignition",
    "4": "Ignition 2",
    "5": "Normal",
    "6": "Room temperature reached",
    "9": "Wood burning",
    "11": "Dropshaft hot",
    "13": "Failed ignition - open door and check burner for pellet accumulation",
    "20": "No fuel",
    "28": "Door open",
    "32": "Heating up",
    "34": "Check burn cup",
}
# Disambiguates substate "14" (state-dependent meaning), keyed "<state>_<substate>".
SUBSTATE_NAMES_BY_STATE: dict[str, str] = {
    "14_0": "By button",
    "14_1": "Wood burning?",
}

STARTUP_STATES = frozenset({"0", "2", "4", "5", "6", "9", "24", "32"})
SHUTDOWN_STATES = frozenset(
    {"11", "13", "14", "15", "17", "18", "19", "20", "23", "28", "33", "34", "35"}
)

# Translation keys for the "State text" / "Substate text" enum sensors, which
# show the codes above as localized plain text (see translations/*.json).
# Codes not listed map to "unknown".
STATE_KEYS: dict[str, str] = {
    "0": "operating",
    "2": "operating_startup",
    "4": "operating_startup",
    "5": "operating",
    "6": "stopped",
    "9": "stopped_wood_burning",
    "11": "stopped_dropshaft_hot",
    "13": "stopped_failed_ignition",
    "14": "off",
    "15": "stopped_bad_smoke_sensor",
    "17": "stopped_bad_dropshaft_sensor",
    "18": "stopped_check_burner_yellow",
    "19": "stopped_bad_external_auger_output",
    "20": "stopped_no_fuel",
    "23": "stopped_by_timer",
    "24": "operating_air_damper_closed",
    "28": "stopped_door_open",
    "32": "operating_power_iii",
    "33": "stopped_co_sensor_defect",
    "34": "stopped_check_burn_cup",
    "35": "stopped_no_fan_power",
}

SUBSTATE_KEYS: dict[str, str] = {
    "0": "waiting",
    "2": "ignition",
    "4": "ignition_2",
    "5": "normal",
    "6": "room_temperature_reached",
    "9": "wood_burning",
    "11": "dropshaft_hot",
    "13": "failed_ignition",
    "20": "no_fuel",
    "28": "door_open",
    "32": "heating_up",
    "34": "check_burn_cup",
}
# Same "<state>_<substate>" disambiguation as SUBSTATE_NAMES_BY_STATE.
SUBSTATE_KEYS_BY_STATE: dict[str, str] = {
    "14_0": "by_button",
    "14_1": "wood_burning_unconfirmed",
}
