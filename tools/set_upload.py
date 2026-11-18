"""Tell Wisp where to upload recordings, over USB: the Nextcloud share's address and its certificate.

    python tools/set_upload.py            # uses serial_port from the local config
    python tools/set_upload.py COM3

Reads config/wisp.local.json's "nextcloud" entry:
  share_token     the text after /s/ in the share link
  share_password  the share's password ("" for none)
  upload_base     the server's WebDAV address for public shares, reached over the tailnet,
                  e.g. https://<nas>.<tailnet>.ts.net:9001/public.php/dav/files/

It fetches the server's certificate (over the tailnet, from this PC), shows its SHA-256
fingerprint, and sends the board:
  set upload_url <upload_base><share_token>/
  set upload_pass <password>          (only when the share has one)
  upload cert begin / add <line>... / end
Wisp then trusts that certificate and no other for uploads. The token and password are never
printed. Run it again if the server's certificate changes (TrueNAS's runs to Oct 2027).

Needs pyserial. The board is not reset (DTR and RTS stay low).
"""
import hashlib
import json
import socket
import ssl
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import serial

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "wisp.local.json"


def ask(s, cmd, want=("@ok", "@error", "@upload"), limit=8.0):
    s.reset_input_buffer()
    s.write((cmd + "\r\n").encode())
    buf, t0 = "", time.time()
    while time.time() - t0 < limit:
        buf += s.read(4096).decode(errors="replace")
        for line in buf.splitlines():
            if line.startswith(want):
                return line.strip()
    return "(no answer)"


def fetch_cert(host, port):
    # Not verified here: this is how we learn the certificate, over the tailnet to our own NAS.
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with socket.create_connection((host, port), timeout=10) as raw:
        with ctx.wrap_socket(raw, server_hostname=host) as tls:
            der = tls.getpeercert(binary_form=True)
    return ssl.DER_cert_to_PEM_cert(der), hashlib.sha256(der).hexdigest()


def main():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
    nc = cfg.get("nextcloud", {})
    port = sys.argv[1] if len(sys.argv) > 1 else cfg.get("serial_port", "")
    token, pw, base = nc.get("share_token", ""), nc.get("share_password", ""), nc.get("upload_base", "")
    if not port or "?" in port:
        sys.exit("No serial port: pass it (e.g. COM3) or set serial_port in config/wisp.local.json")
    if not token or not base.startswith("https://") or not base.endswith("/"):
        sys.exit('config/wisp.local.json needs nextcloud.share_token and nextcloud.upload_base (https://.../)')
    u = urlparse(base)
    pem, fp = fetch_cert(u.hostname, u.port or 443)
    print(f"server certificate SHA-256: {':'.join(fp[i:i + 2] for i in range(0, len(fp), 2))}")
    body = [l for l in pem.strip().splitlines() if not l.startswith("-----")]

    s = serial.Serial()
    s.port, s.baudrate, s.timeout, s.dtr, s.rts = port, 115200, 0.2, False, False
    s.write_timeout = 2
    s.open()
    try:
        r = ask(s, "set upload_url " + base + token + "/")
        print("upload_url:", "saved" if r.startswith("@ok") else r.replace(token, "<token>"))
        if pw:
            r = ask(s, "set upload_pass " + pw)
            print("upload_pass:", "saved" if r.startswith("@ok") else r.replace(pw, "<password>"))
        r = ask(s, "upload cert begin")
        for line in body:
            r = ask(s, "upload cert add " + line)
            if not r.startswith("@ok"):
                break
        if r.startswith("@ok"):
            r = ask(s, "upload cert end")
        print("certificate:", r)
        print("status:", ask(s, "upload", want=("@upload", "@error")).replace(token, "<token>"))
    finally:
        s.close()


if __name__ == "__main__":
    main()
