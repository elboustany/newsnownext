#!/usr/bin/env python3
"""
Fail if extension/feeds.js and generator/config.json have drifted apart.

Both halves of the package define the same eight sources and the same six
topics. A reader who filters the extension to "Oil" and then opens
/topics/oil.html should see the same selection; if the keyword lists diverge,
they quietly won't, and nothing else in the build would notice.

    python3 dev/check-sync.py        # exit 0 in sync, 1 with a diff

JS is read with a regex rather than executed — no Node dependency.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEEDS_JS = ROOT / "extension" / "feeds.js"
CONFIG = ROOT / "generator" / "config.json"


def js_array(src, name):
    """Extract `export const NAME = [ ... ];` and read it as JSON."""
    m = re.search(rf"export const {name}\s*=\s*(\[.*?\n\]);", src, re.S)
    if not m:
        raise SystemExit(f"check-sync: could not find {name} in {FEEDS_JS.name}")
    body = m.group(1)
    # Whole-line comments only — a bare //[^\n]* would eat the // inside every
    # https:// url and leave an unterminated string.
    body = re.sub(r"^[ \t]*//[^\n]*$", "", body, flags=re.M)
    body = re.sub(r"(\{|,)\s*(\w+)\s*:", r'\1"\2":', body)  # quote keys
    body = re.sub(r",(\s*[\]}])", r"\1", body)              # trailing commas
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise SystemExit(f"check-sync: {name} is not parseable as JSON ({e})")


def main():
    src = FEEDS_JS.read_text(encoding="utf-8")
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    problems = []

    ext_feeds = {f["id"]: f["url"] for f in js_array(src, "FEEDS")}
    gen_feeds = {f["id"]: f["url"] for f in cfg["feeds"]}
    for side, missing in (("generator/config.json", ext_feeds.keys() - gen_feeds.keys()),
                          ("extension/feeds.js", gen_feeds.keys() - ext_feeds.keys())):
        for fid in sorted(missing):
            problems.append(f"feed {fid!r} is missing from {side}")
    for fid in sorted(ext_feeds.keys() & gen_feeds.keys()):
        if ext_feeds[fid] != gen_feeds[fid]:
            problems.append(
                f"feed {fid!r} url differs:\n"
                f"    extension  {ext_feeds[fid]}\n"
                f"    generator  {gen_feeds[fid]}")

    ext_topics = {t["slug"]: [k.lower() for k in t["keywords"]]
                  for t in js_array(src, "TOPICS")}
    gen_topics = {t["slug"]: [k.lower() for k in t["keywords"]]
                  for t in cfg["topics"]}
    for side, missing in (("generator/config.json", ext_topics.keys() - gen_topics.keys()),
                          ("extension/feeds.js", gen_topics.keys() - ext_topics.keys())):
        for slug in sorted(missing):
            problems.append(f"topic {slug!r} is missing from {side}")
    for slug in sorted(ext_topics.keys() & gen_topics.keys()):
        only_ext = sorted(set(ext_topics[slug]) - set(gen_topics[slug]))
        only_gen = sorted(set(gen_topics[slug]) - set(ext_topics[slug]))
        if only_ext or only_gen:
            problems.append(
                f"topic {slug!r} keywords differ:\n"
                f"    only in extension  {only_ext or '—'}\n"
                f"    only in generator  {only_gen or '—'}")

    if problems:
        print("Feed/topic definitions are out of sync:\n", file=sys.stderr)
        for p in problems:
            print(f"  · {p}", file=sys.stderr)
        print("\nEdit both files so they match, then rerun.", file=sys.stderr)
        return 1

    print(f"In sync: {len(ext_feeds)} feeds, {len(ext_topics)} topics.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
