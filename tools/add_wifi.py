"""Add a Wi-Fi network to Wisp over USB, keeping the ones she has (up to 5, tried in order).

The network name is typed normally; the password at a hidden prompt, sent straight to the
board and never printed or saved. Afterwards it lists the saved networks (names only).

    python tools/add_wifi.py COM3

Needs pyserial. The board is not reset (DTR and RTS stay low).
"""
import getpass
import sys
import time

import serial


def ask(s, cmd, want=("@ok", "@error", "@wifi"), limit=8.0):
    s.reset_input_buffer()
    s.write((cmd + "\r\n").encode())
    buf, t0 = "", time.time()
    while time.time() - t0 < limit:
        buf += s.read(4096).decode(errors="replace")
        for line in buf.splitlines():
            if line.startswith(want):
                return line.strip()
    return "(no answer)"


def quoted(v):
    # The console splits on spaces and honours "..." with backslash escapes.
    return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
    ssid = input("Network name (as your phone shows it): ").strip()
    if not ssid:
        sys.exit("No name given; nothing sent.")
    pw = getpass.getpass("Password (hidden; Enter for an open network): ")
    s = serial.Serial()
    s.port, s.baudrate, s.timeout, s.dtr, s.rts = port, 115200, 0.2, False, False
    s.write_timeout = 2
    s.open()
    try:
        r = ask(s, "wifi add " + quoted(ssid) + (" " + quoted(pw) if pw else ""))
        print("add:", r.replace(pw, "<password>") if pw else r)
        print("saved:", ask(s, "wifi list"))
    finally:
        s.close()
        pw = None


if __name__ == "__main__":
    main()
