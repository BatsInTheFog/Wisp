# Wisp's face

Wisp's conversation face: glowing eyes, mouth and a flowing forehead flame on pure black, sized for the 368x448 AMOLED screen.

## What's here

| Path | What it is |
| --- | --- |
| `animation_spec.json` | The tuned face settings. The device firmware must follow this file. |
| `preview/wisp-face-lab.html` | Browser preview of the face. Open it in any browser to see Wisp move. |
| `preview/template.html` | Source of the preview page (the art gets inlined into it). |
| `assets/src/` | The original art sheets the parts are cut from. |
| `assets/parts/` | Eyes, mouths, flame and props cut out and aligned to screen pixels, plus `manifest.json` with every part's anchor point. |
| `tools/slice.py` | Cuts `assets/src` into `assets/parts`. |
| `tools/build_preview.py` | Builds `preview/wisp-face-lab.html` from the template and parts. |

## Rebuilding after art changes

```
python tools/slice.py assets/src assets/parts
python tools/build_preview.py .
```

Needs Python 3 with numpy, scipy and Pillow.

## How the face works

- **Eyes:** 24 expressions (4 rows x 6 on the eye sheet). They blink with eye sets 9 (half) and 14 (closed). Eyes that are already shut skip blinking; Wink blinks only its open eye.
- **Mouths:** 13 shapes. Each has a "ladder" per side: forward, then one or two turned drawings. The mouth squeezes and tilts as Wisp turns, then snaps to the next drawing at set glance points (no cross-fade). Wide uses parallax only. Smirk and Soft smile have their left and right turns swapped; Small has only its first turn swapped.
- **Flame:** one drawing warped row by row so the tip sways and the base stays put. It trails behind head turns and squashes when Wisp looks up.
- **Gaze:** eyes move most, mouth less, flame least. The whole face follows up and down, and looking up lifts the face further.
- **Props:** the browser window (researching) and quill (taking notes) float in the lower right; the quill writes left to right.
- **Mic (listening):** sits centred under her mouth. Its 5 frames are input levels, quiet to loud, not an animation loop. The device picks the frame from the mic level (0-1, RMS of each audio chunk), rising fast (~35 ms) and falling slower (~160 ms), blending between neighbouring frames.
- **States:** idle, listening (mic), thinking, researching, taking notes, speaking (lip sync), success, sad, annoyed, asleep, hearts, excited, wink. Their eyes, mouth, gaze style and flame settings are listed in `animation_spec.json`.
