#!/usr/bin/env python3
"""
Fetch real book covers from Open Library into generator/static/covers/.

    python3 dev/gen-covers.py            # fetch missing covers, write map.json

Same philosophy as the source logos: fetched once, committed, served as
local assets, never hotlinked. A book with no cover found keeps the
generated gradient placeholder, so the shelf never shows a broken image.

The map file (static/covers/map.json) keys title -> filename; build.py
reads it and only uses covers that actually exist.
"""

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "generator"
OUT = GEN / "static" / "covers"
UA = "Mozilla/5.0 (compatible; NewsNowNextCovers/1.0)"

SEARCH = ("https://openlibrary.org/search.json?title={}&author={}"
          "&limit=5&fields=cover_i,title")
COVER = "https://covers.openlibrary.org/b/id/{}-M.jpg"


def slug(title):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", title.lower())).strip("-")[:60]


def get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def first_author(author):
    # "Bryan Burrough & John Helyar" -> "Burrough": surnames match best.
    head = re.split(r"[&,]| and ", author)[0].strip()
    parts = head.split()
    return parts[-1] if parts else head


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data = json.loads((GEN / "data" / "books.json").read_text(encoding="utf-8"))
    map_path = OUT / "map.json"
    cover_map = json.loads(map_path.read_text()) if map_path.exists() else {}

    hits = misses = kept = 0
    for title, author, year, cat in data["books"]:
        fn = f"{slug(title)}.jpg"
        if title in cover_map and (OUT / cover_map[title]).exists():
            kept += 1
            continue
        try:
            q = SEARCH.format(urllib.parse.quote(title),
                              urllib.parse.quote(first_author(author)))
            docs = json.loads(get(q)).get("docs", [])
            cover_id = next((d["cover_i"] for d in docs if d.get("cover_i")), None)
            if not cover_id:
                # retry title-only: some editions list different author strings
                q = SEARCH.format(urllib.parse.quote(title), "")
                docs = json.loads(get(q)).get("docs", [])
                cover_id = next((d["cover_i"] for d in docs if d.get("cover_i")), None)
            if not cover_id:
                misses += 1
                print(f"  miss  {title}")
                continue
            img = get(COVER.format(cover_id))
            # Open Library serves a tiny blank for missing sizes; reject it.
            if img[:2] != b"\xff\xd8" or len(img) < 3000:
                misses += 1
                print(f"  blank {title}")
                continue
            (OUT / fn).write_bytes(img)
            cover_map[title] = fn
            hits += 1
            print(f"  ok    {title}")
        except Exception as e:                      # noqa: BLE001 - keep going
            misses += 1
            print(f"  FAIL  {title}: {e}")
        time.sleep(0.6)                             # be polite to Open Library

    map_path.write_text(json.dumps(cover_map, indent=1, sort_keys=True),
                        encoding="utf-8")
    print(f"\n{hits} fetched, {kept} already present, {misses} without covers "
          f"(placeholder stays for those)")


if __name__ == "__main__":
    main()
