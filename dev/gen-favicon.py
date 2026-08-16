#!/usr/bin/env python3
"""
Generate the favicon pair in generator/static/: favicon.svg (crisp at any
size) and favicon.ico (16/32/48 for legacy UAs and /favicon.ico probes).

    python3 dev/gen-favicon.py

The full NEWS/NOW/NEXT wordmark is unreadable at 16 px, so the favicon is
the same identity reduced to its gesture: three rounded bars in the logo
colours on the navbar navy. Colours come from generator/theme.py so a
palette change propagates.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "generator"
sys.path.insert(0, str(GEN))

theme_src = (GEN / "theme.py").read_text(encoding="utf-8")


def token(name, fallback):
    m = re.search(rf"--{name}:\s*(#[0-9a-fA-F]{{6}})", theme_src)
    return m.group(1) if m else fallback


NAVY = token("navbar", "#374151")
BARS = [token("logo-news", "#f97316"),
        token("logo-now", "#10b981"),
        token("logo-next", "#ef4444")]

SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
<rect width="48" height="48" rx="10" fill="{NAVY}"/>
<rect x="10" y="11" width="28" height="7" rx="3.5" fill="{BARS[0]}"/>
<rect x="10" y="20.5" width="21" height="7" rx="3.5" fill="{BARS[1]}"/>
<rect x="10" y="30" width="28" height="7" rx="3.5" fill="{BARS[2]}"/>
</svg>
"""


def main():
    from PIL import Image, ImageDraw

    (GEN / "static" / "favicon.svg").write_text(SVG, encoding="utf-8")

    frames = []
    for size in (48, 32, 16):
        s = size / 48
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([0, 0, size - 1, size - 1],
                            radius=max(2, round(10 * s)), fill=NAVY)
        for colour, (x, y, w, h) in zip(BARS, [(10, 11, 28, 7),
                                               (10, 20.5, 21, 7),
                                               (10, 30, 28, 7)]):
            d.rounded_rectangle([round(x * s), round(y * s),
                                 round((x + w) * s), round((y + h) * s)],
                                radius=max(1, round(3.5 * s)), fill=colour)
        frames.append(img)

    frames[0].save(GEN / "static" / "favicon.ico",
                   sizes=[(48, 48), (32, 32), (16, 16)],
                   append_images=frames[1:])
    print("Wrote static/favicon.svg and static/favicon.ico")


if __name__ == "__main__":
    main()
