#!/usr/bin/env python3
"""
Generate extension/feeds.js from generator/config.json.

The extension and the site show the same regions, the same sources and the same
topic keywords. Keeping two hand-edited copies in step never lasts, so there is
exactly one source of truth — config.json — and this writes the other one.

    python3 dev/gen-feeds.py           # write extension/feeds.js
    python3 dev/gen-feeds.py --check   # exit 1 if it is out of date (no write)

It also rewrites `host_permissions` in the extension manifest, because a source
the manifest does not list is a source the extension silently cannot fetch.
"""

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "generator" / "config.json"
FEEDS_JS = ROOT / "extension" / "feeds.js"
MANIFEST = ROOT / "extension" / "manifest.json"

HEADER = """// GENERATED FILE — do not edit by hand.
// Source of truth: generator/config.json
// Regenerate:      python3 dev/gen-feeds.py
//
// Bloomberg, Reuters and several others have no open RSS any more, so those
// come through Google News site-restricted search. Where that is the case the
// source carries a `via` label and the UI shows it.
"""


def js(value, indent=0):
    """Minimal JS literal writer — json is a valid subset, but keep keys bare."""
    pad = "  " * indent
    if isinstance(value, dict):
        inner = ",\n".join(
            f'{pad}  {k}: {js(v, indent + 1)}'
            for k, v in value.items() if not k.startswith("_")
        )
        return "{\n" + inner + f"\n{pad}}}"
    if isinstance(value, list):
        inner = ",\n".join(f"{pad}  {js(v, indent + 1)}" for v in value)
        return "[\n" + inner + f"\n{pad}]"
    return json.dumps(value, ensure_ascii=False)


def render(cfg):
    regions = [
        {
            "id": r["id"],
            "title": r["title"],
            "sources": [
                {k: s[k] for k in ("id", "label", "via", "url") if k in s}
                for s in r["sources"]
            ],
        }
        for r in cfg["regions"]
    ]
    topics = [
        {"slug": t["slug"], "title": t["title"], "keywords": t["keywords"]}
        for t in cfg["topics"]
    ]
    return (
        HEADER
        + "\nexport const REGIONS = " + js(regions) + ";\n"
        + "\nexport const TOPICS = " + js(topics) + ";\n"
        + "\n// Flat list, for fetching and for the source filter.\n"
          "export const FEEDS = REGIONS.flatMap(r =>\n"
          "  r.sources.map(s => ({ ...s, regionId: r.id, region: r.title })));\n"
    )


def hosts(cfg):
    out = set()
    for r in cfg["regions"]:
        for s in r["sources"]:
            host = urlparse(s["url"]).netloc
            if host:
                out.add(f"https://{host}/*")
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify the generated files are current; write nothing")
    args = ap.parse_args()

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    want_js = render(cfg)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    want_hosts = hosts(cfg)
    manifest["host_permissions"] = want_hosts
    want_manifest = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"

    stale = []
    if not FEEDS_JS.exists() or FEEDS_JS.read_text(encoding="utf-8") != want_js:
        stale.append("extension/feeds.js")
    if MANIFEST.read_text(encoding="utf-8") != want_manifest:
        stale.append("extension/manifest.json (host_permissions)")

    if args.check:
        if stale:
            print("Out of date — run python3 dev/gen-feeds.py:", file=sys.stderr)
            for s in stale:
                print(f"  · {s}", file=sys.stderr)
            return 1
        n = sum(len(r["sources"]) for r in cfg["regions"])
        print(f"Up to date: {len(cfg['regions'])} regions, {n} sources, "
              f"{len(cfg['topics'])} topics.")
        return 0

    FEEDS_JS.write_text(want_js, encoding="utf-8")
    MANIFEST.write_text(want_manifest, encoding="utf-8")
    n = sum(len(r["sources"]) for r in cfg["regions"])
    print(f"Wrote extension/feeds.js — {len(cfg['regions'])} regions, {n} sources, "
          f"{len(cfg['topics'])} topics.")
    print(f"Wrote {len(want_hosts)} host_permissions into extension/manifest.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
