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
| LED panel | Brightness number (1–100%), Auto/Manual backlight select, On/Off/Scheduled display select |
| Filter | Filter problem sensor and reset-filter button |
| Wi-Fi | Deliberately not exposed; Wi-Fi remains the always-on transport |

The unit's humidity reading is also exposed as a sensor. Arbitrary speed
percentages use the device's manual-speed mode.

## Dashboard card

The optional **VENTS Breezy Remote** dashboard card is distributed as the
standalone [`www/vents-breezy-card.js`](www/vents-breezy-card.js) file. It is
not bundled, served, or registered by the integration.

To install it manually:

1. Copy `www/vents-breezy-card.js` from this repository to
   `/config/www/vents-breezy-card.js` in Home Assistant. Create the `www`
   directory if it does not exist.
2. In Home Assistant, open **Settings > Dashboards > Resources**, choose
   **Add resource**, enter `/local/vents-breezy-card.js`, and select
   **JavaScript module**.
3. Reload the browser, add **VENTS Breezy Remote** from the card picker, and
   select the Breezy fan entity.

The card discovers the airflow, heater, LED panel, humidity, filter, and filter-reset
entities on the same device.

The Night, Manual, and Turbo controls are presented as one mutually exclusive
air-intensity control. Moving the speed slider exits Night or Turbo and applies
the selected manual speed. Airflow modes use a four-way control, and filter
reset requires confirmation to avoid accidental resets.

The LED panel section has a brightness slider, Auto/Manual backlighting, and
On/Off/Scheduled display controls. Changing brightness selects manual
backlighting without changing fan power, speed, or the display schedule. Choose
**On** if the display is off and you want to see the new brightness immediately.
**Auto** restores light-sensor control; the slider shows the saved manual
brightness, not the current sensor-adjusted brightness. **Scheduled** uses the
screen-off interval already configured in the VENTS app.

The related entity overrides are `panel_brightness` (number),
`panel_backlight_mode` (select), and `panel_display` (select). Missing controls
are hidden; unknown or unavailable panel states disable their controls. Panel
registers are polled separately so unsupported panel settings do not prevent
normal fan control.

Panel controls use registers `0x0400`, `0x0402`, and `0x0407` from the
[Breezy Smart Home protocol](https://ventilation-system.com/download/breezy-manual-21433.pdf),
also mapped in the
[upstream protocol implementation](https://github.com/gody01/ecovent_v2/blob/main/custom_components/ecovent_v2/protocol_maps.py).

After updating, restart Home Assistant to load the new entities, replace the
standalone card file in `/config/www`, and reload the browser. If the old card
is cached, change the resource URL to `/local/vents-breezy-card.js?v=panel`.

Minimal YAML configuration:

```yaml
type: custom:vents-breezy-card
entity: fan.vents_breezy_160_e
```

The visual editor also allows each related entity to be overridden, which is
useful if entities were moved between devices or deliberately replaced.

If you manage Lovelace resources in YAML, register the copied file there
instead:

```yaml
lovelace:
  resources:
    - url: /local/vents-breezy-card.js
      type: module
```

When upgrading from a release that bundled the card, remove the old
`/vents_breezy/vents-breezy-card.js?...` resource from **Settings > Dashboards >
Resources**. That URL is no longer provided by the integration. Remove it from
YAML instead if your resources are YAML-managed.

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

For `Custom element doesn't exist: vents-breezy-card`, confirm that
`/config/www/vents-breezy-card.js` exists and that **Settings > Dashboards >
Resources** contains exactly one `/local/vents-breezy-card.js` entry of type
**JavaScript module**. Reload the browser after adding or replacing the file.
If the error persists, inspect that URL in the browser's Network and Console
tabs for its HTTP status and any JavaScript error.

## Development

The integration uses a `DataUpdateCoordinator`, config-entry runtime data,
fully async Home Assistant entry points, and executor isolation around the
synchronous upstream library. Run the lightweight checks with:

```bash
python -m compileall custom_components
python -m pytest
node --experimental-vm-modules --test tests/frontend.test.mjs
```

## License

MIT. `pyEcoventV2` is a separate MIT-licensed dependency maintained by its
authors.
