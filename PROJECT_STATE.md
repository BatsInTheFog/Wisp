# Wisp: project state

_Last updated: 2026-11-16 (session 1)_

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

Note: the Hermes install on this Windows PC (`%LOCALAPPDATA%\hermes`) is only a remote
client that connects to the Mac. The real Hermes (and the gadget plugin) lives on the Mac.

Disk: about 21 GB free on C: after the Build Tools (2026-11-16). The ESP toolchain needs
about 3 GB more.

## Toolchain

| Tool | Status on the build machine |
| --- | --- |
| Git | installed |
| Python | 3.11 and 3.14 via `uv` (has Tkinter). The `python` command is only the Microsoft Store stub. |
| Node.js | v24.9.0 |
| C++ compiler | **Visual Studio Build Tools 2026** (18.11), C++ workload, installed 2026-11-16 at `C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools`. Needed for the Gadget simulator. Verified after restart (test program compiles and runs). (The 2022 package on winget fails with installer error 5008: its bootstrapper is too old.) |
| CMake | 4.4.5, inside the Gadget checkout's `.venv` (from pip) |
| Hermes Gadget checkout | `$env:USERPROFILE\Documents\GitHub\hermes-gadget-sdk` at `2ef17f6` (v0.5.0-127), outside the Wisp repo. Python 3.11 venv in `.venv` with `[dev,audio]` extras |
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

Simulator (Hermes Gadget, PowerShell, from `$env:USERPROFILE\Documents\GitHub\hermes-gadget-sdk`):

```
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"      # so build-sim finds cmake
.\.venv\Scripts\hermes-gadget.exe build-sim --test   # after changing firmware/core
.\.venv\Scripts\hermes-gadget.exe devserver          # demo stand-in for Hermes (port 8765)
.\.venv\Scripts\hermes-gadget.exe sim --url ws://<mac-ip>:8765/gadget --board sim-368x448 --name "Wisp sim" --live-audio
```

## What works

- Face art, `animation_spec.json`, slicing tools and the browser preview (`preview/wisp-face-lab.html`).
- Hermes Gadget simulator builds on this PC (core tests pass: 3/3) and completes a headless
  smoke test against the local demo server on `sim-368x448` (2026-11-16): pairs, sends text,
  gets the echo reply.
- **Simulator talks to the real Hermes on the Mac** (2026-11-16): `ws://<home LAN address>:8765/gadget`,
  device "Wisp sim" paired. Typed messages, voice (PC mic → Mac speech-to-text) and spoken
  replies (Mac text-to-speech → PC speakers) all work.
  - To talk: **click and hold on the simulated screen**. Holding Space didn't seem to work in
    our test, probably because keyboard focus was in the text box.
  - Simulator identity and saved replies: `$env:USERPROFILE\.hermes-gadget\sim\wisp-sim\`.

## Known problems / open questions

- Hermes Gadget officially supports only the **V2** 1.8" board. V1 needs a small board profile
  (different display and touch chips). See [docs/V1_PORT.md](docs/V1_PORT.md).
- Gadget's built-in face is 1-bit; Wisp's colour face needs its own renderer.
- No C++ compiler or ESP toolchain on this PC yet.
- Gadget plugin installed from `main` on the Mac's Hermes; the PC simulator is at `2ef17f6`.
  Keep the two in step when updating (plugin and firmware/simulator share the protocol).
- The Mac's address (<home LAN address>) could change; a DHCP reservation on the router would pin it.

## Decisions

- **Path:** fork Hermes Gadget; add a V1 board profile using xiaozhi's known-good V1 values;
  write Wisp's face as our own renderer inside Gadget's UI layer. (Session 1.)
- Art stays in `assets/`, scripts in `tools/`, firmware separate (planned: `firmware/`).

## Single next step

Fork Hermes Gadget on GitHub and add a **V1 board profile** (SH8601 display + FT3168 touch,
values in [docs/V1_PORT.md](docs/V1_PORT.md)), then build it with no flashing. Before the
first flash: install the ESP toolchain, take a full flash backup of the factory firmware, and
ask.
