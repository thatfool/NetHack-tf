#!/usr/bin/env python3
# /// script
# dependencies = ['fonttools']
# ///
"""Build a color font from NetHack's text tile files.

Tile N is mapped to code point BASE_CP + N.
Pixels become vector squares; background colors are left transparent.

Usage:
  uv run build_tile_font.py

Optional:
  --src /path/to/NetHack/win/share
  --out /path/to/output.ttf
  --only 0,1,2
  --width-em 1.2
  --height-em 1.2
  --bottom-em -0.22
  --svg # adds SVG representation - use only if needed
"""
import argparse
import re
import os
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.colorLib.builder import buildCOLR, buildCPAL
from fontTools.ttLib import newTable
from fontTools.ttLib.tables.S_V_G_ import SVGDocument

BASE_CP = 0x100000
UPM = 1000
TILE_FILES = ("monsters.txt", "objects.txt", "other.txt")
TRANSPARENT = {".", "1"}
TILE_RE = re.compile(r"^# tile (\d+) \((.*)\)")
PAL_RE = re.compile(r"^(\S) = \(\s*(\d+),\s*(\d+),\s*(\d+)\)")

# From win/share/tiletext.c; used for statues.
GRAYMAPPINGS = [0, 1, 17, 18, 19, 20, 27, 22, 23, 24, 25, 26, 21, 15, 13, 14,
                14, 1, 17, 18, 19, 20, 27, 22, 23, 24, 25, 20]

def read_tile_file(path: Path):
    """Return (palette_order, palette, [(local_index, name, rows)])."""
    order, palette, tiles = [], {}, []
    lines = path.read_text().splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = PAL_RE.match(line)
        if m:
            order.append(m.group(1))
            palette[m.group(1)] = tuple(int(m.group(k)) for k in (2, 3, 4))
        m = TILE_RE.match(line)
        if m:
            local = int(m.group(1))
            j = i + 1
            while lines[j].startswith("#"):  # optional comment lines
                j += 1
            assert lines[j].strip() == "{", (path.name, local)
            rows = [lines[j + 1 + r].strip() for r in range(16)]
            assert lines[j + 17].strip() == "}", (path.name, local)
            assert all(len(r) == 16 for r in rows), (path.name, local)
            tiles.append((local, m.group(2), rows))
            i = j + 18
            continue
        i += 1
    return order, palette, tiles


def grayed(rows, order):
    """Statue version of a tile: remap every palette entry to its gray."""
    remap = {}
    for idx, key in enumerate(order):
        if idx < len(GRAYMAPPINGS):
            remap[key] = order[GRAYMAPPINGS[idx]]
        else:
            remap[key] = key
    return ["".join(remap.get(c, c) for c in row) for row in rows]


def all_tiles(src: Path):
    """Yield (tile_number, name, rows, palette) in NetHack's numbering."""
    offset = 0
    monsters = None
    for fname in TILE_FILES:
        order, pal, tiles = read_tile_file(src / fname)
        if fname == "monsters.txt":
            monsters = (order, pal, tiles)
        for local, name, rows in tiles:
            yield offset + local, name, rows, pal
        offset += len(tiles)
    order, pal, tiles = monsters
    for local, name, rows in tiles:
        if name.startswith("invisible monster"):
            yield offset + len(tiles) - 1, "invisible statue", grayed(rows, order), pal
        else:
            yield offset + local, "statue of " + name, grayed(rows, order), pal


def draw_rects(rects, x0, y0, px_w, px_h):
    """Return a TrueType glyph made of pixel-run rectangles (col, row, len)."""
    pen = TTGlyphPen(None)
    for col, row, length in rects:
        left = round(x0 + col * px_w)
        right = round(x0 + (col + length) * px_w)
        top = round(y0 + (16 - row) * px_h)
        bottom = round(y0 + (15 - row) * px_h)
        # clockwise contour (TrueType outer contour direction)
        pen.moveTo((left, bottom))
        pen.lineTo((left, top))
        pen.lineTo((right, top))
        pen.lineTo((right, bottom))
        pen.closePath()
    return pen.glyph()


def svg_path(rgb, rects, x0, y0, px_w, px_h):
    """Return an SVG <path> for pixel-run rectangles in one color.

    SVG glyphs use font units with the origin on the baseline and y
    pointing down, so font-space y values are negated.
    """
    d = []
    for col, row, length in rects:
        left = round(x0 + col * px_w)
        right = round(x0 + (col + length) * px_w)
        top = -round(y0 + (16 - row) * px_h)
        bottom = -round(y0 + (15 - row) * px_h)
        d.append(f"M{left} {top}H{right}V{bottom}H{left}Z")
    return '<path fill="#%02x%02x%02x" d="%s"/>' % (*rgb, "".join(d))


def opaque_runs(rows):
    """Pixel runs (col, row, len) covering every non-transparent pixel."""
    runs = []
    for r, row in enumerate(rows):
        c = 0
        while c < 16:
            if row[c] in TRANSPARENT:
                c += 1
                continue
            start = c
            while c < 16 and row[c] not in TRANSPARENT:
                c += 1
            runs.append((start, r, c - start))
    return runs


def main():
    script_dir = os.path.dirname(os.path.realpath(__file__))

    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=script_dir)
    ap.add_argument("--out", type=Path, default=f"{script_dir}/nethack-tile-font.ttf")
    ap.add_argument("--only", help="comma-separated tile numbers (for tests)")
    ap.add_argument("--width-em", type=float, default=1.2)
    ap.add_argument("--height-em", type=float, default=1.2)
    ap.add_argument("--bottom-em", type=float, default=-0.22)
    ap.add_argument("--advance-em", type=float, default=None,
                    help="advance width (default: same as width)")
    ap.add_argument("--family", default="NetHack Tiles")
    ap.add_argument("--svg", action="store_true",
                    help="add an OpenType-SVG table (use only for specific terminals, can break the font for terminals that don't need it)")
    args = ap.parse_args()

    only = {int(x) for x in args.only.split(",")} if args.only else None
    width = args.width_em * UPM
    height = args.height_em * UPM
    x0, y0 = 0, args.bottom_em * UPM
    px_w, px_h = width / 16, height / 16
    advance = round((args.advance_em or args.width_em) * UPM)

    glyph_order = [".notdef", "space"]
    glyphs = {".notdef": TTGlyphPen(None).glyph(), "space": TTGlyphPen(None).glyph()}
    metrics = {".notdef": (advance, 0), "space": (advance, 0)}
    cmap = {0x20: "space"}
    colr_layers = {}
    svg_gids = {}
    svg_docs = {}
    palette_index = {}
    palette = []
    names = []

    for idx, name, rows, pal in all_tiles(args.src):
        if only is not None and idx not in only:
            continue
        runs_by_color = {}
        for r, row in enumerate(rows):
            c = 0
            while c < 16:
                ch = row[c]
                if ch in TRANSPARENT:
                    c += 1
                    continue
                start = c
                while c < 16 and row[c] == ch:
                    c += 1
                runs_by_color.setdefault(pal[ch], []).append((start, r, c - start))

        base = f"tile{idx:04d}"
        svg_gids[base] = len(glyph_order)
        glyph_order.append(base)
        # The base glyph is the tile's silhouette: what renderers without
        # color support draw, and it gives the glyph its bounding box.
        glyphs[base] = draw_rects(opaque_runs(rows), x0, y0, px_w, px_h)
        metrics[base] = (advance, 0)
        cmap[BASE_CP + idx] = base
        layers = []
        svg_rects = []
        for n, (rgb, rects) in enumerate(sorted(runs_by_color.items())):
            if rgb not in palette_index:
                palette_index[rgb] = len(palette)
                palette.append(tuple(v / 255 for v in rgb) + (1.0,))
            lname = f"{base}.l{n}"
            glyph_order.append(lname)
            glyphs[lname] = draw_rects(rects, x0, y0, px_w, px_h)
            metrics[lname] = (advance, 0)
            layers.append((lname, palette_index[rgb]))
            svg_rects.append(svg_path(rgb, rects, x0, y0, px_w, px_h))
        colr_layers[base] = layers
        svg_docs[base] = svg_rects
        names.append(f"U+{BASE_CP + idx:06X} {base} {name}")

    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    # PostScript name to make this work on macOS too
    ps_name = re.sub(r"[^A-Za-z0-9]", "", args.family) + "-Regular"
    fb.setupNameTable({
        "familyName": args.family,
        "styleName": "Regular",
        "uniqueFontIdentifier": ps_name,
        "fullName": f"{args.family} Regular",
        "version": "Version 1.000",
        "psName": ps_name,
    })
    fb.setupPost()
    fb.font["COLR"] = buildCOLR(colr_layers)
    fb.font["CPAL"] = buildCPAL([palette])
    if args.svg:
        svg = newTable("SVG ")
        svg.docList = [
            SVGDocument(
                f'<svg xmlns="http://www.w3.org/2000/svg">'
                f'<g id="glyph{svg_gids[base]}">{"".join(paths)}</g></svg>',
                svg_gids[base], svg_gids[base], True)
            for base, paths in sorted(svg_docs.items(), key=lambda kv: svg_gids[kv[0]])
        ]
        fb.font["SVG "] = svg
    fb.save(args.out)
    (args.out.with_suffix(".map.txt")).write_text("\n".join(names) + "\n")
    print(f"wrote {args.out}: {len(colr_layers)} tiles, {len(palette)} colors")


if __name__ == "__main__":
    main()
