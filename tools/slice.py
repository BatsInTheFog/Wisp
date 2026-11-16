"""Slice the Familiar face art into parts, scaled and anchored to the neutral face.

Output: assets/parts/*.png (black background, additive glow) + assets/parts/manifest.json
Screen: 368x448. All coordinates in the manifest are screen pixels.
"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

SRC = Path(sys.argv[1])          # uploads folder
OUT = Path(sys.argv[2])          # output parts folder
OUT.mkdir(parents=True, exist_ok=True)

W, H = 368, 448
F = {
    "face": "1000049696.png",    # neutral face (layout reference)
    "mouths": "mouths36.png",       # 3 rows x 12: forward, turned right, turned left
    "mouthsHalf": "mouthsC.png",    # 3 rows x 10: gentler turns used as half steps
    "mouthsD": "mouthsD.png",       # 3 rows x 6: rounder fanged style with gentle turns
    "flame": "1000049698.png",
    "flames": "1000049699.png",
    "eyes": "1000049701.png",
    "browser": "props_browser.png",
    "quill": "props_quill.png",
    "mic": "props_mic.png",        # 5 frames, quiet to loud: picked by mic input level, not time
}

def load(name):
    return np.asarray(Image.open(SRC / name).convert("RGB")).astype(np.float32)

def mask(img, thr):
    return img.max(axis=2) > thr

def comps(img, thr, min_area, dil=14):
    raw = mask(img, thr)
    lab, n = ndimage.label(ndimage.binary_dilation(raw, iterations=dil))
    lab = lab * raw   # keep labels only on real pixels -> tight boxes
    out = []
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        if sl is None:
            continue
        area = int((lab[sl] == i).sum())
        if area >= min_area:
            y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
            out.append(dict(x0=x0, x1=x1, y0=y0, y1=y1, area=area,
                            cx=(x0 + x1) / 2, cy=(y0 + y1) / 2))
    return out

def crop_save(img, b, pad, k, name):
    h, w = img.shape[:2]
    x0, y0 = max(0, int(b["x0"] - pad)), max(0, int(b["y0"] - pad))
    x1, y1 = min(w, int(b["x1"] + pad)), min(h, int(b["y1"] + pad))
    c = Image.fromarray(img[y0:y1, x0:x1].clip(0, 255).astype(np.uint8))
    nw, nh = max(1, round((x1 - x0) * k)), max(1, round((y1 - y0) * k))
    c = c.resize((nw, nh), Image.LANCZOS)
    c.save(OUT / f"{name}.png", optimize=True)
    # anchor info in source px relative to crop origin
    return dict(file=f"{name}.png", w=nw, h=nh, ox=x0, oy=y0)

manifest = {"screen": [W, H]}

# ---------- 1. Layout from the neutral face ----------
face = load(F["face"])
parts = comps(face, 60, 2000, dil=14)
parts.sort(key=lambda p: p["area"], reverse=True)
# classify: flame = top-most big part, mouth = lowest, eyes = remaining two by x
by_top = sorted(parts[:4], key=lambda p: p["y0"])
flame_b = by_top[0]
mouth_b = max(parts[:4], key=lambda p: p["y1"])
eyes_b = sorted([p for p in parts[:4] if p is not flame_b and p is not mouth_b], key=lambda p: p["cx"])
assert len(eyes_b) == 2, parts

fx0 = min(p["x0"] for p in parts[:4]); fx1 = max(p["x1"] for p in parts[:4])
fy0 = min(p["y0"] for p in parts[:4]); fy1 = max(p["y1"] for p in parts[:4])
S = min((W * 0.90) / (fx1 - fx0), (H * 0.84) / (fy1 - fy0))   # face px -> screen px
offx = W / 2 - (fx0 + fx1) / 2 * S
offy = H / 2 - (fy0 + fy1) / 2 * S + 6

def to_screen(x, y):
    return [round(x * S + offx, 2), round(y * S + offy, 2)]

eye_w_face = np.mean([e["x1"] - e["x0"] for e in eyes_b])
manifest["layout"] = {
    "scale": S,
    "eyeL": to_screen(eyes_b[0]["cx"], eyes_b[0]["y1"]),     # bottom-centre anchor
    "eyeR": to_screen(eyes_b[1]["cx"], eyes_b[1]["y1"]),
    "mouth": to_screen(mouth_b["cx"], mouth_b["y0"]),       # top-lip anchor: mouths open downward
    "flame": to_screen(flame_b["cx"], flame_b["y1"]),       # bottom tip anchor
}
mouth_w_face = mouth_b["x1"] - mouth_b["x0"]
flame_h_face = flame_b["y1"] - flame_b["y0"]

# ---------- 2. Eye sheet: 4 rows x 12 eyes ----------
eyes = load(F["eyes"])
allc = comps(eyes, 60, 200, dil=8)
allc.sort(key=lambda c: c["cy"])
assert len(allc) == 48, len(allc)
eye_items = []
k_eye = None
for r in range(4):
    big = sorted(allc[r * 12:(r + 1) * 12], key=lambda c: c["cx"])
    base = np.median([b["y1"] for b in big])
    for p in range(6):
        L, R = big[2 * p], big[2 * p + 1]
        pair_cx = (L["cx"] + R["cx"]) / 2
        if k_eye is None:  # first pair = neutral reference
            k_eye = eye_w_face * S / np.mean([L["x1"] - L["x0"], R["x1"] - R["x0"]])
            pair_sep = R["cx"] - L["cx"]
        idx = r * 6 + p
        entry = {"id": idx}
        for side, b, sgn in (("L", L, -1), ("R", R, 1)):
            info = crop_save(eyes, b, 12, k_eye, f"eye{idx:02d}{side}")
            info.update(ax=round((b["cx"] - info["ox"]) * k_eye, 2),
                        ay=round((b["y1"] - info["oy"]) * k_eye, 2),
                        dx=round((b["cx"] - (pair_cx + sgn * pair_sep / 2)) * k_eye, 2),
                        dy=round((b["y1"] - base) * k_eye, 2))
            entry[side] = info
        eye_items.append(entry)
manifest["eyes"] = eye_items

# ---------- 3. Mouths ----------
# Each mouth shape gets a "ladder" of drawings per side: [forward, gentler turn, ..., full turn].
# The preview switches between steps with no fade, so every step is scaled to the same width.
# Sources (all 3 rows: forward, turned toward viewer's right, turned toward viewer's left):
#   mouths36.png  12 shapes, strong turns
#   mouthsC.png   10 shapes, gentler turns (half steps)
#   mouthsD.png    6 shapes, gentle turns, rounder fanged style
def mouth_rows(fname, ncols, dil=12):
    img = load(fname)
    cs = comps(img, 60, 300, dil=dil)
    cs.sort(key=lambda c: c["cy"])
    assert len(cs) == 3 * ncols, (fname, len(cs))
    return img, [sorted(cs[r * ncols:(r + 1) * ncols], key=lambda c: c["cx"]) for r in range(3)]

def width(b):
    return b["x1"] - b["x0"]

def mouth_info(img, b, k, name):
    info = crop_save(img, b, 14, k, name)
    # anchored at the top lip so every mouth opens downward
    info.update(ax=round((b["cx"] - info["ox"]) * k, 2), ay=round((b["y0"] - info["oy"]) * k, 2), dx=0, dy=0)
    return info

M_img, M = mouth_rows(F["mouths"], 12)
C_img, C = mouth_rows(F["mouthsHalf"], 10)
D_img, D = mouth_rows(F["mouthsD"], 6)
k_m = mouth_w_face * S / width(M[0][0])
C_COL = {0: 0, 1: 1, 2: 2, 3: 3, 5: 4, 6: 5, 7: 6, 8: 7, 9: 8, 11: 9}   # mouths36 shape -> mouthsC column
D_TO_M = {1: 2, 2: 4, 3: 5, 4: 7, 5: 11}                              # mouthsD column -> matching mouths36 shape
k_d = k_m * float(np.median([width(M[0][m]) / width(D[0][c]) for c, m in D_TO_M.items()]))

def ladder_from_M(m):
    """forward + C half step (if any) + full turn, all from the original style."""
    fw = k_m * width(M[0][m])
    out = {"fwd": mouth_info(M_img, M[0][m], k_m, f"m{m:02d}_f")}
    for side, r in (("right", 1), ("left", 2)):
        steps = []
        if m in C_COL:
            c = C_COL[m]
            steps.append(mouth_info(C_img, C[r][c], fw / width(C[0][c]), f"m{m:02d}_{side}_half"))
        steps.append(mouth_info(M_img, M[r][m], k_m, f"m{m:02d}_{side}_full"))
        out[side] = steps
    return out

def ladder_from_D(c):
    """the rounder fanged style: forward + gentle turn, then the matching full turn scaled to fit."""
    fw = k_d * width(D[0][c])
    out = {"fwd": mouth_info(D_img, D[0][c], k_d, f"d{c}_f")}
    for side, r in (("right", 1), ("left", 2)):
        steps = [mouth_info(D_img, D[r][c], k_d, f"d{c}_{side}_turn")]
        if c in D_TO_M:
            m = D_TO_M[c]
            steps.append(mouth_info(M_img, M[r][m], fw / width(M[0][m]), f"d{c}_{side}_full"))
        out[side] = steps
    return out

# final mouth list (order = picker order; the preview's state table uses these indexes)
MOUTHS = [
    ("Closed", "M", 0), ("Fang closed", "D", 0), ("Parted", "M", 1), ("Small", "D", 1),
    ("Medium", "M", 3), ("Open", "D", 2), ("Wide", "D", 3), ("Big smile", "M", 6),
    ("Smile", "D", 4), ("Soft smile", "M", 8), ("Smirk", "M", 9), ("Frown", "M", 10), ("Fang frown", "D", 5),
]
ladders = []
for name, src, idx in MOUTHS:
    lad = ladder_from_M(idx) if src == "M" else ladder_from_D(idx)
    lad["name"] = name
    ladders.append(lad)
manifest["mouthLadders"] = ladders

# ---------- 4. Flames ----------
fl = load(F["flame"])
b = max(comps(fl, 60, 2000, dil=14), key=lambda c: c["area"])
k_f = flame_h_face * S / (b["y1"] - b["y0"])
info = crop_save(fl, b, 18, k_f, "flame")
info.update(ax=round((b["cx"] - info["ox"]) * k_f, 2), ay=round((b["y1"] - info["oy"]) * k_f, 2))
manifest["flame"] = info

ff = load(F["flames"])
cs = sorted(comps(ff, 60, 1500, dil=14), key=lambda c: c["area"], reverse=True)[:8]
cs.sort(key=lambda c: c["cx"])
k_ff = flame_h_face * S / np.median([c["y1"] - c["y0"] for c in cs])
frames = []
for i, b in enumerate(cs):
    info = crop_save(ff, b, 16, k_ff, f"flamef{i}")
    info.update(ax=round((b["cx"] - info["ox"]) * k_ff, 2), ay=round((b["y1"] - info["oy"]) * k_ff, 2))
    frames.append(info)
manifest["flameFrames"] = frames

# ---------- 5. Props: 5-frame loops shown low on the screen (browser = researching, quill = notes) ----------
def prop_frames(fname, key, target_w):
    img = load(fname)
    raw = mask(img, 40)
    lab, n = ndimage.label(ndimage.binary_dilation(raw.any(axis=0), iterations=25))
    cols = [s[0] for s in ndimage.find_objects(lab)]
    assert len(cols) == 5, (fname, len(cols))
    rows = np.where(raw.any(axis=1))[0]
    y0, y1 = int(rows.min()), int(rows.max()) + 1
    k = target_w / np.median([c.stop - c.start for c in cols])
    out = []
    for i, c in enumerate(cols):
        sub = img[y0:y1, c.start:c.stop]
        lum = sub.max(axis=2)
        cy, cx = ndimage.center_of_mass(lum)          # brightness centroid keeps frames registered
        b = dict(x0=c.start, x1=c.stop, y0=y0, y1=y1)
        info = crop_save(img, b, 0, k, f"{key}{i}")
        info.update(ax=round(cx * k, 2), ay=round(cy * k, 2))
        out.append(info)
    return out

def level_frames(fname, key, target_h):
    """Frames that represent levels (mic input), anchored at the base so the stand never moves."""
    img = load(fname)
    raw = mask(img, 40)
    # the sound arcs nearly touch the next frame, so split the sheet into 5 equal slots
    w = raw.shape[1]
    boxes = []
    for i in range(5):
        a, b = round(i * w / 5), round((i + 1) * w / 5)
        xs = np.where(raw[:, a:b].any(axis=0))[0] + a
        # drop a neighbour's arc tip: a narrow run of columns that touches the slot's edge
        groups = np.split(xs, np.where(np.diff(xs) > 6)[0] + 1)
        keep = [g for g in groups if not ((g.min() <= a + 1 or g.max() >= b - 2) and len(g) < 40)]
        xs = np.concatenate(keep)
        rows = np.where(raw[:, xs.min():xs.max() + 1].any(axis=1))[0]
        boxes.append(dict(x0=int(xs.min()), x1=int(xs.max()) + 1, y0=int(rows.min()), y1=int(rows.max()) + 1))
    k = target_h / np.median([b["y1"] - b["y0"] for b in boxes])
    out = []
    for i, b in enumerate(boxes):
        info = crop_save(img, b, 3, k, f"{key}{i}")   # tiny pad: neighbouring arcs sit close
        info.update(ax=round(((b["x0"] + b["x1"]) / 2 - info["ox"]) * k, 2), ay=round((b["y1"] - info["oy"]) * k, 2))
        out.append(info)
    return out

manifest["props"] = {
    "browser": prop_frames(F["browser"], "browser", 118),
    "quill": prop_frames(F["quill"], "quill", 112),
    "mic": level_frames(F["mic"], "mic", 92),
}

(OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
print("scale", S, "k_eye", k_eye, "k_m", k_m, "k_f", k_f, "k_ff", k_ff)
print(json.dumps(manifest["layout"]))
