#!/usr/bin/env python3
"""
Generate extension/newtab.css from generator/theme.py.

The extension and the site are meant to look like one product, so the palette,
type and card layout have a single source of truth. This appends only the few
rules the extension needs and the site does not (the refresh button, the
loading skeletons).

    python3 dev/gen-css.py            # write extension/newtab.css
    python3 dev/gen-css.py --check    # exit 1 if it is out of date
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEME = ROOT / "generator" / "theme.py"
OUT = ROOT / "extension" / "newtab.css"

HEADER = """/* GENERATED FILE - do not edit by hand.
   Source of truth: generator/theme.py
   Regenerate:      python3 dev/gen-css.py

   Tokens and layout are the site's, kept identical on purpose. */
"""

EXTRA = """

/* ── Extension only ────────────────────────────────────────────────── */

.nav-links{font-size:13px;color:#cbd5e1;align-items:center}
.refresh{
  font:inherit;font-size:13px;font-weight:500;
  background:transparent;border:1px solid #4b5563;color:var(--navbar-fg);
  border-radius:var(--radius);padding:6px 12px;cursor:pointer;
}
.refresh:hover{border-color:var(--logo-news);color:#fff}
.refresh:disabled{opacity:.5;cursor:default}
.refresh:focus-visible{outline:2px solid var(--logo-news);outline-offset:2px}
.wrap{padding-top:16px}
.chips{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.skeleton{
  border:1px solid var(--border);border-radius:var(--radius);
  height:170px;background:var(--muted);opacity:.55;
}
@media (prefers-reduced-motion:no-preference){
  .skeleton{animation:pulse 1.4s ease-in-out infinite}
  @keyframes pulse{0%,100%{opacity:.55}50%{opacity:.3}}
}
"""


def render():
    theme = THEME.read_text(encoding="utf-8")
    m = re.search(r'CSS = """(.*?)"""', theme, re.S)
    if not m:
        raise SystemExit("gen-css: could not find CSS = \"\"\"…\"\"\" in theme.py")
    return HEADER + "\n" + m.group(1).strip() + EXTRA


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    want = render()
    current = OUT.read_text(encoding="utf-8") if OUT.exists() else None

    if args.check:
        if current != want:
            print("extension/newtab.css is out of date - run python3 dev/gen-css.py",
                  file=sys.stderr)
            return 1
        print(f"Up to date: {len(want)} bytes.")
        return 0

    OUT.write_text(want, encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(want)} bytes).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
