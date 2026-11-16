# Wisp: project state

_Last updated: 2026-11-15 (session 1)_

## Hardware (confirmed from the board's label)

- **Board:** Waveshare ESP32-S3-Touch-AMOLED-1.8, **V1** revision
- **Chip:** ESP32-S3R8, 8 MB PSRAM, 16 MB flash
- **Display:** SH8601 AMOLED, QSPI, 368x448
- **Touch:** FT3168 (I2C 0x38)
- **IO expander:** TCA9554 (I2C 0x20): display reset, display power, touch reset, PWR key
- **Power:** AXP2101 PMIC (I2C 0x34), battery connector
- **Audio:** ES8311 codec (I2C 0x18), built-in analog mic, built-in speaker
- **Also on board:** QMI8658 IMU, PCF85063 RTC, microSD slot, 2 buttons (BOOT, PWR)
- **Full pin map:** [docs/V1_PORT.md](docs/V1_PORT.md)

### Factory firmware (to restore the board)

- File: `ESP32-S3-Touch-AMOLED-1.8-FactoryXiaozhi_250805.bin` (not in this repo; `*.bin` is ignored)
- Flash at address `0x0` with the Espressif Flash Download Tool.
- After flashing: with USB plugged in, hold PWR 6 seconds, then press it again briefly.
- TODO: confirm where the .bin lives on this computer, and take a full flash backup before the first flash.

## Machines

| Role | Machine | Notes |
| --- | --- | --- |
| **Build machine** | This Windows 11 PC (`$env:USERPROFILE\Documents\GitHub\Wisp`) | Builds firmware, flashes the board over USB |
| Hermes Agent | Mac (`~/.hermes/hermes-agent`), v0.22.6 | Also runs speech-to-text and text-to-speech |
| LLM | A separate machine | Hermes calls it |
| Later | n8n, Obsidian | For future features |

Note: this Windows PC **also** has a Hermes install (`%LOCALAPPDATA%\hermes`) with a gateway
running. The plan uses the Mac one unless we decide otherwise.

## Toolchain

| Tool | Status on the build machine |
| --- | --- |
| Git | installed |
| Python | 3.11 and 3.14 via `uv` (has Tkinter). The `python` command is only the Microsoft Store stub. |
| Node.js | v24.9.0 |
| C++ compiler (Visual Studio Build Tools) | **not installed** (needed for the Gadget simulator) |
| CMake | not installed (can come from pip inside a venv) |
| ESP-IDF / PlatformIO | **not installed** (needed for firmware) |
| esptool | not installed |
| GitHub CLI (`gh`) | not installed (git push works over the existing remote) |

## Build and flash commands

Not set up yet. Planned (Hermes Gadget firmware, PlatformIO):

```
cd firmware/esp32
pio run -e <wisp-v1-env>              # build only, safe
pio run -e <wisp-v1-env> -t upload    # FLASHES THE BOARD: ask first
pio device monitor                    # read the serial log, safe
```

Simulator (Hermes Gadget, Windows PowerShell, once a compiler is installed):

```
hermes-gadget build-sim --test
hermes-gadget sim --url ws://<mac-ip>:8765/gadget --board sim-368x448 --live-audio
```

## What works

- Face art, `animation_spec.json`, slicing tools and the browser preview (`preview/wisp-face-lab.html`).

## Known problems / open questions

- Hermes Gadget officially supports only the **V2** 1.8" board. V1 needs a small board profile
  (different display and touch chips). See [docs/V1_PORT.md](docs/V1_PORT.md).
- Gadget's built-in face is 1-bit; Wisp's colour face needs its own renderer.
- No C++ compiler or ESP toolchain on this PC yet.
- Unknown: does the Mac's firewall allow port 8765? Is the gadget plugin installed in Hermes?

## Decisions

- **Path:** fork Hermes Gadget; add a V1 board profile using xiaozhi's known-good V1 values;
  write Wisp's face as our own renderer inside Gadget's UI layer. (Session 1.)
- Art stays in `assets/`, scripts in `tools/`, firmware separate (planned: `firmware/`).

## Single next step

Get the Hermes Gadget desktop simulator connected to Hermes: install the gadget plugin on the
Mac's Hermes, then build and run the simulator (`sim-368x448`) and pair it.
