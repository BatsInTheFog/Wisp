# Wisp's face on the device: plan

_Written 2026-11-16. Status: plan only, nothing built yet._

## In short

Wisp's face will replace Gadget's black-and-white mascot on the board, drawn from the same
art (`assets/parts`) and settings (`animation_spec.json`) as the browser preview, so the device
follows what was tuned there. The work goes in five steps, each tested in the desktop simulator
(same screen size) before the board is flashed:

1. **Pack the art** into one file the board can draw from quickly, stored in the board's
   3.8 MB `assets` area.
2. **Draw a still face** (eyes, mouth, flame) in the simulator from that file.
3. **Bring it to life**: port the preview's animation (gaze, blinks, turning mouths, swaying
   flame, props) to the firmware.
4. **Connect it to what Wisp is doing**: listening (with the real mic level), thinking,
   speaking (lip sync from the real voice), success, error, asleep.
5. **Put it on the board**: full 448-row screen, speed tuning, then flash.

A few choices are yours; they're listed at the end.

## What we're working with

**The art.** 133 PNG parts, already cut at screen size and aligned to screen pixels
(`tools/slice.py`), on pure black, drawn additively (black adds nothing, bright parts glow):

| Part | Count | Notes |
| --- | --- | --- |
| Eyes | 24 expressions x left/right | blinks reuse sets 9 (half) and 14 (closed) |
| Mouths | 13 shapes, 33 drawings | a "ladder" per side: forward, then 1-2 turned drawings |
| Flame | 1 drawing (+8 frames, unused in "warp" style) | warped row by row so the tip sways |
| Props | browser x5, quill x5, mic x5 | the mic's 5 frames are input levels |

1.77 million pixels in all. As raw 16-bit colour that's about 3.5 MB: too close to the
3.8 MB `assets` area, and more than the ~5 MB of free PSRAM should hold. But most of every
part is black, which draws as nothing, so the art packs much smaller (the PNGs are 1.9 MB).

**The animation** (`preview/template.html`, `frame()`): each frame clears to black, then adds
the flame (warped per row, trailing head turns), both eyes (scaled for turn and head tilt,
blink frames on top), the mouth (ladder step + squeeze + small rotation), the thinking dots,
and the prop. Gaze wanders per state ("wander", "listen", "think", "research", "notes",
"calm", "still"); breathing, drift and flame pulse keep her alive. All of this is a few
hundred lines of arithmetic and is portable to C++ as is.

**The board.** ESP32-S3 at 240 MHz, 8 MB PSRAM (about 5 MB free), SH8601 screen over QSPI
at 40 MHz. A full 368x448 frame is 330 KB; sending one takes about 16-20 ms, so a full-screen
redraw tops out near 40-50 frames per second before any drawing time. Gadget's screen today
redraws only rows that changed and ticks its animation every 100 ms.

## How it will work

### 1. Pack the art (`tools/pack_face.py`, in this repo)

A new script turns `assets/parts` + `manifest.json` + `animation_spec.json` into one file,
`wisp_face.bin`:

- a header (format version, screen size) and a table of parts with their anchors and offsets
  from the manifest;
- each part cropped to its lit pixels and stored **row by row as runs**: "skip N black
  pixels, then M colour pixels" in 16-bit colour. Black runs cost almost nothing, and
  drawing can jump straight to any row (needed for the flame warp and for squeezing parts);
- the tuned settings from `animation_spec.json` copied in, so the board and the preview
  can't drift apart.

**Built (step 1 done, 2026-11-16):** 2.24 MB, 58% of the `assets` area, every part
pixel-exact; format in [FACE_FORMAT.md](FACE_FORMAT.md). The board reads it in place from
flash (memory-mapped), so it costs no PSRAM. If future art outgrows the area, the options
are shrinking the two 6 MB app slots (the app uses 1.65 MB) or keeping art on the microSD card.

Getting it onto the board: a one-line USB write to the `assets` area (address 0xC30000),
separate from the firmware, so art changes don't need a firmware rebuild. Later, Hermes
could send face updates over the air.

**Step 2 done (2026-11-16, fork `wisp` branch):** `hg::WispFace` reads the file in place
(checks magic, version, size, CRC; parts by name; manifest + spec as JSON), `hg::add_part`
draws a part additively (nearest-pixel scale, alpha, per-row shift, saturating, row clip),
and `hg::WispFaceRenderer::draw_idle(t)` draws the resting face (swaying, breathing,
pulsing flame; neutral eyes; closed mouth) exactly where the preview puts it. On the idle
screen the UI shows it over the whole panel (also behind hidden bars) with "Hi, I'm Wisp"
and one more line near the bottom. The simulator loads the file from the `HG_WISP_FACE`
environment variable on `sim-368x448`; a side-by-side check with the browser preview
matched. 7 new core tests (663 pass). The board doesn't load the file yet (step 5).

**Step 3 done (2026-11-16, fork `2592253`):** `WispFaceRenderer` is now the animator, a C++
port of the preview's `frame()`: the 13 states from the spec (eyes, mouth or lip sync, gaze
mode, flame, props, dots, flare), wandering gaze with saccades and lag, blinks (shut eyes
don't blink; a wink blinks one eye), mouth ladders with hysteresis and tilt
(`add_part_rotated`), the flame trailing head turns and squashing when she looks up, props
fading in and out (quill writing, level-driven mic), thinking dots. The app steps it at
~30 fps while the face is on screen and redraws only the face. Console `face <state>`
forces a state for testing (`face auto` to return). Checked: all 13 states rendered in the
simulator (contact sheet), the idle face moves between frames, 7 new tests (670 pass).
Open for step 4: the listening mic sits at the bottom (micY 440) where the two text lines go.

**Step 4 done (2026-11-16, fork `2b74467`):** the app picks the face per screen: Ready idle
(happy 2.5 s after an answer, showing the reply's last two lines; sad 4 s after a failure),
listening with the real mic level, thinking or research (Hermes's status mentions search/web/
browse/look), speaking while the reply plays, asleep on the resting clock; other screens keep
the mascot. With the face, a finished reply no longer fills the screen for 20 s (swipe up
for the text). User's prop request: browser, quill and mic stand just above the two text
lines, the mic on the right like the browser. Resting clock: Wisp asleep at 62% in the top
half, time and date in the bottom half, battery icon + percentage in a bottom strip the
bar's height (user request; board setting `battery_display both`). 5 new app tests (675
pass); a spoken turn in the simulator went idle → listening → thinking → speaking → happy
→ idle → asleep with the clock. **Not done:** lip sync uses the preview's made-up
syllables while audio plays, not the real loudness (to add in step 5 if it reads poorly);
the `wisp.mood` action for Hermes (later); the percentage is the AXP2101's own gauge, with
no fitted curve for this battery yet, so it may read a little off.

**Step 5 in progress (2026-11-16):** the port maps the `assets` partition and passes it to
the app; the V1 UI uses all 448 rows (fork `b410574`). `wisp_face.bin` was written to
0xC30000 (hash verified) and the firmware flashed. **First boot looped:** the face loaded
(CRC check ~0.6 s), then `abort()` in the USB console's start-up: a lock allocation failed
because internal RAM was used up by the parsed manifest/spec JSON (thousands of small
allocations, which ESP-IDF keeps in internal RAM). Fix (fork, committed): free the parsed
JSON once the renderer has copied its numbers (`WispFace::drop_metadata`, fork `86a6af9`).
**Flashed: the board stays up, online and paired, showing the face.** But internal RAM
dipped to 496 bytes at start-up (now 119 KB free, was 168 KB), and frame timing (`perf`)
showed ~118 ms a frame (~8 fps: render ~92 ms, flush ~27 ms), with the app task so busy the
console took 15 s to answer. Fixes (fork `afb00cb`, built, 675 tests pass, simulator shows no
leftover pixels): fixed-point column stepping (no per-pixel division); clear and redraw only
the rows the face changed; pace the face (at most every 33 ms, 100 ms on the clock, and a
slow frame waits as long again); small allocations to PSRAM while the metadata is parsed.
Flashed `afb00cb`: no restarts; lowest internal RAM 88 KB (was 496 bytes); frame ~75 ms
(render ~56 ms, flush ~19 ms), so with pacing ~6-7 fps. The user is fine with a lower frame
rate. The board's console didn't know `face` (the port registers commands by name).
Next build (fork `e2ae49b`, 675 tests pass): art copied to PSRAM at start-up (the flash reads
in DIO), a faster `Canvas::blit`, `face` registered on the console. **Flashed:** no restarts;
frame ~56 ms (render ~37 ms, flush ~19 ms, p95 59 ms), so with pacing **~9 fps, steady**,
leaving the app task half its time; console answers in ~1 s; lowest internal RAM 88 KB;
PSRAM 2.4 MB free with the art copy. Accepted as the board's rate for now (user is fine
with a lower rate). Possible later gains: render on the second core, fewer moving rows.

**User test on the board (2026-11-16):** everything works; animations felt slow and the
speaking mouth looked poor. Causes and fixes (fork `e1c77f8`, 676 tests pass, built; needs
an OK to flash): (1) each animation step was clamped to 50 ms as in the preview, so at
~110 ms a frame everything ran under half speed: now long frames advance in 50 ms sub-steps;
(2) lip sync now follows the real reply audio: each 20 ms of audio written to the speaker
gets a loudness and the time it will be heard (after the queue, plus `kLipLatencyMs` = 60,
to tune by eye); each frame takes the loudest chunk heard since the last frame, scaled to a
decaying recent peak; closed between bursts.

Flashed `e1c77f8`. User: mouth slightly behind the speech; animation still low frame rate.
Next build (fork `4d16a33`, 676 tests pass, built; needs an OK to flash): the mouth takes the
sound playing when the frame reaches the screen (now + the last frame's draw-and-send time),
`kLipLatencyMs` 60 → 0; pacing waits a quarter of a slow frame's time instead of all of it
(~13-15 fps expected at ~56 ms frames); pixels read as aligned 16-bit words. If still not
smooth: render on the second core.

**Performance review (2026-11-16, board on `e1c77f8`):** frame 61 ms = **draw 42 ms (~70%)**
+ **send 19 ms (~30%)**, ~8 fps (pacing waited as long again). Screen clock: SH8601 QSPI at
**40 MHz** (Gadget's AMOLED default; xiaozhi's V1 also uses 40). Sending is serial: one
16-row DMA bounce buffer, copy then wait per band, no overlap. Caps: the face's own minimum
33 ms; Gadget's 100 ms model tick doesn't limit the face. Reviewed the user's 7 suggestions;
order proposed (awaiting the user): measure `4d16a33` as baseline, then 80 MHz QSPI, a 30 fps "mouth lane"
between full frames, then overlapped sending / second core. Already done: art as RGB565
from a dedicated partition, copied to PSRAM; lip sync stamped at play time.

**Measured step by step on the board (2026-11-16):**

| Step (fork commit) | Idle fps | Speaking: full + mouth frames/s | Notes |
| --- | --- | --- | --- |
| Before (`e1c77f8`) | ~8 | ~8 + 0 | draw 42 ms, send 19 ms |
| 1. Lip aim + lighter pacing (`4d16a33`) | 13.5 | 11.6 + 0 | draw 37, send 19 |
| 2. QSPI 80 MHz (in `212c239`) | 14.9 | 13.2 + 0 | send 19 → 13 ms; image check by the user pending |
| 3. Mouth lane (`212c239`) | 13.6 | 5.2 + 0.8 | full frames while speaking cost too much to leave gaps |
| Breakdown + text rows only (`e5ab93c`) | 14.9 | 6.1 + 2.9 | text changes had forced whole-band redraws (31 of 66) |
| Mouth band from the drawings (`44de5b1`) | 14.9 | 6.5 + 4.4 | the band reached the eyes; mouth compose 32 → 17 ms |
| Faster turned mouth, no flame in the band (`7eee4b8`) | 16.9 | 7.3 + 5.6 = 12.9 | mouth compose 4.9 ms |
| 4. Compose on the second core (`4677d2b`) | **17.5** | **7.1 + 9.2 = 16.3** | worker compose 21 / 17 ms; showing a frame on the app task 26 / 38 ms |

Breakdown now (idle / speaking): compose 20.7 / 30.1 ms, copy into the display buffer
(PSRAM → PSRAM) 7.0 ms, text 0.4-0.5 ms, send 12.7 ms. While speaking, a full frame takes
~55-80 ms of wall time (audio and Wi-Fi tasks preempt the app task), leaving room for about
one mouth frame between full frames.

Step 4 (2026-11-16): a task pinned to core 1 composes each face frame; the app task steps the
face, hands the job over, leaves the renderer and face buffer alone until it is done, then
shows the frame (copy + send) and starts the next. Strict turn-taking with one face buffer,
so compose (~21 ms) and show (~26 ms idle, ~38 ms speaking) still add up per frame (~47 ms,
so ~21 fps at best). The mouth lane is no longer starved (9.2 mouth frames/s). Possible next
gains: a second face buffer so the next frame composes while the last one is shown (~330 KB
PSRAM), and composing straight into the display buffer to drop the ~7 ms copy.

Flashing note: use the plain `pio run -e esp32s3-touch-amoled-18-v1 -t upload`; adding
`-t nobuild` makes PlatformIO write the app at its default 0x10000 instead of this board's
0x20000, and the board then boot-loops until it is flashed again the normal way.

### 2-3. Draw and animate (`FaceRenderer` in the firmware core)

A new part of Gadget's portable core (so the simulator runs exactly the same code):

- **Drawing**: additive blending of parts into the frame, with nearest-pixel scaling for the
  squeezes, tilt and prop sizes, a per-row offset for the flame warp, and a small rotation
  for the mouth. Brightness (flame pulse, prop fade-in) is a multiply on the way in.
- **Animation**: a direct C++ port of the preview's state machine (gaze targets per mode,
  saccades and lag, blinks, mouth ladder with hysteresis, flame size/brightness/speed easing,
  quill path, mic level smoothing, thinking dots), reading its numbers from the packed file.
- **Speed**: the face gets its own faster tick (target 25-30 frames per second), and redraws
  only the box the face covers, skipping rows that didn't change. Gadget's existing frame
  statistics (`set frame_stats on`, `perf`) measure it on the board.
- **Checking it**: the simulator renders frames at fixed times; we compare them side by side
  with the browser preview at the same settings before going near the board.

### 4. What Wisp shows, and when

| Gadget screen | Wisp's state | Driven by |
| --- | --- | --- |
| Ready (idle) | idle: neutral, wandering gaze, blinks | |
| Listening | listening: wide eyes, **mic prop** | the real microphone level (already measured by Gadget) |
| Thinking | thinking: skeptical, eyes up-right, dots | |
| Thinking, with a "searching" status from Hermes | research: side-eye, **browser prop** | Hermes's status phrase |
| Responding (speaking) | speaking: **lip sync** | the loudness of the audio being played (new: measured as it goes to the speaker) |
| Reply finished OK | success: happy, flame flare, briefly | `turn.end` success |
| Reply failed / error | sad, briefly | `turn.end` failure, errors |
| Screen dimmed / resting | sleepy: eyes shut, low flame | Gadget's dim / doze |
| Note taking (later) | notes: **quill prop** | record mode or a note tool |
| Moods (love, excited, wink, annoyed) | on request | a device action Hermes can call (optional) |

Everything else (settings, Wi-Fi setup, pairing, offline, the conversation view) keeps
Gadget's normal screens.

### 5. On the board

- Switch the V1 profile to the **full 368x448 glass** (`amoled.height = 448`, `gap_y = 0`,
  `touch.offset_y = 0`); the face spec is laid out for 448 rows.
- Flash the firmware, write `wisp_face.bin` to the `assets` area, measure frame rate and
  memory, then tune (smaller redraw box, a faster screen clock if the SH8601 allows it).
- If the art file is missing or damaged, the board falls back to Gadget's mascot, so a bad
  art write never leaves a blank screen.

## Order of work and checkpoints

| Step | Done when | Flash? |
| --- | --- | --- |
| 1. Packer + file format | `wisp_face.bin` builds; a test reads it back pixel-exact against the PNGs | no |
| 2. Still face in the simulator | the simulator shows the idle face matching a preview screenshot | no |
| 3. Animation | simulator frames match the preview at the same times and states | no |
| 4. States + lip sync + mic | the simulator talking to Hermes shows each state at the right moment | no |
| 5. Board | face on the board at a smooth frame rate, memory healthy; you approve each flash | yes, with your OK |

Each step ends with a commit to the fork (`wisp` branch) and this repo, and PROJECT_STATE.md
updated.

## Risks

- **Speed.** Full-screen additive drawing every frame may be too slow; the fixes are redrawing
  only what changed, a smaller face box, or a lower frame rate for the flame than the eyes.
- **Lip sync timing.** Sound plays from a buffer, so the mouth must lag the audio sent to
  the speaker by about the buffer length; to be tuned by eye.
- **Upstream changes.** This adds a sizeable feature to the fork; pulling future Gadget
  updates may need small merges in the UI code.

## Decisions (2026-11-16)

1. **Text on the face screen:** up to **two lines**, toward the **bottom** of the screen, so
   the animation keeps its full size. Where text and art overlap, the **text draws on top**.
   (Reply lines while she speaks, notices, the greeting.)
2. **Resting clock:** **Wisp asleep in the top half**, the **time in the bottom half**
   (replaces Gadget's clock face; same timing, dimming and burn-in shift rules).
3. **Moods from Hermes:** yes, my call on the details. Plan: one device action,
   `wisp.mood`, with `love`, `excited`, `wink`, `annoyed` (and `success` / `sad`), shown for
   a few seconds and then back to the normal state; Hermes sees its description and can use
   it when it fits. Low priority: after the main states work.
4. **Greeting:** Wisp's own, near the bottom of the screen (wording to settle at step 4;
   the device name "Wisp" is already set).
