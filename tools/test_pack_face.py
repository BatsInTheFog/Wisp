"""Tests for tools/pack_face.py:  python -m pytest tools/test_pack_face.py

Packs the real art from assets/parts and reads it back pixel for pixel, and checks the
encoder on small hand-made parts (empty, single pixel, gaps, CRC)."""
import json
import struct
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import pack_face  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def test_real_art_round_trips_pixel_exact(tmp_path):
    out = tmp_path / "wisp_face.bin"
    stats = pack_face.pack(ROOT / "assets/parts", ROOT / "animation_spec.json", out)
    manifest = pack_face.load_manifest(ROOT / "assets/parts")
    assert stats["parts"] == len(pack_face.manifest_files(manifest))
    # The recorder's five mic frames ride along (tools/prep_recorder.py).
    assert [m["file"] for m in manifest["recorder"]["mic"]] == [f"rec_mic_{i}.png" for i in range(1, 6)]
    assert pack_face.check(ROOT / "assets/parts", out) == 0
    meta, _ = pack_face.read(out)
    assert meta["spec"] == json.loads((ROOT / "animation_spec.json").read_text(encoding="utf-8"))
    assert meta["screen"] == [368, 448]
    # It must fit the board's assets partition (3,904 KB).
    assert stats["size"] < 3_904 * 1024


def _write_set(tmp_path, images: dict[str, np.ndarray]) -> Path:
    parts = tmp_path / "parts"
    parts.mkdir()
    manifest = {"screen": [368, 448], "items": [{"file": f"{n}.png"} for n in images]}
    for n, rgb in images.items():
        Image.fromarray(rgb.astype(np.uint8), "RGB").save(parts / f"{n}.png")
    (parts / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "spec.json").write_text("{}", encoding="utf-8")
    return parts


def test_edge_cases_round_trip(tmp_path):
    empty = np.zeros((5, 7, 3))
    dot = np.zeros((9, 9, 3))
    dot[4, 8] = (255, 128, 1)
    gaps = np.zeros((3, 40, 3))
    gaps[1, [0, 2, 5, 30, 39]] = 200  # a 1-gap (merged), a 2-gap (merged), long gaps (split)
    near_black = np.full((2, 2, 3), 2)  # rounds to 0 in RGB565: nothing lit (3 would round up to green 1)
    parts = _write_set(tmp_path, {"empty": empty, "dot": dot, "gaps": gaps, "near_black": near_black})
    out = tmp_path / "f.bin"
    stats = pack_face.pack(parts, tmp_path / "spec.json", out)
    assert pack_face.check(parts, out) == 0
    _, got = pack_face.read(out)
    assert got["empty"].shape == (5, 7) and not got["empty"].any()
    assert not got["near_black"].any()
    assert stats["lit"] == 1 + 5


def test_spans_merge_short_gaps_only():
    row = np.zeros(40, np.uint16)
    row[[0, 2, 5, 30, 39]] = 1
    assert pack_face.spans(row) == [(0, 6), (30, 1), (39, 1)]


def test_corruption_is_detected(tmp_path):
    parts = _write_set(tmp_path, {"dot": np.full((2, 2, 3), 255)})
    out = tmp_path / "f.bin"
    pack_face.pack(parts, tmp_path / "spec.json", out)
    data = bytearray(out.read_bytes())
    data[-1] ^= 0xFF
    out.write_bytes(bytes(data))
    with pytest.raises(ValueError, match="CRC"):
        pack_face.read(out)


def test_header_layout(tmp_path):
    parts = _write_set(tmp_path, {"dot": np.full((2, 2, 3), 255)})
    out = tmp_path / "f.bin"
    pack_face.pack(parts, tmp_path / "spec.json", out)
    data = out.read_bytes()
    assert data[:8] == b"WISPFACE"
    version, hsize, w, h, count, name_len = struct.unpack_from("<6H", data, 8)
    assert (version, hsize, w, h, count, name_len) == (1, 48, 368, 448, 1, 24)
    size = struct.unpack_from("<I", data, 36)[0]
    assert size == len(data)
