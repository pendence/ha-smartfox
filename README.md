# SMARTFOX for Home Assistant

Experimental Home Assistant custom integration for **SMARTFOX Pro / SMARTFOX Pro 2** via local Modbus TCP.

## Current version

**0.1.0-alpha.11** — early public test version.

This version has been tested on a SMARTFOX Pro 2 with Home Assistant. Reading of the core electrical values works, Car Charge 1 mode control has been successfully tested using Modbus/TCP FC16, and heater power is read from the local SMARTFOX `values.xml` endpoint because that value is not available through the documented Modbus registers.

## Features

- Local Modbus TCP connection; no cloud required
- Grid power, phase power, voltage, current and frequency
- PV production and total PV energy
- Battery 1 SOC and power
- Car Charge 1 power, session/total energy, mode and manual charging value
- Relay 1–4 and Verbrauchsregler control entities
- SMARTFOX heater power from local `values.xml`
- Current shown in A and energy in kWh
- Optional register groups are disabled by default where appropriate

## Requirements

- Home Assistant 2026.9 or newer
- SMARTFOX connected via LAN
- Modbus TCP reachable, normally port 502
- Unit ID normally 1

The integration observes a minimum one-second spacing for normal Modbus polling. SMARTFOX documentation specifies register offset `-1`; for example documented register 41608 is addressed as 41607 on Modbus.

## Installation with HACS

Until this repository is included in HACS by default, add this repository to HACS as a **custom repository** of type **Integration**, install SMARTFOX, restart Home Assistant, then go to **Settings → Devices & services → Add integration → SMARTFOX**.

## Manual installation

Copy `custom_components/smartfox` to `/config/custom_components/smartfox`, restart Home Assistant, then add the SMARTFOX integration from **Settings → Devices & services**.

## Alpha notice

This is an experimental integration. Some optional SMARTFOX register groups have not yet been validated on real hardware. Use writable entities carefully. No cyclic Modbus writes are performed; writes occur only after an explicit entity change.

## License

MIT
