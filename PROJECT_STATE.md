# Wisp: project state

_Last updated: 2026-11-16 (session 1, decisions on remote access and recordings)_

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
- **Full flash backup taken 2026-11-16** (verified against the board, digest matched):
  `(a private backups folder outside the repo)`, outside
  the repo, with a README holding its SHA-256, partition table and the restore command.
  It contains the board's settings storage, so it stays private. Restoring it puts the board
  back exactly as it was, so the downloadable factory .bin is only a second fallback.
- Board on this PC: **COM3** (USB Serial/JTAG, VID:PID 303A:1001),
  chip ESP32-S3 rev v0.2, flash 16 MB (quad), PSRAM 8 MB.
- Factory partition layout: nvs, otadata, phy_init, `model` (952 KB), `factory` app
  (4.2 MB), `ota_0` app (6 MB), `storage` (4.8 MB). Gadget's layout is different, so the
  first Gadget flash must be a full USB flash (bootloader + partition table + app).

## Machines

| Role | Machine | Notes |
| --- | --- | --- |
| **Build machine** | This Windows 11 PC (`$env:USERPROFILE\Documents\GitHub\Wisp`) | Builds firmware, flashes the board over USB |
| Hermes Agent | Mac (`~/.hermes/hermes-agent`), v0.22.6 | Also runs speech-to-text and text-to-speech. Static IP on the home network (in `config/wisp.local.json`). Already on the user's tailnet. |
| LLM | A separate machine | Hermes calls it |
| Later | n8n, Obsidian | For future features |

Note: the Hermes install on this Windows PC (`%LOCALAPPDATA%\hermes`) is only a remote
client that connects to the Mac. The real Hermes (and the gadget plugin) lives on the Mac.

Disk: about 17 GB free on C: after the Build Tools and PlatformIO (2026-11-16).

## Toolchain

| Tool | Status on the build machine |
| --- | --- |
| Git | installed |
| Python | 3.11 and 3.14 via `uv` (has Tkinter). The `python` command is only the Microsoft Store stub. |
| Node.js | v24.9.0 |
| C++ compiler | **Visual Studio Build Tools 2026** (18.11), C++ workload, installed 2026-11-16 at `C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools`. Needed for the Gadget simulator. Verified after restart (test program compiles and runs). (The 2022 package on winget fails with installer error 5008: its bootstrapper is too old.) |
| CMake | 4.4.5, inside the Gadget checkout's `.venv` (from pip) |
| Hermes Gadget checkout | `$env:USERPROFILE\Documents\GitHub\hermes-gadget-sdk`, outside the Wisp repo. Remotes: `origin` = fork `BatsInTheFog/hermes-gadget-sdk`, `upstream` = Adolanium's original (pushing to it is disabled). Work branch **`wisp`** (based on upstream `2ef17f6`, v0.5.0-127). Python 3.11 venv in `.venv` with `[dev,audio]` extras |
| CMake | not installed (can come from pip inside a venv) |
| ESP-IDF / PlatformIO | PlatformIO Core 6.2.0 in the Gadget `.venv`; ESP-IDF comes with it (in `%USERPROFILE%\.platformio`) |
| esptool | v5.4.0, bundled with PlatformIO |
| GitHub CLI (`gh`) | not installed (git push works over the existing remote) |

## Build and flash commands

PlatformIO Core 6.2.0 is installed in the Gadget checkout's `.venv` (run it as
`..\..\.venv\Scripts\pio.exe` from `firmware\esp32`); its toolchains live in
`%USERPROFILE%\.platformio`. Commands, from the Gadget checkout's `firmware/esp32` folder on
the `wisp` branch:

```
pio run -e esp32s3-touch-amoled-18-v1              # build only, safe
pio run -e esp32s3-touch-amoled-18-v1 -t upload    # FLASHES THE BOARD: ask first
pio device monitor                                 # read the serial log, safe
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

- Hermes Gadget officially supports only the **V2** 1.8" board. Our **V1 profile is written**
  on the fork's `wisp` branch (commit `f66e85f`): board option `esp32s3-touch-amoled-18-v1`,
  SH8601 driven through Gadget's AMOLED code with xiaozhi's V1 table, FT3168 touch at 0x38 /
  INT 21. Gadget's firmware/docs tests pass (176). **Compiles for the ESP32** (2026-11-16,
  first build 32 min incl. toolchain download): output in
  `firmware\esp32\.pio\build\esp32s3-touch-amoled-18-v1\` (`firmware.bin` 1.65 MB).
  **Flashed to the board 2026-11-16** over COM3 (bootloader, partition table, OTA data and
  app all written and hash-verified).
  - **Boots and draws correctly** (2026-11-16): shows Gadget's Wi-Fi setup screen with QR
    code, upright, not mirrored, no edge stripe; colours right (red status dot is red).
  - Console (`status`, `diag` over COM3): board `esp32s3-touch-amoled-1.8-v1`, firmware
    0.5.0 (IDF 6.1.0), battery 74% / 3970 mV charging on USB, PWR key found, 1.49 MB
    recording buffer, 5 MB PSRAM free. I2C answers: 0x18 ES8311, 0x20 TCA9554, 0x34
    AXP2101, 0x51 PCF85063 RTC, 0x6b QMI8658 IMU. **0x38 (FT3168 touch) not in the scan**:
    possibly just dozing (Gadget notes the 2.06's FT3168 does this); confirm with a swipe.
  - Phone Wi-Fi setup ("Check connection and save") saved nothing on the first try
    (2026-11-16). Hermes address and name "Wisp" were then set over USB (`set server`,
    `set name`). Wi-Fi then set over USB with `hermes-gadget provision` (user ran it): the
    board finds the network (signal -48 dBm, strong) but keeps failing with **reason 15,
    "4-way handshake timeout"**, which almost always means the password doesn't match.
    In PowerShell, use single quotes around the password (`$` and backtick are special
    inside double quotes). **That was it**: the password has a `$`; re-entered with single
    quotes, the board joined (WPA2-PSK, channel 6).
  - After joining, the board took a while (more than 30 s) to get an address from the
    router: the log repeated `sta is connected, disconnect before connecting to new ap`.
    Signal was weak at that moment (-85 dBm on one mesh point, -53 earlier). It then got an
    address on its own, connected to Hermes, showed a pairing code, and the user approved
    it: **the V1 board is paired with Hermes as "Wisp"** (2026-11-16). Watch for slow joins.
  - **First voice test on the board:** speech recognised, reply spoken, swipe-down cancel
    works instantly. Volume was soft: set to 80 (`set volume 80`). **Replies stuttered**:
    the board sat on a distant mesh node (-87 to -91 dBm, channel 6; one connection dropped
    with a 10 s stalled send) while a near node was at -48 (channel 11). Cause: Gadget joins
    the first access point it hears (ESP-IDF fast scan) and fast join keeps returning to
    it. **Fix on the fork** (`a347dcd`, `port_wifi.cpp`): scan all channels and join the
    strongest; forget a remembered access point heard below -75 dBm. Flashed together with
    swipe-up (`980f396`) on 2026-11-16: the board went back to the remembered weak node
    (channel 6, -78) and got stuck associated with **no address** for 2+ minutes, because
    the "forget weak" step only runs once an address arrives. **Follow-up fix `f5444e1`**:
    when a retry finds the board associated but without an address, forget the remembered
    node and disconnect so it rejoins by scanning. Flashed: it left the weak node and
    joined the **strong one (channel 11, -55 dBm)**, but still got no address within ~20 s
    there either, and the new rule then dropped it every 20 s, so it looped. **The router's
    slow address hand-out is a separate issue from signal.** Fix `1bf49c0`: only abandon
    when the access point is weak (below -75); on a good signal keep waiting as stock
    Gadget does. **Flashed and confirmed** (board's `elf_sha256` `c252ab487cf01cdc` matches
    the local build; the `build.time` in `diag` is the app-descriptor compile time and can
    look stale). Board stays on the strong node (channel 11, -49 to -62) but got **no
    address for 4+ minutes**.
  - Suspected Gadget's `CONFIG_LWIP_DHCP_RESTORE_LAST_IP=y` (asks straight for the last
    address); turned it off for the V1 board (fork `71a00d6`, full rebuild 12 min) and
    flashed (fingerprint `e916b210cf337c2f`). **Didn't help:** associated to a strong node
    (channel 6, -50) and still **no address after 2+ minutes**; the log shows only Gadget's
    20 s retry (`sta is connected`). This PC (<home LAN address>, same network) sees no trace of
    the board; its earlier address <home LAN address> doesn't answer. Fresh discovery is kept
    (harmless, and fine with Tailscale: the tailnet address is separate).
  - **Root cause still unknown.** It got an address once (slowly) on the original
    firmware. Next checks, on the router side: does the router app list the board
    (, maybe as "espressif"), is it paused/blocked, can it get a
    reservation; restart the router/mesh points (many failed and repeated joins may have
    made it throttle the board). On the board side if needed: DHCP debug logging.
  - Router app (Google Home) lists the board as **idle, not offline**: associated, no
    traffic. Theory: after today's many hops between mesh points the mesh still maps the
    board to an old point; the DHCP exchange (or lwIP's ARP check of the offered address,
    `CONFIG_LWIP_DHCP_DOES_ARP_CHECK=y`) then fails. First test, no flashing: restart the
    whole mesh and power-cycle the board. If that fails: a build with DHCP debug logs (and
    possibly the ARP check off). Note: Gadget's NVS sits at the same place as xiaozhi's
    (0x9000, 24 KB), so old xiaozhi settings (incl. Wi-Fi driver data) are still in it.
  - **Mesh restart + board power-cycle fixed it** (2026-11-16): the board came online
    (user report; it wasn't on USB afterwards, so signal and access point weren't read).
    So the router side was confused, most likely by today's many reconnects between mesh
    points. Firmware on the board now: fork `71a00d6` (strongest-point join, weak-point
    forget, rescan only on a weak point, fresh DHCP discovery, swipe-up reply recall).
    If it happens again: restart the mesh first.
  - **Spoken replies are smooth now** (user test, 2026-11-16): the stutter was the weak
    mesh point, not memory or the chip. Opus isn't needed for now.
  - Memory during these tests is healthy: internal RAM 168 KB free (lowest 135 KB), PSRAM
    5 MB free, recording buffer 1.49 MB, nothing dropped. Playback of 24 kHz speech is well
    within the ESP32-S3's means; the stutter matched the -87 to -91 dBm signal and a 10 s
    stalled send, not memory.
  - **Reading replies again:** Gadget keeps a finished reply on screen for 20 s, then the
    mascot returns; only boards with Up/Down keys could bring it back. **Fork `980f396`
    adds swipe up** on the touchscreen: the first swipe brings the last reply back, further
    swipes page through it. Core tests pass (651, incl. a new one). **Confirmed on the
    board** (2026-11-16): swipe up after a reply brings it back; during a reply it shows the
    text scrolling along with the speech; PWR stops speech and the text can still be
    recalled. Works in the simulator too (`sim-368x448`, drag up) once rebuilt.
  - If stutter ever returns with a good signal: turn on Opus for spoken replies (about a
    tenth of the data) by installing libopus on the Mac (`brew install opus`) and
    restarting the gateway.
  - Phone Wi-Fi setup tip: the board allows 30 s for "Check connection and save" and the
    phone may drop off the setup network meanwhile (rejoin and reload to see the result).
    Needs a 2.4 GHz network.
  - Cosmetic: `diag` reports `display co5300` for the SH8601 (hard-coded label); fix later.
  - **Touch UI for Wisp** (fork `9dd40dd`, 2026-11-16), two new `DeviceProfile` options, on
    for the V1 board and the `sim-368x448` simulator profile, off for every other board:
    - `autohide_bars`: on Ready / Listening / Thinking / Responding while online, the top
      bar ("Wisp" + network) and the hint bar stay dark; any swipe shows them for 5 s
      (`kBarsShowMs`). Settings, setup, pairing, offline/connecting screens and hint
      messages (e.g. "Paired with Hermes") keep them.
    - `chat_view`: the board keeps the conversation (speech transcripts, typed messages,
      final replies; newest 40 lines; a new session clears it). Swipe left on the face
      opens "Conversation" at the newest line; swipe down scrolls back, up forward; swipe
      left again or PWR returns to the face. Holding the screen still talks from it.
    - RTC turned on (`b.rtc.enabled`, PCF85063 at 0x51). IMU still unused.
    - Checks: 656 core tests pass (5 new), Gadget firmware/docs/sim tests pass
      (`test_sim_window` once errored on a window-timing hiccup, then passed 7/7), simulator
      screenshots show each state. Built (app 1650 KB, 73% free). **Flashed 2026-11-16**
      (firmware `c78812e34c2b4904`): online in 20 s, still paired, `diag` lists
      `rtc: pcf85063`. **User confirmed all of it works** (bars, conversation view, resting clock).
    - **Time isn't set yet:** Gadget only runs SNTP (pool.ntp.org) while the resting clock
      face is on (`clock` setting, off by default), and the RTC chip starts without a valid
      time. To get time: turn on the clock face (Settings → Clock face, or `set clock 60`)
      and set the time zone (`set timezone <POSIX TZ>`, default `UTC0`); optionally
      `set time_format 12h`. **Done 2026-11-16:** `timezone` = `CST6CDT,M3.2.0,M11.1.0`
      (Chicago, with daylight saving), `time_format` = `12h`, `clock` = `150` (resting clock
      after 2.5 min idle). SNTP synced at once (`diag` time valid + synced, UTC 10:29 =
      4:29 AM Chicago, matching the PC), and the time is written to the RTC.
    - Labels are English-only literals for now ("Conversation", "You", "Swipe left for the
      face"), not in Gadget's translation tables.
  - Reading the console: `console.py`-style script (open COM3 with DTR/RTS low, send
    `status` / `diag`); resetting via RTS and reading the boot log returned nothing.
  - The UI is 368x432 on the 368x448 glass on purpose (as Gadget's V2 profile): the panel
    window covers all 448 rows, the top and bottom 8 rows stay black, and the UI keeps clear
    of the rounded corners. Wisp's face renderer will want the full glass: then set
    `amoled.height = 448`, `gap_y = 0`, `touch.offset_y = 0`.
  - The flash wrote only Gadget's own regions; old xiaozhi data elsewhere on the chip
    (e.g. its settings and model areas) was not erased. If settings act strangely, an NVS
    erase is the fix (ask first).
  - If the screen stays dark: with USB plugged in, hold PWR 6 seconds, then press it again
    briefly (from the factory-restore procedure). Risks to check on first boot: screen dark or shifted (start-up table),
  touch mirrored, mic gain. See [docs/V1_PORT.md](docs/V1_PORT.md).
- Gadget's built-in face is 1-bit; Wisp's colour face needs its own renderer.
- **App space (was tight):** the shared table gave each app slot ~2 MB (17% free). Fork
  `7be3631` gives the V1 board its own 16 MB table
  (`boards/esp32s3-touch-amoled-18-v1/partitions.csv`): nvs 0x9000 (24 KB), otadata,
  phy_init at the same addresses as before (settings and pairing survive), **ota_0 / ota_1
  6 MB each**, coredump 64 KB at 0xc20000, **assets 3.8 MB** (data/spiffs) at 0xc30000.
  Built: app 1648 KB in a 6144 KB slot, **73% free**; Gadget checks pass (172). **USB-flashed
  2026-11-16** (all four parts hash-verified): online 22 s after boot, **still paired**,
  name/server/Wi-Fi kept, `diag` `ota.slot_size` 6291456, firmware `58155120ebda806e`,
  address <home LAN address> on a strong point (-50). Later firmware can go over USB or over
  the air (the layout stays).
- Gadget plugin installed from `main` on the Mac's Hermes; the PC simulator is at `2ef17f6`.
  Keep the two in step when updating (plugin and firmware/simulator share the protocol).

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

- **Fork:** `BatsInTheFog/hermes-gadget-sdk` (created 2026-11-16), a copy of Adolanium's Hermes Gadget
  on GitHub. Forks of public repos are **public**. It holds only board code: the V1 profile,
  later the long-recording mode and Wisp's face renderer. Work goes on a `wisp` branch so
  upstream updates can be pulled into `main` and merged across.
- **Wisp (this repo, private):** art, face spec, tools, docs, project state. It will point to
  one exact commit of the fork (a git submodule at `firmware/hermes-gadget`, to add once the
  firmware runs on the board), so a Wisp commit always says which firmware it goes with.
  Until then, PROJECT_STATE.md records the fork commit.
- **Secrets never go in either repo:** Wi-Fi password, Hermes address, pairing data, device
  keys, Tailscale keys. They live in `config/wisp.local.json` on this PC (git-ignored; template
  in `config/wisp.local.example.json`) and, once set, in the board's flash. The simulator's
  identity lives in `%USERPROFILE%\.hermes-gadget\`, outside both repos.
- Note: earlier Wisp commits mention the Mac's home-network address (192.168.x.x). Decision
  (2026-11-16): leave that history as is (home-network only, private repo).

## Future requirements (planned, not built)

### 1. Away-from-home access (e.g. at work)

**Decision (2026-11-16): option A, the board joins the tailnet via TailTiny. Funnel (B) is the
fallback.** The Mac is already on the tailnet (the laptop reaches Hermes that way).

**Order:** V1 board working on home Wi-Fi with stock Gadget first, then turn on the tailnet.

**When we get there, walk through (user does the admin-console steps):**
1. Tailnet policy: add `tag:wisp` under `tagOwners`, and a grant letting only `tag:wisp`
   reach `tcp:8765` on the Mac's `100.x` address (nothing else on the tailnet).
2. Auth key: Settings → Keys → one-off (not reusable), not ephemeral, pre-approved, tagged
   `tag:wisp`. Store it only in `config/wisp.local.json`, then on the board (`set ts_key`).
3. Key expiry: tagged devices have node-key expiry off by default; confirm in Machines →
   the board → "Disable key expiry" if it shows as expiring.
4. Mac: gadget plugin listens on the tailnet address too (`platforms.gadget.extra.host`),
   restart the gateway; board's `server` = `ws://<mac 100.x>:8765/gadget`.
5. Run Gadget's tailnet checklist (`docs/hardware-validation.md#tailnet`).

Options considered, best first:

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
- Test plan: Gadget's tailnet checklist in `docs/hardware-validation.md#tailnet`.

### 2. Note taking: quick notes and longer spoken notes

- **Quick voice notes** fit the normal talk turn (Gadget's limit is **30 s**,
  `kMaxUtteranceMs` in `firmware/core/include/hg/app.hpp`). Hermes (or n8n via a Hermes tool)
  decides it's a note and files it in Obsidian. No firmware change needed.
- **Card:** 32 GB microSD (FAT32). Recordings **regularly run 15 minutes or longer**, up to an
  hour. At 16 kHz mono 16-bit: 15 min ≈ 29 MB, 1 h ≈ 115 MB; the card holds about 270 hours,
  and FAT32's 4 GB file limit is far away. Record mode is designed for 15-60 min as the
  normal case, not an edge case.
- **Long recordings** need a separate **record mode** in our fork, because
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
  6. **Power during long sessions:** the screen shows an elapsed timer, kept mostly black
     (AMOLED black pixels are off) and dimmed after a while; Wi-Fi can stay off or idle while
     recording and upload afterwards. Warn on screen, and close the file cleanly, if the
     battery gets low or the card is nearly full.
- **Checks when record mode is built:**
  - Record 60 min on battery with the timer on screen; log battery % / mV every minute
    (Gadget has a battery log) and note minutes per 10% drop. Repeat with Wi-Fi off during
    recording, and with the screen dimmed, to see what each saves.
  - Pull power mid-recording: the file up to the last flush must survive and upload.
  - Drop Wi-Fi mid-upload: upload resumes from the last confirmed byte.
  - A 15-min recording uploads and reaches Hermes/n8n intact (duration matches).
- Gadget's 30 s limit (`kMaxUtteranceMs`) stays for normal turns; record mode doesn't change it.
- What Gadget already gives us: a microSD mount (FAT32) used for its log mirror
  (`port_sdlog.*`, `SdConfig` in `board.hpp`), and Wi-Fi/offline handling.
- To confirm: the V1 board's microSD pins (from Waveshare's V1 schematic), and that the
  slot is wired to the S3 (not shared with something else).

## Single next step

The face plan is written: [docs/FACE_DEVICE_PLAN.md](docs/FACE_DEVICE_PLAN.md). Get the
user's answers to its four choices (text on the face, resting clock, moods from Hermes,
greeting), then start **step 1: `tools/pack_face.py`** and the `wisp_face.bin` format, with
a test that reads it back pixel-exact. Later: the tailnet, record mode, the `diag` label.

Device settings made 2026-11-16 (in the board's flash, not in code): `screen_timeout` 210 s
(dims at ~105 s, dark 60 s after the resting clock appears at 150 s), `clock` 150,
`time_format` 12h, `timezone` Chicago, `volume` 80, `name` Wisp.
