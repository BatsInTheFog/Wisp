# V1 board port: research notes

What it takes to run Hermes Gadget on our **Waveshare ESP32-S3-Touch-AMOLED-1.8 V1**.
Researched 2026-11-15 against:

| Project | Commit read | License |
| --- | --- | --- |
| [Hermes Gadget SDK](https://github.com/Adolanium/hermes-gadget-sdk) | `2ef17f6` (v0.5.0) | MIT |
| [xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) | `1b7644a` | MIT |
| [agent-charm](https://github.com/garavitgabriel/agent-charm) | `57e10cc` | MIT (art has its own license) |

## V1 vs V2: only two chips differ

xiaozhi has a board folder for each revision:
`main/boards/waveshare/esp32-s3-touch-amoled-1.8` (V1) and `...-1.8-v2` (V2).
Comparing them, **every pin, the I2C bus, the TCA9554 reset sequence, the ES8311
codec and the AXP2101 setup are identical**. Only the display and touch chips change:

| | V1 (ours) | V2 (what Gadget supports) |
| --- | --- | --- |
| Display controller | **SH8601**, QSPI 40 MHz, SPI mode 0 | CO5300, QSPI |
| Column offset | **0** | 16 |
| Touch controller | **FT3168** (talks like an FT5x06), I2C 0x38, INT GPIO 21 | CST820, I2C 0x15 |

### Shared pin map (both revisions)

| Part | Connection |
| --- | --- |
| Display QSPI | CS 12, SCLK 11, D0-D3 = 4/5/6/7; no reset GPIO (reset via TCA9554) |
| I2C bus | SDA 15, SCL 14 |
| TCA9554 expander | 0x20. P0 = LCD reset, P1 = display power, P2 = touch reset (outputs); P4 = PWR key (input) |
| ES8311 codec | 0x18. I2S MCLK 16, BCLK 9, WS 45, DOUT 8, DIN 10; speaker amp enable GPIO 46 |
| Microphone | analog mic into the ES8311's own ADC (no ES7210) |
| AXP2101 PMIC | 0x34. ALDO1 3.3 V powers the mic |
| BOOT button | GPIO 0 |
| Audio rate | 24 kHz in and out (xiaozhi) |

### V1 SH8601 start-up table (from xiaozhi's V1 board)

```
0x11 (sleep out), wait 120 ms
0x44 01 D1
0x35 00
0x53 20, wait 10 ms
0x2A 00 00 01 6F   (columns 0..367)
0x2B 00 00 01 BF   (rows 0..447)
0x51 00            (brightness 0), wait 10 ms
0x29 (display on), wait 10 ms
```

Brightness on the AMOLED is the `0x51` command (0-255), not a backlight pin.

## What Hermes Gadget already has

- An `SH8601` QSPI path in `SpiDisplay` (`firmware/esp32/main/port_display.cpp`), used by the
  round 360x360 Knob board. Its start-up table (`panel_sh8601.hpp`) is for that glass, not ours.
- `Ft5x06` touch, already used for the FT3168 on the AMOLED-2.06 watch.
- TCA9554 expander resets (`ExpanderResetConfig`), ES8311 with analog mic (`MicCodec::Es8311`),
  AXP2101 power, BOOT button, PWR key via TCA9554 P4: all used by the V2 profile.
- A `sim-368x448` simulator board with our exact screen size.

## What a V1 port needs

1. A new board profile (Kconfig choice, `board.cpp` entry, `boards/<name>/sdkconfig.defaults`,
   `board.json`). Copy the V2 profile and change display + touch.
2. A way to choose the SH8601 start-up table per board (like `lcd.st77916_panel` does for the
   ST77916), plus the V1 table above.
3. Brightness through the `0x51` command (the `board_backlight` hook), since there is no
   backlight pin.
4. Mark the display `emissive` so the background is true black (pixels off).
5. Touch: FT5x06 at 0x38, INT 21, probably no mirroring; verify on the board.

Estimate: **small**. Roughly 100-250 lines, almost all configuration. The real work is the
first-flash check (colors, offset, touch direction, mic gain), not writing drivers.

## Not usable as-is

- **xiaozhi's board class** is tied to xiaozhi's own `Application`, LVGL setup and MCP server.
  We borrow its **values** (pins, init table, timings), not its code.
- **agent-charm** targets **V2 only** (CO5300/CST820, Arduino_GFX). Useful for ideas
  (honest states, streamed speech, card design), not for V1 bring-up.
- **Gadget's built-in face** is 1-bit, three frames (idle/blink/talk). Wisp's face (colour,
  24 eyes, 13 mouths, warped flame, props) needs its own renderer on top of Gadget.
