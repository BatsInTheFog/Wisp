# Voice recorder

Wisp records long sessions (longer spoken notes, a few minutes to an hour) to the microSD card and uploads them to a
Nextcloud File drop share, where an n8n workflow transcribes, summarises and files them. Built in
three phases; the user tests each on the device before the next.

| Phase | What | State |
|---|---|---|
| 1 | Record to SD, the recording screen | Flashed 2026-11-17; the user is testing it |
| 2 | Crash safety (`.wav.part`, header every 10 s, repair on boot); Save or Delete after Stop | Done 2026-11-18; the user tested it on the device |
| 3 | Upload queue to Nextcloud, over the tailnet | Done 2026-11-18; works end to end with n8n |

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
  `rec delete`, `rec level reset`. `sd rm <file>` deletes one file on the card.

## Uploads (Phase 3)

- **Route: over the tailnet, straight to Nextcloud on the TrueNAS** (port 9001), not through
  the public address. That address goes through Cloudflare, which refuses uploads over 100 MB
  (~52 min of audio). Checked 2026-11-18 from the PC: a 120 MB test file went through the
  tailnet in 14 s (`TEST_wisp_upload_120MB.mp3`, HTTP 201).
- **Uploads go through the Mac** (changed 2026-11-18, after the first away test). From a
  network away from home, the NAS never answered Wisp's tunnel requests (no reply through the relay or directly;
  at home it worked because the two meet on the LAN). Wisp keeps a live tunnel to the Mac for
  Hermes from anywhere, so the Mac forwards Nextcloud for her:
  `tailscale serve --bg --tcp 9001 tcp://<home LAN address>:9001` (run once on the Mac; it stays on
  across restarts; `tailscale serve --tcp=9001 off` undoes it). The upload address is the
  Mac's tailnet number on port 9001; the bytes pass through untouched, so the NAS's
  certificate (and Wisp's pin on it) is the same, and Nextcloud accepts that address. Uploads
  now need the Mac on, as Hermes does.
- **TLS memory:** the first upload through the Mac broke mid-file with "esp-aes: Failed to
  allocate memory": with TLS buffers in PSRAM, the AES accelerator allocates an internal DMA
  buffer for every record, and internal RAM had dipped to 8.6 KB free (PSRAM: ~580 KB of 8 MB
  free). V1 now uses software AES, and the upload's read buffer is in PSRAM.
- **The board needs the NAS's tailnet number** (100.x), not its `.ts.net` name: those names
  only resolve through Tailscale's own DNS, which TailTiny doesn't give lwIP. And before each
  upload Wisp brings up the WireGuard session with the NAS (`TailnetLink::wake_peer`, the
  handshake TailTiny's own sockets do): lwIP sockets can't reach a tailnet peer without one,
  and only Hermes's is kept up. It took ~10 s the first time.
- **Address:** Nextcloud 35's public WebDAV, `https://<nas>:9001/public.php/dav/files/<share
  token>/<file>`. The old `public.php/webdav/` answers 409 for File drop shares. A share
  without a password needs no login (with one: basic auth, user `anonymous`; untested).
- **Certificate:** Nextcloud on TrueNAS uses TrueNAS's self-signed certificate ("localhost",
  valid to Oct 2027). Wisp trusts exactly that certificate and no other (its name isn't
  checked). If TrueNAS renews it, run `tools/set_upload.py` again.
- **Setup over USB:** `tools/set_upload.py COM3` reads `nextcloud` from the ignored local config
  (`share_token`, `share_password`, `upload_base`), fetches the certificate over the tailnet and
  shows its fingerprint, and sends `set upload_url ...`, `upload cert ...` to the board. The
  token and password are never printed; `get upload_url` on the board says `<set>`.
- **When:** only while Wi-Fi is up and nothing is recording (from triple-press to "Saved"). A
  recording that starts mid-upload stops the upload at once; it starts over later. Oldest
  first, streamed from the card in 8 KB pieces.
- **On screen:** after "Saved" (2 s): "Uploading..." with its percent, then "Sent" (2 s), then the
  face. Offline: "Saved / Will upload when online". A failure: "Will upload later". A long one
  (over 30 s) carries on behind the face. A tap goes back to the face at once. On the face, the
  caption line says "2 recordings waiting" or "Uploading recording 40%".
- **Retries:** 30 s, then doubling, at most 30 min; a new Wi-Fi connection tries at once.
- **After sending:** the file moves to `/recordings/sent/`. Sent files are deleted 14 days after
  they were recorded, or the oldest first when the card has under 2 GB free. A recording that
  hasn't been sent is never deleted.
- **Console:** `upload` (configured, waiting, uploading, percent, sent, failures, last_error,
  retry_in_s), `upload now`, `upload cert begin | add <line> | end | clear`.

## Decisions

- **SD stays in SD mode (SDMMC 1-bit), not SPI** (2026-11-17, the user agreed). Same pins;
  already tested at 1.82 MB/s writing, 57× what recording needs.
- **Uploads go over the tailnet, not the public address** (decided 2026-11-18). The public
  address goes through Cloudflare, which refuses uploads over 100 MB (~52 min of audio); the
  tailnet route to the TrueNAS has no such limit (a 120 MB test went through). Details under
  Uploads.
- The share token and password live only in `config/wisp.local.json` (git-ignored), under
  `nextcloud`, and on the board.

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

Checked 2026-11-18 over USB after flashing Phase 2: the start-up check deleted the two old short
files ("0 recovered, 2 short deleted"). An 11 s recording showed as `.wav.part` at 319,532 bytes
(the 10 s checkpoint: 9.98 s of audio already in its size), asked Save or Delete, and after
`rec save` became `wisp_20261118_023844.wav` (364,812 bytes, 11.4 s). An 8 s one deleted with
`rec delete` left nothing. 0 samples dropped. Still to do on the device: the power-cut test, and
tuning the gain while the user talks.

2026-11-18: the user ran the device tests, including the power cut (held PWR 6 s while
recording): at the restart the check reported "1 recovered", a 61 s file. At the user's request
all recordings on the card were then deleted with `sd rm` (none were to be sent); the folder is
empty. Gain tuning is still to do.

2026-11-18, Phase 3 on the device: `tools/set_upload.py` set the address and the certificate
(SHA-256 `2d:e9:5d:9f:…`). The first upload, the user's 59 s `wisp_20261118_032939.wav`, went
over the tailnet at **218 KB/s** (HTTP 201) and moved to `sent/`. At that speed an hour (115 MB)
takes about 9 minutes; it runs in the background. The n8n workflow picked it up within 5 min:
transcribed, summarised, filed under `Codex/Wisp/Recordings/2026/2026-11/` and announced on
Telegram. It was filed as a general note, because the workflow needs the
recording to open with a spoken name cue.
The user confirmed the whole chain works.
