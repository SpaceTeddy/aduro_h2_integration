# Aduro H2 Pellet Stove — Home Assistant Integration

A native Home Assistant custom integration for Aduro/NBE pellet stoves,
rewritten from the original `pyduro_mqtt.py` python_script + MQTT setup
(see [SpaceTeddy/homeassistant_aduro_stove_control_python_scripts](https://github.com/SpaceTeddy/homeassistant_aduro_stove_control_python_scripts))
into a proper integration with a config flow, a `DataUpdateCoordinator`, and
native entities. No MQTT broker, `python_script`, or helper automations are
needed anymore — the integration talks to the stove directly via
[pyduro](https://pypi.org/project/pyduro/).

The integration ships its own icon, shown in the integrations list and
config flow. This uses Home Assistant's local brand images feature and
needs **Home Assistant 2026.3 or newer**; on older cores the icon is simply
not shown, everything else still works.

## Installation

### Via HACS (recommended)

1. In HACS, go to **Integrations → ⋮ → Custom repositories**, add this
   repository's URL with category **Integration**.
2. Search for "Aduro H2 Pellet Stove" in HACS and install it.
3. Restart Home Assistant.

### Manual

1. Copy the `custom_components/aduro_h2` folder into your Home Assistant
   `config/custom_components/` directory, so you end up with
   `config/custom_components/aduro_h2/...`.
2. Restart Home Assistant.

### Setup

1. Go to **Settings → Devices & Services → Add Integration**, search for
   "Aduro H2 Pellet Stove".
2. Enter the stove's **serial number** and **pin code** (both on a sticker
   on the stove). Leave the address field empty to auto-discover the stove
   via UDP broadcast on the local network; if your Home Assistant instance
   is on a different subnet/VLAN than the stove (broadcast discovery won't
   reach it), enter its IP address or hostname directly instead.

The polling interval (default 60s) can be changed afterwards via the
integration's **Configure** button.

## What it creates

One device per stove, with:

- **Sensors**: room/shaft/smoke temperature, power (kW/%), oxygen, state,
  substate (both with a human-readable `description` attribute), substate
  remaining time, mode (raw), last alarm code, heat level (raw),
  stove/auger/ignition operating time, pellet consumption
  (today/yesterday/month/year), WiFi signal strength, stove IP, router SSID,
  MAC address, stove serial/type/SW version/SW build, and a diagnostic
  "Raw status" sensor exposing every raw status field as attributes (for
  templates/dashboards, including any field pyduro doesn't have a name for
  yet, as `unknown_<index>`).

  Note: the raw protocol field is called `boiler_temp`/`boiler_ref`, but on
  this (non-hydronic) stove it's actually room temperature and its
  setpoint, not boiler water — confirmed against the independent
  NewImproved/Aduro integration's own sensor docstring and German
  translation (`Raumtemperatur`/`Solltemperatur`), so the sensor here is
  named `room_temperature` accordingly. There's no separate DHW (domestic
  hot water) sensor - this stove model doesn't report one.
- **Binary sensor**: Alarm.
- **Switches**: Power (start/stop pellet feed & ignition), Force fan
  (manual fan override — see safety note below).
- **Selects**: Heat level (low/medium/high → `regulation.fixed_power`
  10/50/100), Mode (heat level/temperature/wood →
  `regulation.operation_mode`).
- **Number**: Target temperature (5–35°C → `boiler.temp`; only takes effect
  in temperature mode, which is switched to automatically when you set it).
- **Buttons**: Start, Stop, Force auger run, Reset alarm, Fetch data
  (manual refresh), Resume after wood mode.

## Known limitations / assumptions

- The NBE protocol's numeric `state`/`substate` codes, the
  `regulation.operation_mode` values, and the `STARTUP_STATES`/
  `SHUTDOWN_STATES` classification used by the Power switch are not
  publicly documented by the vendor. The mappings used here (see
  `custom_components/aduro_h2/const.py`) are reproduced, with attribution,
  from two independent reverse-engineering efforts for the same NBE
  protocol family: [svanggaard/NBEConnect](https://github.com/svanggaard/NBEConnect)
  and [NewImproved/Aduro](https://github.com/NewImproved/Aduro) (which also
  supplied the `boiler.temp` / `regulation.operation_mode` write paths for
  the Target temperature number and Mode select). They match this stove
  model in testing, but aren't a vendor spec.
- **Force fan safety**: turning it on puts the stove into manual mode and
  forces the fan on. The stove drops manual mode on its own if it stops
  receiving a `manual.keep_alive`, and this integration also re-sends one
  every 20s. It forces itself off after 10 minutes (e.g. in case Home
  Assistant restarts mid-override) or if smoke temperature exceeds 320°C,
  as safety nets independent of the stove's own timeout. Still, prefer
  turning it off explicitly rather than relying on any of these.
- Pellet consumption values are exposed with a `kg` unit to match the
  vendor app's display; this isn't independently confirmed against an NBE
  protocol spec.
- If the stove becomes unreachable, the coordinator automatically retries
  discovery (falling back to the `apprelay20.stokercloud.dk` cloud relay
  address, exactly like the original script) before giving up until the
  next poll cycle.

## Migrating from the old script

You can remove the old `python_script/pyduro_mqtt.py`, the automations that
called it, and the MQTT sensors/template sensors that read its topics —
everything they provided is now native entities on the device page.

## License

GPL-2.0, see [LICENSE](LICENSE).
