"""Inline the sliced parts into the preview page as data URIs."""
import base64, json, sys
from pathlib import Path

root = Path(sys.argv[1])
parts = root / "assets" / "parts"
m = json.loads((parts / "manifest.json").read_text())

def uri(f):
    return "data:image/png;base64," + base64.b64encode((parts / f).read_bytes()).decode()

for e in m["eyes"]:
    for s in ("L", "R"):
        e[s]["src"] = uri(e[s].pop("file"))
for x in [x for lad in m["mouthLadders"] for x in [lad["fwd"]] + lad["right"] + lad["left"]] + m["flameFrames"] + [m["flame"]] + [f for fr in m["props"].values() for f in fr]:
    x["src"] = uri(x.pop("file"))

tpl = (root / "preview" / "template.html").read_text()
out = root / "preview" / "wisp-face-lab.html"
out.write_text(tpl.replace("__MANIFEST__", json.dumps(m, separators=(",", ":"))))
print(out, round(out.stat().st_size / 1e6, 2), "MB")
