"""Pack Wisp's face art into one file the device can draw from: wisp_face.bin.

    python tools/pack_face.py pack  [--parts assets/parts] [--spec animation_spec.json] [--out build/wisp_face.bin]
    python tools/pack_face.py check [--parts assets/parts] [--file build/wisp_face.bin]

`pack` reads every part listed in assets/parts/manifest.json, converts it to 16-bit colour
(RGB565) and stores only its lit pixels, row by row, with the manifest and animation_spec.json
embedded as JSON. `check` reads the file back and compares every part, pixel for pixel, with
the PNG it came from. The format is described in docs/FACE_FORMAT.md.

Needs Python 3 with numpy and Pillow.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import zlib
from pathlib import Path

import numpy as np
from PIL import Image

MAGIC = b"WISPFACE"
VERSION = 1
HEADER = struct.Struct("<8sHHHHHHIIIIII4x")  # 48 bytes, see docs/FACE_FORMAT.md
PART = struct.Struct("<24sHHHHHHIII")          # 48 bytes
NAME_LEN = 24
MERGE_GAP = 2  # black gaps this short stay inside a span: cheaper than a new span header

assert HEADER.size == 48 and PART.size == 48


def to565(rgb: np.ndarray) -> np.ndarray:
    """H x W x 3 uint8 -> H x W uint16 RGB565, rounded to nearest."""
    r = (rgb[..., 0].astype(np.uint32) * 31 + 127) // 255
    g = (rgb[..., 1].astype(np.uint32) * 63 + 127) // 255
    b = (rgb[..., 2].astype(np.uint32) * 31 + 127) // 255
    return ((r << 11) | (g << 5) | b).astype(np.uint16)


def load565(path: Path) -> np.ndarray:
    return to565(np.asarray(Image.open(path).convert("RGB")))


def manifest_files(manifest: dict) -> list[str]:
    """Every part file the manifest references, in first-seen order."""
    out: list[str] = []

    def walk(o):
        if isinstance(o, dict):
            if "file" in o and o["file"] not in out:
                out.append(o["file"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(manifest)
    return out


def spans(row: np.ndarray) -> list[tuple[int, int]]:
    """(start, length) of lit runs in one row, short black gaps merged in."""
    lit = np.flatnonzero(row)
    if lit.size == 0:
        return []
    out = []
    start = prev = int(lit[0])
    for x in lit[1:]:
        x = int(x)
        if x - prev - 1 > MERGE_GAP:
            out.append((start, prev - start + 1))
            start = x
        prev = x
    out.append((start, prev - start + 1))
    return out


def encode_part(img: np.ndarray) -> tuple[tuple[int, int, int, int], bytes, int]:
    """Crop to the lit box and encode. Returns (crop_x, crop_y, crop_w, crop_h), block, lit count."""
    h, w = img.shape
    ys, xs = np.nonzero(img)
    if ys.size == 0:
        return (0, 0, 0, 0), b"", 0
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
    crop = img[y0:y1, x0:x1]
    ch = y1 - y0
    rows = []
    for r in crop:
        sp = spans(r)
        b = bytearray(struct.pack("<H", len(sp)))
        for sx, n in sp:
            b += struct.pack("<HH", sx, n)
            b += r[sx:sx + n].astype("<u2").tobytes()
        rows.append(bytes(b))
    table = bytearray()
    offset = 4 * ch
    for b in rows:
        table += struct.pack("<I", offset)
        offset += len(b)
    return (x0, y0, x1 - x0, ch), bytes(table) + b"".join(rows), int(np.count_nonzero(img))


def pad4(n: int) -> int:
    return (n + 3) & ~3


def pack(parts_dir: Path, spec_path: Path, out: Path) -> dict:
    manifest = json.loads((parts_dir / "manifest.json").read_text(encoding="utf-8"))
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    screen_w, screen_h = manifest["screen"]
    files = manifest_files(manifest)

    meta = json.dumps({"manifest": manifest, "spec": spec}, separators=(",", ":")).encode("utf-8")
    parts_offset = HEADER.size
    meta_offset = parts_offset + PART.size * len(files)
    data_offset = pad4(meta_offset + len(meta))

    entries, blocks = [], []
    cursor = data_offset
    stats = {"parts": len(files), "lit": 0, "pixels": 0}
    for name in files:
        stem = Path(name).stem
        if len(stem.encode()) >= NAME_LEN:
            raise SystemExit(f"part name too long for the format: {stem}")
        img = load565(parts_dir / name)
        h, w = img.shape
        (cx, cy, cw, ch), block, lit = encode_part(img)
        entries.append(PART.pack(stem.encode(), w, h, cx, cy, cw, ch, cursor if block else 0, len(block), lit))
        padded = block + b"\0" * (pad4(len(block)) - len(block))
        blocks.append(padded)
        cursor += len(padded)
        stats["lit"] += lit
        stats["pixels"] += w * h

    body = b"".join(entries) + meta + b"\0" * (data_offset - meta_offset - len(meta)) + b"".join(blocks)
    size = HEADER.size + len(body)
    crc = zlib.crc32(body) & 0xFFFFFFFF
    header = HEADER.pack(MAGIC, VERSION, HEADER.size, screen_w, screen_h, len(files), NAME_LEN,
                         parts_offset, meta_offset, len(meta), data_offset, size, crc)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(header + body)
    stats.update(size=size, meta=len(meta), crc=crc)
    return stats


def read(path: Path) -> tuple[dict, dict[str, np.ndarray]]:
    """Parse a packed file: (meta, {part name: full-size H x W uint16 image})."""
    data = path.read_bytes()
    (magic, version, hsize, sw, sh, count, name_len, parts_off, meta_off, meta_len,
     data_off, size, crc) = HEADER.unpack_from(data, 0)
    if magic != MAGIC or version != VERSION or hsize != HEADER.size or name_len != NAME_LEN:
        raise ValueError("not a version 1 Wisp face file")
    if size != len(data):
        raise ValueError(f"size {len(data)} != header {size}")
    if zlib.crc32(data[HEADER.size:]) & 0xFFFFFFFF != crc:
        raise ValueError("CRC mismatch")
    meta = json.loads(data[meta_off:meta_off + meta_len])
    parts = {}
    for i in range(count):
        name, w, h, cx, cy, cw, ch, off, bsize, _lit = PART.unpack_from(data, parts_off + i * PART.size)
        name = name.rstrip(b"\0").decode()
        img = np.zeros((h, w), np.uint16)
        for y in range(ch):
            pos = off + struct.unpack_from("<I", data, off + 4 * y)[0]
            (n,) = struct.unpack_from("<H", data, pos)
            pos += 2
            for _ in range(n):
                sx, cnt = struct.unpack_from("<HH", data, pos)
                pos += 4
                img[cy + y, cx + sx:cx + sx + cnt] = np.frombuffer(data, "<u2", cnt, pos)
                pos += 2 * cnt
        parts[name] = img
    meta["screen"] = [sw, sh]
    return meta, parts


def check(parts_dir: Path, path: Path) -> int:
    manifest = json.loads((parts_dir / "manifest.json").read_text(encoding="utf-8"))
    meta, parts = read(path)
    bad = 0
    files = manifest_files(manifest)
    for name in files:
        want = load565(parts_dir / name)
        got = parts.get(Path(name).stem)
        if got is None or got.shape != want.shape or not np.array_equal(got, want):
            print(f"MISMATCH {name}")
            bad += 1
    if meta["manifest"] != manifest:
        print("MISMATCH embedded manifest")
        bad += 1
    print(f"checked {len(files)} parts: {'all match' if not bad else f'{bad} differ'}")
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pack")
    p.add_argument("--parts", type=Path, default=Path("assets/parts"))
    p.add_argument("--spec", type=Path, default=Path("animation_spec.json"))
    p.add_argument("--out", type=Path, default=Path("build/wisp_face.bin"))
    c = sub.add_parser("check")
    c.add_argument("--parts", type=Path, default=Path("assets/parts"))
    c.add_argument("--file", type=Path, default=Path("build/wisp_face.bin"))
    a = ap.parse_args(argv)
    if a.cmd == "pack":
        s = pack(a.parts, a.spec, a.out)
        print(f"wrote {a.out}: {s['size']:,} bytes ({s['size'] / 1024 / 1024:.2f} MB), {s['parts']} parts, "
              f"{s['lit']:,} of {s['pixels']:,} pixels lit, metadata {s['meta']:,} bytes, crc {s['crc']:08x}")
        return 0
    return check(a.parts, a.file)


if __name__ == "__main__":
    sys.exit(main())
