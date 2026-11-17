"""Scale the recorder's mic art for the screen and list it for the face packer.

    python tools/prep_recorder.py [--src assets/recorder] [--parts assets/parts] [--height 300]

Reads rec_mic_1.png ... rec_mic_5.png (368x488 on black, quiet to loud), scales each to
`height` rows (keeping the shape), sets the faintest near-black pixels to pure black (black is
"nothing" to the packer, so the glow's noise floor doesn't cost space), and writes them to
assets/parts with assets/parts/recorder.json. tools/pack_face.py then packs them into
wisp_face.bin with the face, under the manifest's "recorder" key.

Layout on the 368x448 screen: the REC dot and timer above the mic, the Pause and Stop buttons
below it. The firmware places the mic from recorder.json's "box" (its top-left corner).

Needs Python 3 with numpy and Pillow.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
FRAMES = 5
SCREEN_W = 368
# Channel values at or under this (0..255) become black. RGB565 rounds values under ~4 to zero
# anyway; 6 also drops the faint speckle in the art's background.
FLOOR = 6


def prep(src: Path, parts: Path, height: int, top: int) -> dict:
    items = []
    size = None
    for i in range(1, FRAMES + 1):
        img = Image.open(src / f"rec_mic_{i}.png").convert("RGB")
        w = round(img.width * height / img.height)
        small = np.asarray(img.resize((w, height), Image.LANCZOS)).copy()
        small[small.max(axis=2) <= FLOOR] = 0
        name = f"rec_mic_{i}.png"
        Image.fromarray(small).save(parts / name)
        items.append({"file": name, "w": w, "h": height})
        size = (w, height)
    info = {
        "_comment": "Written by tools/prep_recorder.py. The mic art, quiet (1) to loud (5).",
        "mic": items,
        "box": [(SCREEN_W - size[0]) // 2, top],
    }
    (parts / "recorder.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    return info


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, default=ROOT / "assets" / "recorder")
    ap.add_argument("--parts", type=Path, default=ROOT / "assets" / "parts")
    ap.add_argument("--height", type=int, default=300)
    ap.add_argument("--top", type=int, default=66, help="screen row of the mic's top edge")
    a = ap.parse_args()
    info = prep(a.src, a.parts, a.height, a.top)
    print(f"{len(info['mic'])} frames, {info['mic'][0]['w']}x{info['mic'][0]['h']}, at {info['box']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
