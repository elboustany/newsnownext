#!/usr/bin/env python3
"""
NewsNowNext static site builder.

Renders the whole site as plain HTML: a home page of region cards (US, UK,
China, France, Switzerland, Middle East, Blogs, Markets) exactly as the live
site lays them out, plus topic pages and dated recaps.

Everything is server-rendered. That is the point — the live site is a
client-rendered SPA, so crawlers currently receive an empty shell and none of
this content is indexable. Here the headlines are in the HTML.

Standard library only. Python 3.9+.

    python3 build.py                 # build everything
    python3 build.py --no-fetch      # rebuild pages from the last cached pull
    python3 build.py --config config.test.json

A recap page is only marked indexable once a human synopsis exists at
synopsis/YYYY-MM-DD.txt, and a topic page once notes/<slug>.txt exists.
Without one the page is generated but carries noindex, because a page of other
people's headlines with no original writing on it is the exact thing search
engines demote.
"""

import argparse
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime, format_datetime
from pathlib import Path

from theme import CSS
from filterjs import FILTER_JS

HERE = Path(__file__).resolve().parent
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 NewsNowNextBuilder/2.0")
CACHE = HERE / ".cache" / "items.json"

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "dc": "http://purl.org/dc/elements/1.1/",
}


# ── Fetch and parse ──────────────────────────────────────────────────────

def fetch(url, timeout=25):
    # A url with no scheme is a path relative to this file, so config.test.json
    # can point at fixtures/ and the self-test runs anywhere without network.
    if "://" not in url:
        return (HERE / url).read_bytes()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def text_of(node):
    return (node.text or "").strip() if node is not None else ""


def parse_date(raw):
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        d = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d is None:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def clean_title(title, src):
    """Strip the ' - Publisher' suffix Google News appends to every headline.

    For a site-restricted query the publisher is the source label, but a broad
    query ("switzerland economy") returns whatever outlet ran it — so a Swiss
    rates story comes back as "… - Bitcoin World" and then matches the crypto
    topic. Strip the suffix for anything routed through Google News; leave
    native feeds alone, where a trailing dash is usually part of the headline.
    """
    t = re.sub(r"\s+", " ", title).strip()
    if src.get("via") == "Google News":
        t = re.sub(r"\s+[-–—]\s+[^-–—]{2,40}$", "", t)
    else:
        head = src["label"].split()[0]
        t = re.sub(rf"\s+[-–—]\s+{re.escape(head)}[^-–—]*$", "", t, flags=re.I)
    return t.strip()


def parse_feed(raw, src, region):
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        raise ValueError(f"malformed XML ({e})")

    out = []
    nodes = list(root.iter("item")) + list(root.iter(f"{{{NS['atom']}}}entry"))

    for n in nodes:
        title = text_of(n.find("title")) or text_of(n.find(f"{{{NS['atom']}}}title"))
        if not title:
            continue

        link = text_of(n.find("link"))
        if not link:
            for ln in n.findall(f"{{{NS['atom']}}}link"):
                if ln.get("rel", "alternate") == "alternate" and ln.get("href"):
                    link = ln.get("href")
                    break
        if not link:
            continue

        raw_date = (
            text_of(n.find("pubDate"))
            or text_of(n.find(f"{{{NS['dc']}}}date"))
            or text_of(n.find(f"{{{NS['atom']}}}updated"))
            or text_of(n.find(f"{{{NS['atom']}}}published"))
        )
        when = parse_date(raw_date) or datetime.now(timezone.utc)

        out.append({
            "title": clean_title(title, src),
            "link": link,
            "ts": when.isoformat(),
            "source": src["label"],
            "source_id": src["id"],
            "region_id": region["id"],
            "region": region["title"],
            "via": src.get("via"),
        })
    return out


def collect(cfg):
    items, failures = [], []
    for region in cfg["regions"]:
        for src in region["sources"]:
            try:
                got = parse_feed(fetch(src["url"]), src, region)
                if not got:
                    raise ValueError("no items in feed")
                items.extend(got)
                print(f"  ok    {region['title']:<18} {src['label']} ({len(got)})")
            except Exception as e:                  # noqa: BLE001 - report and continue
                failures.append(f"{region['title']}/{src['label']}")
                print(f"  FAIL  {region['title']:<18} {src['label']}: {e}",
                      file=sys.stderr)
    return items, failures


def within(items, hours):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    out = []
    for it in items:
        when = parse_date(it["ts"])
        if when and when >= cutoff:
            out.append(it)
    return out


def key_of(title):
    return re.sub(r"[^a-z0-9]+", "", title.lower())[:60]


def by_source(items, cfg):
    """Group into {source_id: [items]}, newest first, deduped within a source.

    Deliberately not deduped across sources: the home page shows each desk's
    own column, and two desks covering the same story is information, not noise.
    """
    buckets = {}
    for it in items:
        buckets.setdefault(it["source_id"], []).append(it)

    for sid, lst in buckets.items():
        seen, keep = set(), []
        for it in sorted(lst, key=lambda i: i["ts"], reverse=True):
            k = key_of(it["title"])
            if not k or k in seen:
                continue
            seen.add(k)
            keep.append(it)
        buckets[sid] = keep[: cfg["max_per_source"]]
    return buckets


def merged(items):
    """One deduped chronological wire, for the topic and recap pages."""
    seen = {}
    for it in items:
        k = key_of(it["title"])
        if not k:
            continue
        if k not in seen or it["ts"] > seen[k]["ts"]:
            seen[k] = it
    return sorted(seen.values(), key=lambda i: i["ts"], reverse=True)


# ── Topic matching ───────────────────────────────────────────────────────

def topic_pattern(topic):
    return "(?<![a-z0-9])(" + "|".join(
        re.escape(k.lower()) for k in topic["keywords"]) + ")(?![a-z0-9])"


def matches(item, topic):
    return re.search(topic_pattern(topic), item["title"], flags=re.I) is not None


# ── HTML ─────────────────────────────────────────────────────────────────

def esc(s):
    return html.escape(str(s), quote=True)


def stamp(dt):
    """'Aug 3 12:23 PM' — the format the live site uses."""
    hour = dt.hour % 12 or 12
    ampm = "AM" if dt.hour < 12 else "PM"
    return f"{dt.strftime('%b')} {dt.day} {hour}:{dt.strftime('%M')} {ampm}"


NAV = [
    ("/", "News"),
    ("/topics/", "Topics"),
    ("/recap/", "Daily recap"),
]


def shell(cfg, *, title, description, canonical, body, noindex=False,
          current="/", extra_head="", body_attrs="", scripts=""):
    links = "".join(
        '<a href="{}"{}>{}</a>'.format(
            href, ' aria-current="page"' if href == current else "", esc(label))
        for href, label in NAV
    )
    robots = '<meta name="robots" content="noindex,follow">' if noindex else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(canonical)}">
{robots}
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:type" content="website">
<link rel="alternate" type="application/rss+xml" title="{esc(cfg['site_name'])} recaps" href="/feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800;900&display=swap">
<link rel="stylesheet" href="/assets/site.css">
{extra_head}
</head>
<body{body_attrs}>
<nav class="nav">
  <div class="nav-in">
    <a class="logo" href="/" aria-label="{esc(cfg['site_name'])} home">
      <span class="l1">NEWS</span><span class="l2">NOW</span><span class="l3">NEXT</span>
    </a>
    <div class="nav-links">{links}</div>
  </div>
</nav>
<div class="wrap">
{body}
<footer class="foot">
  Headlines link out to their publishers. {esc(cfg['site_name'])} does not host or
  reproduce article text. &nbsp;·&nbsp; <a href="/feed.xml">RSS</a>
</footer>
</div>
{scripts}
</body>
</html>
"""


def filter_bar(cfg, regions_present):
    region_chips = "".join(
        f'<button class="chip" type="button" data-region-btn="{esc(r["id"])}" '
        f'aria-pressed="false">{esc(r["title"])}</button>'
        for r in cfg["regions"] if r["id"] in regions_present
    )
    topic_chips = "".join(
        f'<button class="chip" type="button" data-topic-btn="{esc(t["slug"])}" '
        f'aria-pressed="false">{esc(t["title"])}</button>'
        for t in cfg["topics"]
    )
    topic_links = " · ".join(
        f'<a href="/topics/{esc(t["slug"])}.html">{esc(t["title"])}</a>'
        for t in cfg["topics"]
    )
    return f"""
<div class="filters" data-filters hidden>
  <div class="frow">
    <div class="fsearch">
      <label class="sr-only" for="f-q">Filter headlines</label>
      <input id="f-q" type="search" autocomplete="off" spellcheck="false"
             placeholder="Filter headlines…  (press / )">
    </div>
    <label class="sr-only" for="f-sort">Order</label>
    <select id="f-sort" class="fsel">
      <option value="newest">Newest first</option>
      <option value="oldest">Oldest first</option>
    </select>
  </div>

  <div class="frow">
    <span class="flabel">Region</span>
    {region_chips}
  </div>

  <details class="more">
    <summary>More filters</summary>
    <div class="frow">
      <span class="flabel">Topic</span>
      {topic_chips}
    </div>
    <div class="frow">
      <span class="flabel">Since</span>
      <label class="sr-only" for="f-window">Time window</label>
      <select id="f-window" class="fsel">
        <option value="0">Any time</option>
        <option value="6">Last 6 hours</option>
        <option value="12">Last 12 hours</option>
        <option value="24">Last 24 hours</option>
      </select>
    </div>
    <p class="fcount" style="margin-top:10px">Full pages: {topic_links} · <a href="/recap/">Daily recap</a></p>
  </details>

  <p class="fcount">
    <span id="f-count">—</span>
    <button class="linkbtn" id="f-clear" type="button" hidden>Clear filters</button>
  </p>
</div>
"""


def region_card(region, buckets):
    blocks, total = [], 0
    for src in region["sources"]:
        rows = buckets.get(src["id"], [])
        if not rows:
            continue
        total += len(rows)
        lis = []
        for it in rows:
            when = parse_date(it["ts"])
            lis.append(
                f'<li data-item data-src="{esc(it["source"])}" '
                f'data-region="{esc(region["id"])}" '
                f'data-ts="{when.timestamp():.0f}">'
                f'<a href="{esc(it["link"])}" rel="nofollow noopener" target="_blank">'
                f'{esc(it["title"])}</a>'
                f'<time datetime="{when.isoformat()}">{esc(stamp(when))}</time>'
                f'</li>'
            )
        via = f' <span class="via">via {esc(src["via"])}</span>' if src.get("via") else ""
        blocks.append(
            f'<div class="src" data-source="{esc(src["id"])}">'
            f'<h3>{esc(src["label"])}{via}</h3>'
            f'<ul class="items">{"".join(lis)}</ul>'
            f'</div>'
        )

    if not blocks:
        return "", 0

    return (
        f'<section class="card" data-region="{esc(region["id"])}">'
        f'<div class="card-head"><h2>{esc(region["title"])}</h2>'
        f'<span class="card-count" data-card-count>{total}</span></div>'
        f'{"".join(blocks)}'
        f'</section>'
    ), total


def wire_list(items, mark_sessions=False):
    """Merged chronological list, used on topic and recap pages."""
    out, current_day = [], None
    for it in items:
        when = parse_date(it["ts"])
        day = when.strftime("%A %d %B %Y")
        if day != current_day:
            if current_day is not None:
                out.append("</ol>")
            out.append(f'<p class="daymark">{esc(day)}</p><ol class="wire">')
            current_day = day
        via = f' via {esc(it["via"])}' if it.get("via") else ""
        out.append(
            f'<li><time datetime="{when.isoformat()}">{esc(stamp(when))}</time>'
            f'<div><a href="{esc(it["link"])}" rel="nofollow noopener" target="_blank">'
            f'{esc(it["title"])}</a>'
            f'<span class="src-tag">{esc(it["source"])}{via}</span></div></li>'
        )
    if current_day is not None:
        out.append("</ol>")
    return "\n".join(out) or '<p class="empty">Nothing on the wire in this window.</p>'


# ── Build ────────────────────────────────────────────────────────────────

def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  wrote {path.name}")


def build(cfg, items, out: Path):
    base = cfg["base_url"].rstrip("/")
    urls = []

    write(out / "assets" / "site.css", CSS.strip())
    write(out / "assets" / "filter.js", FILTER_JS.strip())

    buckets = by_source(items, cfg)
    wire = merged(items)

    # ── Home ─────────────────────────────────────────────────────────
    cards, present, total = [], set(), 0
    for region in cfg["regions"]:
        markup, n = region_card(region, buckets)
        if markup:
            cards.append(markup)
            present.add(region["id"])
            total += n

    topic_json = json.dumps({t["slug"]: topic_pattern(t) for t in cfg["topics"]})
    home_body = (
        '<div class="page-head">'
        f'<h1>{esc(cfg["site_name"])} — {esc(cfg.get("tagline", "financial news"))}</h1>'
        '<p class="standfirst">Every desk on one page, newest first. '
        'Headlines link straight to the publisher.</p>'
        '</div>'
        + filter_bar(cfg, present)
        + '<p class="empty" id="f-empty" hidden>Nothing matches those filters.</p>'
        + f'<div class="grid">{"".join(cards)}</div>'
    )
    write(out / "index.html", shell(
        cfg,
        title=f"{cfg['site_name']} — {cfg.get('tagline', 'Global Financial News Feed')}",
        description=("Financial and world news from every major desk on one page: "
                     "US, UK, China, France, Switzerland and the Middle East."),
        canonical=f"{base}/", body=home_body, current="/",
        extra_head=f"<script>window.__TOPICS__={topic_json};</script>",
        scripts='<script src="/assets/filter.js" defer></script>',
    ))
    urls.append((f"{base}/", datetime.now(timezone.utc)))

    # ── Topic pages ──────────────────────────────────────────────────
    for topic in cfg["topics"]:
        hits = [i for i in wire if matches(i, topic)][: cfg["max_per_topic"]]
        note_path = HERE / "notes" / f"{topic['slug']}.txt"
        note = note_path.read_text(encoding="utf-8").strip() if note_path.exists() else ""
        note_html = ""
        if note:
            paras = "".join(f"<p>{esc(p.strip())}</p>"
                            for p in note.split("\n\n") if p.strip())
            note_html = f'<div class="note">{paras}</div>'

        canonical = f"{base}/topics/{topic['slug']}.html"
        write(out / "topics" / f"{topic['slug']}.html", shell(
            cfg,
            title=f"{topic['title']} news — {cfg['site_name']}",
            description=topic["description"], canonical=canonical,
            body=('<div class="prose"><div class="page-head">'
                  f'<h1>{esc(topic["title"])}</h1>'
                  f'<p class="standfirst">{esc(topic["description"])}</p></div>'
                  f'{note_html}{wire_list(hits)}</div>'),
            current="/topics/", noindex=not note,
        ))
        if note:
            urls.append((canonical, datetime.now(timezone.utc)))

    cards_html = "".join(
        f'<li><h2><a href="/topics/{esc(t["slug"])}.html">{esc(t["title"])}</a></h2>'
        f'<p>{esc(t["description"])}</p></li>'
        for t in cfg["topics"]
    )
    write(out / "topics" / "index.html", shell(
        cfg, title=f"Topics — {cfg['site_name']}",
        description="Financial news by topic: oil, crypto, rates, equities, China and tech.",
        canonical=f"{base}/topics/", current="/topics/",
        body=('<div class="prose"><div class="page-head"><h1>Topics</h1>'
              '<p class="standfirst">The wire, filtered to one subject and kept for 72 hours.</p>'
              f'</div><ul class="cards">{cards_html}</ul></div>'),
    ))
    urls.append((f"{base}/topics/", datetime.now(timezone.utc)))

    # ── Daily recap ──────────────────────────────────────────────────
    today = datetime.now(timezone.utc).date()
    syn_path = HERE / "synopsis" / f"{today.isoformat()}.txt"
    synopsis = syn_path.read_text(encoding="utf-8").strip() if syn_path.exists() else ""
    day_items = [i for i in wire if parse_date(i["ts"]).date() == today]

    syn_html = ""
    if synopsis:
        paras = "".join(f"<p>{esc(p.strip())}</p>"
                        for p in synopsis.split("\n\n") if p.strip())
        syn_html = f'<div class="note">{paras}</div>'

    pretty = today.strftime("%d %B %Y")
    canonical = f"{base}/recap/{today.isoformat()}.html"
    ld = json.dumps({
        "@context": "https://schema.org", "@type": "NewsArticle",
        "headline": f"Market recap, {pretty}",
        "datePublished": datetime.now(timezone.utc).isoformat(),
        "publisher": {"@type": "Organization", "name": cfg["site_name"]},
        "url": canonical,
    })
    write(out / "recap" / f"{today.isoformat()}.html", shell(
        cfg, title=f"Market recap, {pretty} — {cfg['site_name']}",
        description=(synopsis[:155] if synopsis
                     else f"Every headline that crossed the wire on {pretty}."),
        canonical=canonical, current="/recap/", noindex=not synopsis,
        body=('<div class="prose"><div class="page-head">'
              f'<h1>Market recap, {esc(pretty)}</h1>'
              '<p class="standfirst">What crossed the wire today, in order.</p></div>'
              f'{syn_html}{wire_list(day_items)}</div>'),
        extra_head=f'<script type="application/ld+json">{ld}</script>',
    ))
    if synopsis:
        urls.append((canonical, datetime.now(timezone.utc)))

    archive = sorted(
        (p for p in (out / "recap").glob("*.html")
         if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem)), reverse=True)
    links = "".join(
        f'<li><h2><a href="/recap/{p.name}">'
        f'{esc(datetime.fromisoformat(p.stem).strftime("%d %B %Y"))}</a></h2></li>'
        for p in archive)
    write(out / "recap" / "index.html", shell(
        cfg, title=f"Daily market recaps — {cfg['site_name']}",
        description="An archive of daily financial market recaps.",
        canonical=f"{base}/recap/", current="/recap/",
        body=('<div class="prose"><div class="page-head"><h1>Daily recaps</h1>'
              '<p class="standfirst">A short written summary of each trading day.</p>'
              f'</div><ul class="cards">{links}</ul></div>'),
    ))
    urls.append((f"{base}/recap/", datetime.now(timezone.utc)))

    # ── Sitemap, RSS, robots ─────────────────────────────────────────
    sm = ["<?xml version='1.0' encoding='UTF-8'?>",
          "<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>"]
    for loc, when in urls:
        sm.append(f"<url><loc>{esc(loc)}</loc>"
                  f"<lastmod>{when.date().isoformat()}</lastmod></url>")
    sm.append("</urlset>")
    write(out / "sitemap.xml", "\n".join(sm))

    now = datetime.now(timezone.utc)
    rss = ["<?xml version='1.0' encoding='UTF-8'?>", "<rss version='2.0'><channel>",
           f"<title>{esc(cfg['site_name'])} — daily market recap</title>",
           f"<link>{esc(base)}/recap/</link>",
           "<description>A short written summary of each trading day.</description>",
           f"<lastBuildDate>{format_datetime(now)}</lastBuildDate>"]
    for p in archive[:30]:
        d = datetime.fromisoformat(p.stem).replace(tzinfo=timezone.utc)
        rss.append(f"<item><title>Market recap, {d.strftime('%d %B %Y')}</title>"
                   f"<link>{esc(base)}/recap/{p.name}</link>"
                   f"<guid>{esc(base)}/recap/{p.name}</guid>"
                   f"<pubDate>{format_datetime(d)}</pubDate></item>")
    rss.append("</channel></rss>")
    write(out / "feed.xml", "\n".join(rss))

    write(out / "robots.txt", f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")

    return len(urls), total, (bool(synopsis), today.isoformat())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(HERE / "config.json"))
    ap.add_argument("--no-fetch", action="store_true",
                    help="rebuild from the cached pull instead of hitting the network")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    out = Path(cfg["output_dir"])
    if not out.is_absolute():
        out = HERE / out

    if args.no_fetch:
        if not CACHE.exists():
            sys.exit("No cache yet — run once without --no-fetch.")
        raw = json.loads(CACHE.read_text(encoding="utf-8"))
        print(f"Using cached pull: {len(raw)} items")
    else:
        print("Fetching feeds…")
        raw, failed = collect(cfg)
        if not raw:
            sys.exit("Every feed failed. Nothing to build.")
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(raw), encoding="utf-8")
        if failed:
            print(f"\nNote: {len(failed)} source(s) unavailable: {', '.join(failed)}")

    items = within(raw, cfg["window_hours"])
    print(f"\n{len(items)} headlines in the last {cfg['window_hours']}h")

    print("Building…")
    count, shown, (has_syn, day) = build(cfg, items, out)

    print(f"\nDone. {shown} headlines on the home page, "
          f"{count} indexable URL(s) in {out}")
    if not has_syn:
        print(f"Today's recap is noindex — write synopsis/{day}.txt "
              f"(200–300 words) and rerun to publish it.")
    missing = [t["slug"] for t in cfg["topics"]
               if not (HERE / "notes" / f"{t['slug']}.txt").exists()]
    if missing:
        print(f"Topic pages still noindex (no intro written): {', '.join(missing)}")


if __name__ == "__main__":
    main()
