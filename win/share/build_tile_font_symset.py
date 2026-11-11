#!/usr/bin/env python3
"""Generate a NetHack symset to use with a tile font.

Usage:
  uv run build_tile_font_symset.py

Optional:
  --tilemap   util/tilemappings.lst (written by NetHack's util/tilemap)
  --nethack   the nethack binary (for --dumpglyphnames)
  --name      the name for the symbol set
  --out       the file to write to

The output needs to be appended to the symbols file, either in the
source code, or in an installed nethack directory.
"""
import argparse
import re
import os
import subprocess
from pathlib import Path

BASE_CP = 0x100000
GLYPH_RE = re.compile(r"^glyph\[(\d+)\] \[(\d+)\] (.*?)\s*$")
NAME_RE = re.compile(r"^\((\d+)\) (G_\S+)")
SKIP_TILE_NAMES = {"stone"}


def main():
    script_dir = os.path.dirname(os.path.realpath(__file__))

    ap = argparse.ArgumentParser()
    ap.add_argument("--tilemap", type=Path, default=f"{script_dir}/../../util/tilemappings.lst")
    ap.add_argument("--nethack", type=Path, default=f"{script_dir}/../../src/nethack")
    ap.add_argument("--name", default="TileFont")
    ap.add_argument("--out", type=Path, default=f"{script_dir}/nethack-tile-font.symbols")
    args = ap.parse_args()

    tile_of = {}
    tile_names = {}
    for line in args.tilemap.read_text().splitlines():
        m = GLYPH_RE.match(line)
        if m:
            tile_of[int(m.group(1))] = int(m.group(2))
        m = re.match(r"^tile\[(\d+)\] \S+ (.*?)\s*(\(|:)", line)
        if m:
            tile_names[int(m.group(1))] = m.group(2).strip()

    dump = subprocess.run([str(args.nethack), "--dumpglyphnames"],
                          capture_output=True, text=True, check=True).stdout
    entries, skipped, missing = [], 0, 0
    for line in dump.splitlines():
        m = NAME_RE.match(line)
        if not m:
            continue
        glyph, gname = int(m.group(1)), m.group(2)
        if glyph not in tile_of:
            missing += 1
            continue
        tile = tile_of[glyph]
        if tile_names.get(tile) in SKIP_TILE_NAMES:
            skipped += 1
            continue
        entries.append(f"\t{gname}: U+{BASE_CP + tile:06X}")

    block = [
        f"start: {args.name}",
        "\tDescription: NetHack tiles via a tile font",
        "\tRestrictions: primary",
        "\tHandling: UTF8",
        *entries,
        "finish",
        "",
    ]
    args.out.write_text("\n".join(block))
    print(f"wrote {args.out}: {len(entries)} glyphs "
          f"({skipped} stone glyphs left blank, {missing} without a tile)")

if __name__ == "__main__":
    main()
