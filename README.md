# VENTS Breezy for Home Assistant

![VENTS Breezy integration icon](custom_components/vents_breezy/brand/icon.png)

A small, local-only Home Assistant custom integration for the **VENTS Breezy
160-E**. It communicates over the fan's local UDP interface and does not need a
VENTS cloud account.

The integration reuses
[`pyEcoventV2`](https://github.com/gody01/pyEcoventV2) for the VENTS/Blauberg
wire protocol, with a narrow Breezy register map to avoid polling unrelated
device families.

## Features

| Remote control | Home Assistant entity |
|---|---|
| Power and three speed buttons | Fan power and percentage (33%, 67%, 100%) |
| Night | `night` fan preset |
| Turbo | `turbo` fan preset |
| Airflow buttons | Airflow mode select: ventilation, heat recovery, air supply, extract |
| Heater | Heater switch |
| Filter | Filter problem sensor and reset-filter button |
| Wi-Fi | Deliberately not exposed; Wi-Fi remains the always-on transport |

The unit's humidity reading is also exposed as a sensor. Arbitrary speed
percentages use the device's manual-speed mode.

## Dashboard card

The integration includes a **VENTS Breezy Remote** dashboard card and loads it
automatically; no separate frontend install or dashboard resource is needed.
Add it from the dashboard card picker, select the Breezy fan entity, and the
card discovers the airflow, heater, humidity, filter, and filter-reset entities
on the same device.

The Night, Manual, and Turbo controls are presented as one mutually exclusive
air-intensity control. Moving the speed slider exits Night or Turbo and applies
the selected manual speed. Airflow modes use a four-way control, and filter
reset requires confirmation to avoid accidental resets.

Minimal YAML configuration:

```yaml
type: custom:vents-breezy-card
entity: fan.vents_breezy_160_e
```

The visual editor also allows each related entity to be overridden, which is
useful if entities were moved between devices or deliberately replaced.

After installing or updating the integration, restart Home Assistant. The card
is registered as a versioned frontend module after its HTTP route is available,
including in already-open dashboards. Version 0.2.2 also removes the legacy
stored Lovelace resource created by version 0.2.1, which could be loaded too
early during startup.

## Requirements

- Home Assistant 2026.3 or newer
- VENTS Breezy 160-E connected to the same local network as Home Assistant
- A fixed DHCP lease or otherwise stable fan IP address
- UDP port 4000 reachable from Home Assistant

## Install with HACS

HACS requires a public repository. While this repository is private, use the
manual installation below. CI skips HACS validation for private repositories;
Hassfest and the Python checks still run. If the repository is made public,
HACS validation runs automatically. Before then, set a repository description
and relevant topics such as `vents`, `breezy`, and `ventilation` in GitHub's
**About** settings.

1. Open HACS and choose **Integrations**.
2. Open the menu, choose **Custom repositories**, and add this repository as an
   **Integration**.
3. Download **VENTS Breezy** and restart Home Assistant.
4. Go to **Settings > Devices & services > Add integration**, search for
   **VENTS Breezy**, and enter the fan's IP address.

The factory device password is `1111`. If you changed it in the VENTS app, enter
the new password during setup.

## Manual install

Copy `custom_components/vents_breezy` into the `custom_components` directory in
your Home Assistant configuration, restart Home Assistant, then add the
integration from the UI.

## Notes

- Commands are local and stay on your LAN.
- The integration never disables or reconfigures Wi-Fi.
- Night and Turbo use the unit's built-in Night/Party timer modes, including the
  timer durations already configured on the fan.
- Filter reset should be pressed only after cleaning or replacing the filter.

## Troubleshooting

If setup cannot connect, confirm that the IP address is current, Home Assistant
can reach the fan's subnet, UDP port 4000 is not blocked, and the password is
correct. Download integration diagnostics from the device page when reporting
an issue; passwords are redacted.

## Development

The integration uses a `DataUpdateCoordinator`, config-entry runtime data,
fully async Home Assistant entry points, and executor isolation around the
synchronous upstream library. Run the lightweight checks with:

```bash
python -m compileall custom_components
python -m pytest
```

## License

MIT. `pyEcoventV2` is a separate MIT-licensed dependency maintained by its
authors.
