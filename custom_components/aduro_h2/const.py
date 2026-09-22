"""Constants for the Aduro H2 Pellet Stove integration."""
from __future__ import annotations

DOMAIN = "aduro_h2"
MANUFACTURER = "Aduro"

CONF_SERIAL = "serial"
CONF_PIN = "pin"
CONF_SCAN_INTERVAL = "scan_interval"

# Stores the dict returned by AduroH2Api.discover() (serial/ip/type/version/
# build/lang) in the config entry, so device info survives restarts without
# needing a fresh broadcast discovery every time.
CONF_DISCOVERY = "discovery"

DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 20
MAX_SCAN_INTERVAL = 600

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
