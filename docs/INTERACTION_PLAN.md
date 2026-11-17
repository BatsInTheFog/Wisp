# Wisp interaction plan: buttons, recorder trigger, gestures per screen

_Written 2026-11-16. Items marked **Proposed** wait for a decision; nothing here is built
unless it says **Done**._

## The buttons on the V1 board (as the firmware has them today)

| Button | Wiring | How the firmware reads it | What it does now |
| --- | --- | --- | --- |
| **BOOT** | GPIO 0, straight to the ESP32-S3 | Polled by the app task every ~10 ms, 3 polls to debounce (~30 ms) | **TALK.** Hold to talk, release to send (a press under 350 ms is "too short" and nothing is sent). Two presses within 400 ms: home. BOOT + PWR together: settings. |
| **PWR** (side) | Into the AXP2101 power chip; the chip's cleaned-up level goes to pin P4 of the TCA9554 I/O expander (I2C 0x20) | Read over I2C by the touch task every ~20 ms | **CANCEL.** A short press (on release) stops a recording, closes a card, cancels a turn, closes the conversation, or else opens the dashboard. Hold 2 s: new session. Hold **6 s: the AXP2101 cuts power in hardware** (firmware can't change this). |

The PWR level arrives over I2C, so its timing jitters by up to ~20 ms. BOOT is more precise.

## 1. Recorder on a triple tap of BOOT (Proposed)

**The delay question.** To tell a single tap from a triple tap, the firmware can either:

- **Wait and see.** After each tap, wait for the gap window (~350-400 ms) in case another tap
  follows. Every single tap would then act ~0.4 s late.
- **Act now, undo later (recommended).** The firmware already does this for the double press
  (home). Tap 1 acts at once, as today. Tap 2 within 400 ms goes home, as today. Tap 3 within
  400 ms of tap 2 starts the recorder. **Single taps get no added delay.** The only side effect
  is that tap 1 opens the mic for a moment. A tap is shorter than the 350 ms minimum, so
  nothing is sent, and the "too short" hint would be hidden once a second tap follows.

**After the triple tap:** "Recording in 3... tap to cancel" counts down for 3 s. Tapping the
screen or pressing BOOT or PWR cancels it. Then a clear indicator: a red dot and an mm:ss timer
at the top, with Wisp in her note-taking look (the quill).

**Stopping (proposed):** one press of **BOOT** stops and saves. **PWR also stops and saves**:
a long recording should never be thrown away by one press, so discarding needs a confirmation.
On the screen, a **1.5 s hold** stops and saves; taps are ignored, so a pocket can't stop it.

**Blocker:** there is no recorder yet. Long recordings were planned to go to the microSD card
and upload to Hermes afterwards (PROJECT_STATE.md, "Note taking"). The V1 board's microSD pins
still need confirming from Waveshare's V1 schematic. Suggested order: confirm the SD pins and
mount the card, then record to it (WAV, flushed every few seconds), then this trigger and
screen, then the upload.

## 2. Long press per screen (Proposed)

| Screen | Long press (touch) |
| --- | --- |
| Wisp's face (Ready) | Talk (as now) |
| The current response | Talk (as now) |
| Conversation thread | **Message options** for the message under the finger: *Read it again* (Hermes speaks it), *Ask about this* (starts a turn with that message as context), *Save as note* (Hermes files it). The thread no longer talks on a hold (**Done**, fork `e5cf2ca`). |
| Settings list | What the row does (a one-line help card); a second long press resets the row to its default |
| Profile grid | That profile's details, and "make default" |
| Dozing / clock | Wakes only (**Done** with the idle ladder) |

**BOOT long press as a universal talk button: recommended, yes**, on every screen except where
BOOT is already the select key (the settings menu, a question on screen, the hardware check).
It nearly works that way already. The new case is the thread, where the touch hold now opens
message options, so BOOT becomes the one sure way to talk from there.

## 3. Thread scrolling (**Done**, fork `e5cf2ca`)

Movement past 8 px is a scroll (and cancels the hold); the text follows the finger a line at a
time, and the lift's speed carries on, slowing to a stop (a touch stops it). A swipe down closes
the thread only when it starts in the top strip (the bar and the title); a still hold on the
title there still opens settings.

## Turning the screen off by hand

Today on V1 there's no button for it: PWR is Cancel/Back. Holding PWR for 6 s powers the whole
board off. Options (**Proposed**):

- **PWR short press with nothing to cancel → screen off** (recommended). This takes PWR's last
  fallback away from opening the dashboard. Any touch, BOOT, PWR or a pick-up wakes her (the
  waking input does nothing else).
- A swipe down from the top strip on her face → Dozing.
- A console and Hermes command, `sleep`, for testing and for "goodnight" from Hermes.
