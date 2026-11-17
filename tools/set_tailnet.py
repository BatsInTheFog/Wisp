"""Put Wisp on the tailnet over USB: the Tailscale auth key, the Hermes address, tailnet on.

The key is typed at a hidden prompt and goes straight to the board: it is never printed,
logged or saved to a file. The Hermes address comes from config/wisp.local.json
("hermes_url_away", the Mac's ws://100.x.y.z:8765/gadget address), and the serial port from its
"serial_port" (or the first argument).

    python tools/set_tailnet.py            # uses serial_port from the local config
    python tools/set_tailnet.py COM3

Needs pyserial. The board is not reset (DTR and RTS stay low).
"""
import getpass
import json
import sys
import time
from pathlib import Path

import serial

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "wisp.local.json"


def ask(s, cmd, want=("@ok", "@error"), limit=8.0):
    s.reset_input_buffer()
    s.write((cmd + "\r\n").encode())
    buf, t0 = "", time.time()
    while time.time() - t0 < limit:
        buf += s.read(4096).decode(errors="replace")
        for line in buf.splitlines():
            if line.startswith(want):
                return line.strip()
    return "(no answer)"


def main():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
    port = sys.argv[1] if len(sys.argv) > 1 else cfg.get("serial_port", "")
    url = cfg.get("hermes_url_away", "")
    if not port or "?" in port:
        sys.exit("No serial port: pass it (e.g. COM3) or set serial_port in config/wisp.local.json")
    if not url.startswith("ws://100."):
        sys.exit("config/wisp.local.json needs hermes_url_away = ws://<Mac tailnet IP>:8765/gadget")
    key = getpass.getpass("Tailscale auth key (hidden): ").strip()
    if not key.startswith("tskey-"):
        sys.exit("That doesn't look like a Tailscale auth key (it starts with tskey-). Nothing sent.")
    s = serial.Serial()
    s.port, s.baudrate, s.timeout, s.dtr, s.rts = port, 115200, 0.2, False, False
    s.write_timeout = 2
    s.open()
    try:
        r = ask(s, "set ts_key " + key)
        print("ts_key:", "saved" if r.startswith("@ok") else r.replace(key, "<key>"))
        if not r.startswith("@ok"):
            return
        print("server:", ask(s, "set server " + url))
        print("tailnet:", ask(s, "set tailnet on"))
        print("check:", ask(s, "get ts_key", want=("@value", "@error")))
    finally:
        s.close()
        key = None
    print("Done. Watch the screen: 'Joining tailnet', then 'Reaching Hermes over the tailnet'.")


if __name__ == "__main__":
    main()
