# wisp_face.bin: packed face art (version 1)

The device draws Wisp's face from one file, built from `assets/parts` and
`animation_spec.json` by `tools/pack_face.py`, and written to the board's `assets` partition
(0xC30000, 3,904 KB). The device reads it in place from flash.

```
python tools/pack_face.py pack     # -> build/wisp_face.bin (git-ignored)
python tools/pack_face.py check    # read back, compare every part with its PNG
python -m pytest tools/test_pack_face.py
```

Needs Python 3 with numpy and Pillow (pytest for the tests). Without a Python install:
`uv run --no-project --with pillow --with numpy python tools/pack_face.py pack`.

First build (2026-11-16): 133 parts, 2,344,780 bytes (2.24 MB), 1,085,928 of 1,774,614
pixels lit, every part identical to its PNG in RGB565.

## Layout

All numbers little-endian. Offsets are from the start of the file.

### Header (48 bytes)

| Offset | Type | Field |
| --- | --- | --- |
| 0 | 8 bytes | magic `WISPFACE` |
| 8 | u16 | version = 1 |
| 10 | u16 | header size = 48 |
| 12 | u16 | screen width (368) |
| 14 | u16 | screen height (448) |
| 16 | u16 | part count |
| 18 | u16 | name field length = 24 |
| 20 | u32 | part table offset (= 48) |
| 24 | u32 | metadata offset |
| 28 | u32 | metadata length |
| 32 | u32 | pixel data offset (4-byte aligned) |
| 36 | u32 | file size |
| 40 | u32 | CRC-32 (zlib) of bytes 48 to the end |
| 44 | 4 bytes | reserved, 0 |

### Part table (48 bytes per part)

| Offset | Type | Field |
| --- | --- | --- |
| 0 | 24 bytes | name: the PNG's file name without `.png`, NUL-padded (e.g. `eye05L`) |
| 24 | u16, u16 | full part size w, h (as in the manifest; anchors refer to it) |
| 28 | u16, u16 | lit box x, y inside the part |
| 32 | u16, u16 | lit box w, h (0, 0 for an all-black part) |
| 36 | u32 | pixel block offset (0 when empty) |
| 40 | u32 | pixel block size |
| 44 | u32 | lit pixel count |

### Metadata

UTF-8 JSON: `{"manifest": <assets/parts/manifest.json>, "spec": <animation_spec.json>}`.
Parts are found by name: a manifest entry's `file` without `.png`. Anchors (`ax`, `ay`),
offsets (`dx`, `dy`) and the layout come from the manifest; tuning and states from the spec.

### Pixel block (one per part, 4-byte aligned)

- `lit h` x u32: offset of each row's data from the block start.
- Each row: u16 span count, then each span: u16 x (from the lit box's left edge),
  u16 n, then n pixels as u16 RGB565.

Pixels outside spans are black. Black gaps of up to 2 pixels stay inside a span as 0.
Because the art is drawn additively (black adds nothing), black pixels inside a span are
harmless. Colour: `r5 = round(r * 31 / 255)`, `g6 = round(g * 63 / 255)`,
`b5 = round(b * 31 / 255)`, packed `r5 << 11 | g6 << 5 | b5`. The device swaps bytes for the
panel when it draws.

## Changing the format

Bump the version; the firmware refuses versions it doesn't know and falls back to Gadget's
mascot.
