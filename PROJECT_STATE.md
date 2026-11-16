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
- **Simulator talks to the real Hermes on the Mac** (2026-11-16): the address is in
  `config/wisp.local.json` (not committed), device "Wisp sim" paired. Typed messages, voice (PC mic → Mac speech-to-text) and spoken
  replies (Mac text-to-speech → PC speakers) all work.
  - To talk: **click and hold on the simulated screen**. Holding Space didn't seem to work in
    our test, probably because keyboard focus was in the text box.
  - Simulator identity and saved replies: `$env:USERPROFILE\.hermes-gadget\sim\wisp-sim\`.

## Known problems / open questions

- Hermes Gadget officially supports only the **V2** 1.8" board. V1 needs a small board profile
  (different display and touch chips). See [docs/V1_PORT.md](docs/V1_PORT.md).
- Gadget's built-in face is 1-bit; Wisp's colour face needs its own renderer.
- No ESP toolchain on this PC yet (the C++ compiler for the simulator is installed).
- Gadget plugin installed from `main` on the Mac's Hermes; the PC simulator is at `2ef17f6`.
  Keep the two in step when updating (plugin and firmware/simulator share the protocol).
- The Mac's home-network address could change; a DHCP reservation on the router would pin it.

## Decisions

- **Path:** fork Hermes Gadget; add a V1 board profile using xiaozhi's known-good V1 values;
  write Wisp's face as our own renderer inside Gadget's UI layer. (Session 1.)
- Art stays in `assets/`, scripts in `tools/`, firmware separate (planned: `firmware/`).
- **Stock Gadget face first.** Wisp's custom face (`animation_spec.json`) comes only after the
  V1 board works with stock Gadget firmware.
- **Hermes address is a setting, never compiled in.** Gadget already keeps it (with Wi-Fi,
  pairing keys and any Tailscale key) in the device's flash storage (NVS), set over USB
  (`set server ...`, `hermes-gadget provision`) or the phone setup page.

## Two repositories, and where secrets live

- **Fork:** `BatsInTheFog/hermes-gadget-sdk` (planned), a copy of Adolanium's Hermes Gadget
  on GitHub. Forks of public repos are **public**. It holds only board code: the V1 profile,
  later the long-recording mode and Wisp's face renderer. Work goes on a `wisp` branch so
  upstream updates can be pulled into `main` and merged across.
- **Wisp (this repo, private):** art, face spec, tools, docs, project state. It will point to
  one exact commit of the fork (a git submodule at `firmware/hermes-gadget`), so a Wisp commit
  always says which firmware it goes with.
- **Secrets never go in either repo:** Wi-Fi password, Hermes address, pairing data, device
  keys, Tailscale keys. They live in `config/wisp.local.json` on this PC (git-ignored; template
  in `config/wisp.local.example.json`) and, once set, in the board's flash. The simulator's
  identity lives in `%USERPROFILE%\.hermes-gadget\`, outside both repos.
- Note: earlier Wisp commits mention the Mac's home-network address (192.168.x.x). It is only
  reachable inside the home network and this repo is private, so the history was left as is.

## Future requirements (planned, not built)

### 1. Away-from-home access (e.g. at work)

Hermes is only on the home network now. Options for the board, best first:

| Option | How the ESP32 connects | Hermes exposed to the internet? | Status in Gadget |
| --- | --- | --- | --- |
| **A. Native tailnet** (recommended to try first) | The board joins your Tailscale tailnet itself using TailTiny (an independent ESP32 Tailscale client), with a one-off tagged auth key (`set ts_key`, `set tailnet on`). Connects to `ws://100.x.y.z:8765/gadget`. WireGuard encrypts it. | No | Built in but **experimental and off on every board**: we turn it on for our V1 profile (`b.tailnet = true` + 5 sdkconfig lines). Needs PSRAM (we have 8 MB). About 114 KB flash, 27 KB internal RAM, more battery use. |
| **B. Tailscale Funnel** (fallback, no firmware change) | Plain internet: `wss://<mac>.<tailnet>.ts.net/gadget`. TLS with a Let's Encrypt certificate, which the firmware trusts. | Yes, the gadget port only; pairing + per-device key still guard it. An access token can be added. | Works with stock firmware on every board. |
| C. Cloudflare Tunnel | Same as B with a Cloudflare address. | Yes | Works with current firmware (older firmware rejected Cloudflare's certificate chain). |
| D. Plain WireGuard client | Would need a WireGuard library added and a server to run. | No | Not in Gadget; no reason to build it while A exists. |

- Either way the Hermes address stays a setting. Moving between home and work needs no
  rebuild: with A the same `100.x` address works everywhere; with B the same `wss://` address.
- Wi-Fi: the device stores up to **5 networks**, tried in order, so home and work Wi-Fi
  (or a phone hotspot) can both be saved. No captive-portal (login page) networks.
- Mac side for A: set the gadget plugin to listen on the Mac's tailnet address (or all
  interfaces) and add a tailnet rule letting `tag:gadget` reach only TCP 8765 on the Mac.
- Test plan: Gadget's tailnet checklist in `docs/hardware-validation.md#tailnet`.

### 2. Note taking: quick notes and longer spoken notes

- **Quick voice notes** fit the normal talk turn (Gadget's limit is **30 s**,
  `kMaxUtteranceMs` in `firmware/core/include/hg/app.hpp`). Hermes (or n8n via a Hermes tool)
  decides it's a note and files it in Obsidian. No firmware change needed.
- **Long recordings (up to 1 hour)** need a separate **record mode** in our fork, because
  normal turns hold the whole utterance in a RAM buffer (1.5 MB for 30 s at 24 kHz). One hour
  is about 115 MB at 16 kHz, which can't fit in 8 MB of PSRAM. Planned design:
  1. **Start/stop** from a separate gesture or screen (not hold-to-talk), with a visible
     timer and a "recording" state on the face.
  2. **Write to microSD** as it records: one WAV file per session, in chunks, flushed every
     few seconds so a power loss keeps all but the last moments. (16 kHz mono 16-bit is
     about 1.9 MB/minute; compression such as Opus can come later.)
  3. **Upload queue:** a small index file on the card lists finished recordings and how many
     bytes of each were confirmed by Hermes. When online, upload in the background,
     resuming from the last confirmed byte after any dropout. Delete from the card only
     after Hermes confirms, or keep until space runs low.
  4. **Transport:** extend Gadget's protocol in the fork with a "recording upload" message
     and binary channel (alongside audio/image/firmware/face), so it reuses the existing
     pairing and device key. The plugin saves the file on the Mac, then hands it to Hermes
     or n8n (transcribe, summarise, file to Obsidian). Alternative: HTTP upload straight to
     an n8n webhook, but that needs a second credential on the device.
  5. **Doesn't block talking:** record mode is its own state, separate from conversation turns.
- What Gadget already gives us: a microSD mount (FAT32) used for its log mirror
  (`port_sdlog.*`, `SdConfig` in `board.hpp`), and Wi-Fi/offline handling.
- To confirm: the V1 board's microSD pins (from Waveshare's V1 schematic), and that the
  slot is wired to the S3 (not shared with something else).

## Single next step

Fork Hermes Gadget on GitHub and add a **V1 board profile** (SH8601 display + FT3168 touch,
values in [docs/V1_PORT.md](docs/V1_PORT.md)), then build it with no flashing. Before the
first flash: install the ESP toolchain, take a full flash backup of the factory firmware, and
ask.
