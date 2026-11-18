# Voice recorder

Wisp records long sessions (longer spoken notes, a few minutes to an hour) to the microSD card and uploads them to a
Nextcloud File drop share, where an n8n workflow transcribes, summarises and files them. Built in
three phases; the user tests each on the device before the next.

| Phase | What | State |
|---|---|---|
| 1 | Record to SD, the recording screen | Flashed 2026-11-17; the user is testing it |
| 2 | Crash safety (`.wav.part`, header every 10 s, repair on boot); Save or Delete after Stop | Built, not yet flashed |
| 3 | Upload queue to Nextcloud | Not started |

## How it behaves (Phase 1)

- **Open:** press BOOT three times quickly (each within 0.4 s of the last). Recording starts at
  once. The first press acts as usual (it starts talking for a moment), the second goes home,
  the third opens the recorder, so single presses get **no added delay**. From a dark screen
  the first press only wakes her, so it takes four.
- **Screen** (replaces the face): red ● REC and the timer (mm:ss, h:mm:ss after an hour) at
  the top; the mic art in the middle, frame 1 (quiet) to 5 (loud) by level; Pause and Stop at
  the bottom.
  - **Pause:** a tap. Shows frame 1 dimmed to 40%, PAUSED in amber, and a blinking timer.
    Resume continues the same file. The timer counts recorded time only.
  - **Stop:** hold for one second while a red ring fills. Letting go early, or sliding off,
    keeps recording.
  - **After Stop: Save or Delete** (added 2026-11-18, the user's design). SAVE fills the top
    half in Wisp's teal in the clock's large font; a tap saves. DELETE is a smaller red button
    below it and needs a one-second hold (it fills from the left), so a brushed screen never
    throws away a long note. The recorded length shows above SAVE. No choice in 60 s: it is
    saved (the countdown shows under SAVE). The keys don't choose. While the choice is up the
    file stays open and paused, so a crash still keeps it.
  - Then "Saving...", then "Saved" with the file name for 2 s (or "Deleted"), then the face. A
    tap or a key press on that message goes back at once.
  - **6 seconds or less is deleted** (recorded time, pauses left out; `kRecordMinKeepS`): the
    screen says "Not kept" without asking Save or Delete. Pocket presses and demos never take
    card space or reach the upload.
- **While open:** BOOT and PWR only brighten the screen; hold-to-talk and taps don't talk
  (the mic is busy); the idle ladder never sleeps her; after 30 s untouched the screen dims,
  and the touch that brightens it does nothing else. At 5% battery (on battery) she stops and
  saves on her own, without asking.

## Crash safety (Phase 2)

- While recording, the file is `wisp_….wav.part`. Every 10 s its WAV header is rewritten with
  the length so far and the card synced, so a dead battery or a pulled card loses at most the
  last ~10 s. When finished it is renamed to `wisp_….wav`.
- At every start-up, before a recording can start, Wisp checks `/recordings`: a leftover
  `.part` gets its header fixed and becomes `.wav` (with `_recovered` added if the name is
  taken), and any recording of 6 s or less is deleted (crash leftovers, and files from before
  the 6 s rule). `rec` reports it as `boot_check`.
- **Mic level → art:** RMS of each 50 ms block in dBFS, −50 dB → frame 1 and −15 dB → frame 5
  (`RecLevel::kQuietDb`, `kLoudDb` in the fork's `core/include/hg/recorder.hpp`). Rises at
  once, falls over ~300 ms (`kReleaseMs`).
- **Files:** `/recordings/wisp_YYYYMMDD_HHMMSS.wav`, the local start time. 16 kHz, 16-bit,
  mono WAV (~115 MB an hour). If the clock was never set: `wisp_unsynced_0001.wav` and up.
  Network time now syncs whenever Wi-Fi is up (it used to only with the clock face on) and
  keeps the PCF85063 set. The timezone is the board's `timezone` setting.

## How it works

- The ES8311 microphone runs at 24 kHz (it shares the clock with the speaker). The mic task
  hands every chunk straight to the recorder before the app's event queue. The recorder
  converts to 16 kHz (low-pass filter, then 3 → 2 samples) into a 1 MB ring buffer in PSRAM
  (~32 s). Its own task ("hg-rec") writes 8 KB blocks to the card. A slow card write is
  absorbed by the ring, not dropped; `rec` reports `dropped` (should stay 0) and the ring's
  peak fill.
- The app keeps the screen. The mic art is packed into `wisp_face.bin` with the face:
  `tools/prep_recorder.py` scales `assets/recorder/rec_mic_*.png` (368×488) to 226×300 into
  `assets/parts/`, and `tools/pack_face.py` adds them under the manifest's `recorder` key.
  The file grew from 2.34 MB to 2.59 MB (the assets partition holds 3.9 MB).
- **Console** (USB): `rec` shows state, seconds, the level now and its peak (`db`,
  `peak_db`: for tuning the gain), `dropped`, `ring_peak_pct`, the file and `boot_check`. Also
  `rec start`, `rec pause`, `rec resume`, `rec stop` (asks Save or Delete), `rec save`,
  `rec delete`, `rec level reset`.

## Decisions

- **SD stays in SD mode (SDMMC 1-bit), not SPI** (2026-11-17, the user agreed). Same pins;
  already tested at 1.82 MB/s writing, 57× what recording needs.
- **Upload over Cloudflare has a 100 MB limit.** The Nextcloud server is behind Cloudflare
  (Nextcloud 35.0.3), which rejects request bodies over 100 MB on its standard plans: about
  52 minutes of audio in one PUT. The user is fine with uploading straight into Nextcloud
  instead. Decide in Phase 3, after a 60 MB and a 120 MB test upload from the PC. The options:
  - upload over the tailnet to Nextcloud directly, skipping Cloudflare (if Nextcloud is on
    the tailnet);
  - split long recordings into parts;
  - raise the limit, if the Cloudflare plan allows.
- The share token and password live only in `config/wisp.local.json` (git-ignored), under
  `nextcloud`. Nextcloud 35 may not keep the old `public.php/webdav/` address; the upload
  address is a setting there, and the Phase 3 test tries both forms.

## Phase 1 tests on the device

Checked 2026-11-17 over USB: `rec start` records to `wisp_20261117_175741.wav` (local time,
so the timezone and clock are right), 0 samples dropped; a 3 s test was deleted on stop. A quiet
room reads about −63 dBFS. Two ~6 s files from the user's first tries (on the firmware before
the 6 s rule) are still on the card.

1. Flash the firmware and the new `wisp_face.bin`, and set the timezone (`set timezone
   CST6CDT,M3.2.0,M11.1.0`).
2. Triple-press BOOT: the recorder opens and the timer runs.
3. Talk across a table; check `rec`: `peak_db` around −25 to −20 dB is mid-scale. Tune the
   gain if not.
4. Pause and resume; hold Stop; check the file with `sd ls /sdcard/recordings`.
5. Record 5+ minutes; `dropped` must be 0.
6. Copy the WAV off the card and play it.
