#!/usr/bin/env python3
"""
NewsNowNext static site builder.

Renders the whole site as plain HTML: a home page of region cards (US, UK,
China, France, Switzerland, Middle East, Blogs, Markets) exactly as the live
site lays them out, plus topic pages and dated recaps.

Everything is server-rendered. That is the point - the live site is a
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
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime, format_datetime
from pathlib import Path

from theme import CSS
import market
from filterjs import FILTER_JS
from booksjs import BOOKS_JS
from pagesjs import PAGES_JS

HERE = Path(__file__).resolve().parent
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 NewsNowNextBuilder/2.0")
# Appended to CSS/JS URLs so every deploy busts Cloudflare's edge cache and
# the service worker in one move. Without it a deploy could serve new HTML
# with up to four hours of stale stylesheet - mixed chrome, seen in the wild.
BUILD_STAMP = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
# Keyed on output_dir so the offline self-test (which writes site-test/) cannot
# clobber the production pull. They shared one path and it silently did.
def cache_path(cfg):
    return HERE / ".cache" / f"items-{cfg['output_dir']}.json"

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
    query ("switzerland economy") returns whatever outlet ran it - so a Swiss
    rates story comes back as "… - Bitcoin World" and then matches the crypto
    topic. Strip the suffix for anything routed through Google News; leave
    native feeds alone, where a trailing dash is usually part of the headline.
    """
    t = re.sub(r"\s+", " ", title).strip()
    # House style: no em or en dashes anywhere, including publishers' own
    # headlines.
    t = t.replace(" \u2014 ", " - ").replace("\u2014", "-")
    t = t.replace(" \u2013 ", " - ").replace("\u2013", "-")
    if src.get("via") == "Google News":
        t = re.sub(r"\s+[---]\s+[^---]{2,40}$", "", t)
    else:
        head = src["label"].split()[0]
        t = re.sub(rf"\s+[---]\s+{re.escape(head)}[^---]*$", "", t, flags=re.I)
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
    for c in cfg.get("world", []):
        src = {"id": f"world-{c['slug']}", "label": c["title"], "via": "Google News",
               "url": c["url"]}
        try:
            got = parse_feed(fetch(src["url"]), src, {"id": "world", "title": "World"})
            for g in got:
                g["world_slug"] = c["slug"]
            items.extend(got)
        except Exception:                           # noqa: BLE001 - reported in the tally
            failures.append(f"World/{c['title']}")

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



# ── Trending ─────────────────────────────────────────────────────────────

STOP = {"the", "a", "an", "to", "of", "in", "on", "for", "as", "at", "and",
        "or", "with", "after", "over", "more", "than", "says", "say", "new",
        "its", "his", "her", "their", "from", "by", "is", "are", "be", "will",
        "amid", "into", "out", "up", "down", "how", "why", "what", "who"}


def _tokens(title):
    return {w for w in re.findall(r"[a-z0-9]+", title.lower())
            if len(w) > 2 and w not in STOP}


def _trend_history_path(cfg):
    return HERE / ".cache" / f"trending-history-{cfg['output_dir']}.json"


def _cluster_key(toks):
    return "-".join(sorted(toks)[:6])


def _load_trend_history(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:                               # noqa: BLE001 - fresh start
        return {}


def _update_trend_history(clusters, path):
    """Persist desk counts across builds so the next build can say a story
    went from one desk to five. Runs on a 30-minute cron in production, so
    the history accumulates on its own."""
    hist = _load_trend_history(path)
    now = datetime.now(timezone.utc).isoformat()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    hist = {k: v for k, v in hist.items() if v.get("updated", "") >= cutoff}
    for c in clusters:
        k = _cluster_key(c["toks"])
        prev = hist.get(k)
        c["first_seen"] = prev["first_seen"] if prev else now
        c["prev_desks"] = prev["desks"] if prev else None
        hist[k] = {"first_seen": c["first_seen"], "desks": len(c["sources"]),
                   "updated": now}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(hist), encoding="utf-8")


def trending_clusters(items, hist_path, hours=24):
    """Group near-duplicate stories across desks.

    The ranking signal is deliberately simple and explainable: a story that
    three desks ran inside a day is trending; a story one desk ran is just
    news. Similarity is token overlap against the cluster's newest title.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent = [i for i in items if parse_date(i["ts"]) >= cutoff]

    clusters = []
    for it in recent:                       # items arrive newest first
        toks = _tokens(it["title"])
        if len(toks) < 3:
            continue
        for c in clusters:
            inter = len(toks & c["toks"])
            if inter and inter / min(len(toks), len(c["toks"])) >= 0.6:
                c["sources"].add(it["source"])
                break
        else:
            clusters.append({"toks": toks, "rep": it, "sources": {it["source"]}})

    clusters.sort(key=lambda c: (len(c["sources"]), c["rep"]["ts"]), reverse=True)
    _update_trend_history(clusters, hist_path)
    return clusters


TREND_LABELS = [("oil", "Oil"), ("crypto", "Crypto"), ("rates", "Rates"),
                ("equities", "Equities"), ("china", "China"),
                ("ai-and-tech", "AI & tech")]


def trending_section(cfg, items):
    clusters = trending_clusters(items, _trend_history_path(cfg))
    if len(clusters) < 5:
        return ""
    by_slug = {t["slug"]: t for t in cfg["topics"]}

    # Hotness: desk count decayed by age. A 2-desk story from 20 minutes ago
    # beats a 4-desk story from last night, which is what "trending" means.
    now_dt = datetime.now(timezone.utc)

    def hotness(c):
        age_h = max(0.0, (now_dt - parse_date(c["rep"]["ts"])).total_seconds() / 3600)
        return len(c["sources"]) / (1.0 + age_h / 6.0)

    hot_ranked = sorted(clusters, key=hotness, reverse=True)

    def card(rank, c):
        it = c["rep"]
        n = len(c["sources"])
        # The signal, stated plainly - and its first derivative when the
        # cross-build history shows the story accelerating.
        bits = []
        if n >= 3:
            bits.append(f"{n} desks agree")
        elif n == 2:
            bits.append("2 desks on it")
        else:
            bits.append(f"Only {esc(it['source'])} has this")
        if c.get("prev_desks") and n > c["prev_desks"]:
            bits.append(f"&#8599; up from {c['prev_desks']}")
        mins = int((datetime.now(timezone.utc)
                    - parse_date(it["ts"])).total_seconds() // 60)
        if mins < 60:
            bits.append(f"{max(mins, 1)}m ago")
        elif mins < 48 * 60:
            bits.append(f"{mins // 60}h ago")
        else:
            bits.append(f"{mins // 1440}d ago")
        desks = f'<p class="tmeta">{" &middot; ".join(bits)}</p>'
        return (
            f'<article class="tcard">'
            f'<div class="ttop"><span class="tnum">#{rank}</span>'
            f'<button class="bm" type="button" aria-pressed="false" '
            f'aria-label="Read later" data-bm data-title="{esc(it["title"])}" '
            f'data-link="{esc(it["link"])}" data-bm-source="{esc(it["source"])}">'
            f'{BOOKMARK_SVG}</button></div>'
            f'<a class="thl" href="{esc(it["link"])}" rel="nofollow noopener" '
            f'target="_blank">{esc(it["title"])}</a>'
            f'<div class="tfoot"><span class="tsrc">{esc(it["source"])}</span>'
            f'{desks}</div></article>')

    def group(gid, rows, hidden):
        cards = "".join(card(i + 1, c) for i, c in enumerate(rows[:5]))
        return (f'<div class="tgrid" data-trend-group="{gid}"'
                f'{" hidden" if hidden else ""}>{cards}</div>')

    groups = [group("all", hot_ranked, False)]
    chips = ['<button class="chip" type="button" data-trend-chip="all" '
             'aria-pressed="true">All</button>']

    # Consensus: what every desk agrees matters. Exclusives: what exactly one
    # desk is reporting right now - the closest thing a wire has to a scoop.
    consensus = [c for c in clusters if len(c["sources"]) >= 3]
    if len(consensus) >= 2:
        groups.append(group("consensus", consensus, True))
        chips.append('<button class="chip" type="button" '
                     'data-trend-chip="consensus" aria-pressed="false">'
                     'Consensus</button>')
    now_utc = datetime.now(timezone.utc)
    exclusives = [c for c in hot_ranked
                  if len(c["sources"]) == 1
                  and (now_utc - parse_date(c["rep"]["ts"])).total_seconds() < 6 * 3600]
    if len(exclusives) >= 2:
        groups.append(group("exclusives", exclusives, True))
        chips.append('<button class="chip" type="button" '
                     'data-trend-chip="exclusives" aria-pressed="false">'
                     'Exclusives</button>')
    for slug, label in TREND_LABELS:
        topic = by_slug.get(slug)
        if not topic:
            continue
        rows = [c for c in hot_ranked if matches(c["rep"], topic)]
        if len(rows) < 2:
            continue                        # a one-story tab is not a trend
        groups.append(group(slug, rows, True))
        chips.append(f'<button class="chip" type="button" '
                     f'data-trend-chip="{slug}" aria-pressed="false">'
                     f'{esc(label)}</button>')

    return (
        '<section class="trend" data-trend>'
        '<div class="trend-head">'
        '<h2><span class="flame" aria-hidden="true">&#128293;</span> Trending Now</h2>'
        f'<div class="chips trend-chips">{"".join(chips)}</div>'
        '<button class="tcollapse" type="button" aria-expanded="true" '
        'aria-label="Collapse trending">&#9650;</button></div>'
        f'<div class="trend-body">{"".join(groups)}</div>'
        '</section>')


# ── HTML ─────────────────────────────────────────────────────────────────

def esc(s):
    return html.escape(str(s), quote=True)


def stamp(dt):
    """'Aug 3 12:23 PM' - the format the live site uses."""
    hour = dt.hour % 12 or 12
    ampm = "AM" if dt.hour < 12 else "PM"
    return f"{dt.strftime('%b')} {dt.day} {hour}:{dt.strftime('%M')} {ampm}"


# The client's nav, verbatim: the live site shows these nine links flat, in
# this order, with no dropdowns. The extra pages this build adds (economic
# calendar, topics, recaps, newsletter) are linked from the footer and the
# ticker's Events tab instead of changing the bar. Do not regroup this into
# submenus again - that redesign was explicitly rejected.
NAV = [
    ("link", "News", "/"),
    ("link", "Books", "/books/"),
    ("link", "Forex", "/forex/"),
    ("link", "World News", "/world-news/"),
    ("link", "Podcasts", "/podcasts/"),
    ("link", "Contact", "/contact/"),
    ("link", "Preferences", "/preferences/"),
    ("link", "Read Later", "/read-later/"),
    ("link", "Portfolio", "/portfolio/"),
]

# Market clocks in the navbar: label, IANA zone, open/close minutes local.
CLOCKS = [
    ("New York", "America/New_York", 570, 960),
    ("London", "Europe/London", 480, 990),
    ("Frankfurt", "Europe/Berlin", 540, 1050),
    ("Tokyo", "Asia/Tokyo", 540, 900),
    ("Hong Kong", "Asia/Hong_Kong", 570, 960),
]

def _svg(*paths):
    inner = "".join(f'<path d="{d}"/>' for d in paths)
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
            f'aria-hidden="true">{inner}</svg>')


NAV_ICONS = {
    # News only shows in the phone menu; the desktop bar keeps its bare label.
    "News": _svg("M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16"
                 "a2 2 0 0 1-4 0V9h2", "M18 14h-8", "M15 18h-5",
                 "M10 6h8v4h-8z"),
    "Forex": _svg("M8 3L4 7l4 4", "M4 7h16", "M16 21l4-4-4-4", "M20 17H4"),
    "Economic Calendar": _svg("M8 2v4", "M16 2v4",
                              "M3 6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z",
                              "M3 10h18"),
    "Topics": _svg("M4 9h16", "M4 15h16", "M10 3L8 21", "M16 3l-2 18"),
    "Daily recap": _svg("M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z",
                        "M14 2v6h6", "M16 13H8", "M16 17H8"),
    "World News": _svg("M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z", "M2 12h20",
                       "M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 "
                       "15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"),
    "Podcasts": _svg("M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z",
                     "M19 10v2a7 7 0 0 1-14 0v-2", "M12 19v4", "M8 23h8"),
    "Books": _svg("M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z",
                  "M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"),
    "Preferences": _svg("M4 21v-7", "M4 10V3", "M12 21v-9", "M12 8V3",
                        "M20 21v-5", "M20 12V3", "M1 14h6", "M9 8h6", "M17 16h6"),
    "Portfolio": _svg("M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16",
                      "M2 9a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2z"),
    "Contact": _svg("M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z",
                    "M22 6l-10 7L2 6"),
}

BOOKMARK_SVG = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
                'aria-hidden="true"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10'
                'a2 2 0 0 1 2 2z"/></svg>')

# The client's two ad-slot banners, reproduced verbatim from the live site
# (copy, em dash and all - his content, not ours to reword). They are
# placeholder ads there too: plain text, no link, dismissible. The top one
# rides above the nav; the bottom one is fixed to the viewport bottom.
PROMO = ("""<div class="promo" id="promo"><div class="promo-in">"""
         """<span class="tag">AD</span>"""
         """<strong>Market Intelligence Pro</strong>"""
         """<span class="muted">&mdash; Get exclusive market insights and trading signals</span>"""
         """<span class="learn">Click to learn more &rarr;</span>"""
         """<button class="close" id="promo-x" type="button" """
         """aria-label="Dismiss">&times;</button>"""
         """</div></div>""")

BOTBAR = ("""<div class="botbar" id="botbar" hidden><div class="promo-in">"""
          """<span class="tag">AD</span>"""
          """<strong>Financial News Premium</strong>"""
          """<span class="muted">&mdash; Get real-time market alerts and exclusive analysis</span>"""
          """<span class="learn">Click to learn more &rarr;</span>"""
          """<button class="close" id="botbar-x" type="button" """
          """aria-label="Dismiss">&times;</button>"""
          """</div></div>""")


def money(v, dp=2):
    return f"{v:,.{dp}f}"


def signed(v, dp=2, suffix=""):
    return f"{v:+,.{dp}f}{suffix}"


def dir_class(v):
    return "up" if v > 0 else "down" if v < 0 else "flat"


def ticker_strip(mkt):
    """The quote-card band under the nav, matching the live site: centred
    tabs, then four cards per tab with a coloured badge, LIVE dot, price,
    signed change and the as-of time in US Eastern.

    All four panels are server-rendered; the tabs only toggle visibility, so
    it works with JavaScript off and a crawler sees every number.
    """
    if not mkt or not mkt.get("quotes"):
        return ""

    # As-of time, shown as the live site shows it. Quotes are one build old
    # at most, so this is the fetch time, not an exchange timestamp.
    when = ""
    try:
        from zoneinfo import ZoneInfo
        fetched = mkt.get("fetched")
        if fetched:
            et = datetime.fromisoformat(fetched).astimezone(ZoneInfo("America/New_York"))
            hour = et.hour % 12 or 12
            when = f"{hour}:{et.strftime('%M')} {'AM' if et.hour < 12 else 'PM'} EDT"
    except Exception:                               # noqa: BLE001 - cosmetic only
        when = ""

    BADGE = ["#3b82f6", "#10b981", "#a855f7", "#f97316"]   # blue green purple orange

    tabs, panels = [], []
    for i, (tid, label, rows) in enumerate(mkt["tabs"]):
        first = i == 0
        tabs.append(
            f'<button class="tab" type="button" role="tab" id="tab-{tid}" '
            f'aria-controls="panel-{tid}" aria-selected="{"true" if first else "false"}" '
            f'data-tab="{tid}">{esc(label)}</button>')

        cards = []
        for j, (sym, name, code) in enumerate(rows):
            q = mkt["quotes"].get(sym)
            badge = (f'<span class="qbadge" style="background:{BADGE[j % 4]}">'
                     f'{esc(code)}</span>')
            if not q:
                cards.append(
                    f'<div class="qcard"><div class="qtop">'
                    f'<span class="qname">{esc(name)}</span></div>{badge}'
                    f'<p class="qmissing">Unavailable</p></div>')
                continue
            dp = 2 if abs(q["price"]) >= 10 else 4
            cls = dir_class(q["change"])
            arrow = "&#8599;" if q["change"] > 0 else "&#8600;" if q["change"] < 0 else ""
            # The live site says LIVE on every card regardless of quote age
            # (its data is delayed too); match it, the as-of time tells the truth.
            live = '<span class="qlive"><i></i>LIVE</span>'
            cnbc_sym = market.CNBC_SYMBOLS.get(sym, "")
            cards.append(
                f'<div class="qcard" data-sym="{esc(cnbc_sym)}">'
                f'<div class="qtop"><span class="qname">{esc(name)}</span>{live}</div>'
                f'{badge}'
                f'<div class="qprice">{money(q["price"], dp)}</div>'
                f'<div class="qchg {cls}">{arrow} {signed(q["change"], dp)} '
                f'({signed(q["pct"], 2, "%")})</div>'
                + (f'<div class="qtime">{esc(when)}</div>' if when else "")
                + '</div>')

        panels.append(
            f'<div class="quotes" role="tabpanel" id="panel-{tid}" '
            f'aria-labelledby="tab-{tid}"{"" if first else " hidden"}>{"".join(cards)}</div>')

    # Fifth tab: the next market-moving events, so the calendar is one glance
    # away on every page.
    try:
        from zoneinfo import ZoneInfo
        ev_data = json.loads((HERE / "data" / "events.json").read_text(encoding="utf-8"))
        tz = ZoneInfo(ev_data.get("timezone", "America/New_York"))
        today_d = datetime.now(timezone.utc).date()
        upcoming = []
        for e in sorted(ev_data["events"], key=lambda x: (x["date"], x["time"])):
            local = datetime.strptime(f'{e["date"]} {e["time"]}',
                                      "%Y-%m-%d %H:%M").replace(tzinfo=tz)
            if local.date() >= today_d:
                upcoming.append((local, e))
            if len(upcoming) == 4:
                break
        if upcoming:
            CATS = {"fed": "Fed", "inflation": "Inflation", "jobs": "Jobs",
                    "growth": "Growth"}
            cards = []
            for local, e in upcoming:
                days = (local.date() - today_d).days
                big = ("Today" if days == 0 else "Tomorrow" if days == 1
                       else f"{days} days")
                hour = local.hour % 12 or 12
                at = (f'{local.strftime("%A")}, {hour}:{local.strftime("%M")} '
                      f'{"AM" if local.hour < 12 else "PM"} ET')
                cards.append(
                    f'<a class="qcard evc" href="/events/" title="{esc(e["note"])}">'
                    f'<div class="qtop"><span class="qname">{esc(e["name"])}</span>'
                    f'<span class="ev-badge {esc(e["impact"])}">'
                    f'{"HIGH" if e["impact"] == "high" else "MED"}</span></div>'
                    f'<span class="qbadge" style="background:#1f2937">'
                    f'{local.strftime("%b").upper()} {local.day}</span>'
                    f'<div class="qprice">{esc(big)}</div>'
                    f'<div class="qchg flat">{esc(at)}</div>'
                    f'<div class="qtime">{esc(CATS.get(e["category"], "Calendar"))}'
                    f' &middot; Economic calendar</div>'
                    f'</a>')
            tabs.append(
                '<button class="tab" type="button" role="tab" id="tab-events" '
                'aria-controls="panel-events" aria-selected="false" '
                'data-tab="events">Events</button>')
            panels.append(
                '<div class="quotes" role="tabpanel" id="panel-events" '
                f'aria-labelledby="tab-events" hidden>{"".join(cards)}</div>')
    except Exception:                               # noqa: BLE001 - tab is optional
        pass

    return (f'<div class="ticker"><div class="ticker-in">'
            f'<div class="tabs" role="tablist" data-ticker>{"".join(tabs)}</div>'
            f'<div class="panels">{"".join(panels)}</div></div></div>')


def shell(cfg, *, title, description, canonical, body, noindex=False,
          current="/", extra_head="", body_attrs="", scripts="", ticker=""):
    # Bar links are bare text like the live site; only Read Later carries
    # its bookmark glyph, because that is exactly what the client's nav does.
    parts = []
    for kind, label, target in NAV:
        icon = BOOKMARK_SVG if label == "Read Later" else ""
        parts.append('<a href="{}"{}>{}{}</a>'.format(
            target, ' aria-current="page"' if target == current else "",
            icon, esc(label)))
    links = "".join(parts)

    # The phone menu is the old site's pattern: a hamburger opening a
    # full-screen overlay with the same nine links as one flat list.
    mnav = (
        '<button class="burger" id="burger" type="button" aria-label="Open menu" '
        'aria-expanded="false" aria-controls="mnav">'
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" aria-hidden="true">'
        '<path d="M4 7h16M4 12h16M4 17h16"/></svg></button>')
    moverlay = (
        '<div class="mnav" id="mnav" hidden>'
        '<div class="mnav-head">'
        '<span class="logo" aria-hidden="true">'
        '<span class="l1">NEWS</span><span class="l2">NOW</span>'
        '<span class="l3">NEXT</span></span>'
        '<button class="mnav-x" id="mnav-x" type="button" aria-label="Close menu">'
        '&times;</button></div>'
        f'<nav class="mnav-links">{links}</nav></div>')

    clock_rows = "".join(
        f'<div class="clock-row" data-tz="{tz}" data-open="{o}" data-close="{c}">'
        f'<i class="dot"></i><span class="cname">{esc(name)}</span>'
        f'<span class="ctime">--:--</span></div>'
        for name, tz, o, c in CLOCKS)
    clocks = (
        '<div class="clockbox" data-menu data-clocks>'
        '<button class="menu-btn clock-chip" type="button" aria-expanded="false" '
        'aria-haspopup="true" title="Market hours">'
        '<span class="clock-ico" aria-hidden="true">&#128340;</span>'
        '<span data-clock-mini>NY --:--</span>'
        '<span class="caret" aria-hidden="true">&#9662;</span></button>'
        f'<div class="menu-pop clock-pop" hidden>{clock_rows}</div></div>')
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
<meta property="og:site_name" content="{esc(cfg['site_name'])}">
<meta property="og:image" content="{esc(cfg['base_url'].rstrip('/'))}/assets/og.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{esc(cfg['base_url'].rstrip('/'))}/assets/og.png">
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" type="image/svg+xml" href="/assets/favicon.svg">
<link rel="apple-touch-icon" href="/assets/icon-192.png">
<link rel="alternate" type="application/rss+xml" title="{esc(cfg['site_name'])} recaps" href="/feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800;900&display=swap">
<link rel="stylesheet" href="/assets/site.css?v={BUILD_STAMP}">
<link rel="manifest" href="/manifest.webmanifest">
<meta name="theme-color" content="#374151">
{extra_head}
</head>
<body{body_attrs}>
{PROMO}
<div class="chrome">
<nav class="nav">
  <div class="nav-in">
    <a class="logo" href="/" aria-label="{esc(cfg['site_name'])} home">
      <span class="l1">NEWS</span><span class="l2">NOW</span><span class="l3">NEXT</span>
    </a>
    {clocks}
    <div class="nav-links">{links}</div>
    {mnav}
  </div>
</nav>
</div>
{moverlay}
{ticker}
<div class="wrap">
{body}
<button class="totop" id="totop" type="button" aria-label="Back to top" hidden>
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"
       stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path d="M12 19V5"/><path d="M5 12l7-7 7 7"/></svg>
</button>
<button class="ai-fab" id="ai-fab" type="button" aria-expanded="false"
        aria-controls="ai-modal">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
       stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
  </svg>
  Ask AI about News
</button>
<div class="ai-modal" id="ai-modal" hidden>
  <div class="ai-back" id="ai-back"></div>
  <div class="ai-sheet" role="dialog" aria-modal="true"
       aria-label="Ask AI about News &amp; Finance">
    <div class="ai-head">
      <h2>Ask AI about News &amp; Finance</h2>
      <button class="ai-x" id="ai-x" type="button" aria-label="Close">&#10005;</button>
    </div>
    <label class="sr-only" for="ai-q">Ask about the news</label>
    <textarea id="ai-q" autocomplete="off" placeholder="Ask anything! e.g., 'Summarize today's news' or 'Why do Fed rate cuts affect markets?'"></textarea>
    <div class="ai-actions">
      <button class="ai-ask" id="ai-ask" type="button" disabled>Ask AI</button>
      <button class="ai-quick" id="ai-quick" type="button">Quick Summary</button>
      <button class="ai-clear" id="ai-clear" type="button">Clear</button>
    </div>
    <div class="ai-out" id="ai-out">The summary will appear here&hellip;</div>
    <p class="ai-hint">&#128161; <strong>Two modes:</strong> <span id="ai-hint-modes">Ask
      about current news or general finance topics (Fed policy, markets,
      economics, etc.)</span></p>
  </div>
</div>
</div>
<footer class="foot">
  <div class="foot-in">
    <p class="foot-tag">Never refresh, never miss - real-time news feed</p>
    <p class="foot-links"><a href="/topics/">Topics</a> &middot;
       <a href="/recap/">Daily recap</a> &middot;
       <a href="/events/">Economic calendar</a> &middot;
       <a href="/newsletter/">Newsletter</a> &middot;
       <a href="/feed.xml">RSS</a></p>
    <div class="foot-rule"></div>
    <p>&copy; 2026 {esc(cfg['site_name'])}. All Rights Reserved.</p>
    <p>Content may not be reproduced without permission.</p>
  </div>
</footer>
{BOTBAR}
<script src="/assets/pages.js?v={BUILD_STAMP}" defer></script>
{scripts}
</body>
</html>
"""


def filter_bar(cfg, regions_present):
    """One line: search, region, order, count.

    Region was eight chips and order was a block below it; together they pushed
    the first headline off the fold. Both are menus now.
    """
    regions = "".join(
        f'<option value="{esc(r["id"])}">{esc(r["title"])}</option>'
        for r in cfg["regions"] if r["id"] in regions_present)
    topics = "".join(
        f'<option value="{esc(t["slug"])}">{esc(t["title"])}</option>'
        for t in cfg["topics"])
    return f"""
<div class="filters" data-filters hidden>
  <div class="fsearch">
    <label class="sr-only" for="f-q">Filter headlines</label>
    <input id="f-q" type="search" autocomplete="off" spellcheck="false"
           placeholder="Search headlines…">
  </div>
  <label class="sr-only" for="f-region">Region</label>
  <select id="f-region" class="fsel">
    <option value="">All regions</option>{regions}
  </select>
  <label class="sr-only" for="f-topic">Topic</label>
  <select id="f-topic" class="fsel">
    <option value="">All topics</option>{topics}
  </select>
  <label class="sr-only" for="f-window">Time</label>
  <select id="f-window" class="fsel">
    <option value="0">Any time</option>
    <option value="6">Last 6h</option>
    <option value="12">Last 12h</option>
    <option value="24">Last 24h</option>
  </select>
  <label class="sr-only" for="f-sort">Order</label>
  <select id="f-sort" class="fsel">
    <option value="newest">Newest</option>
    <option value="oldest">Oldest</option>
  </select>
  <p class="fcount">
    <span id="f-count">-</span>
    <button class="linkbtn" id="f-clear" type="button" hidden>Clear</button>
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
                f'<button class="bm bm-sm" type="button" aria-pressed="false" '
                f'aria-label="Read later" data-bm data-title="{esc(it["title"])}" '
                f'data-link="{esc(it["link"])}" data-bm-source="{esc(it["source"])}">'
                f'{BOOKMARK_SVG}</button>'
                f'</li>'
            )
        via = f' <span class="via">via {esc(src["via"])}</span>' if src.get("via") else ""
        logo = ""
        if (HERE / "static" / "logos" / f"{src['id']}.png").exists():
            logo = (f'<img class="srclogo" alt="" width="16" height="16" '
                    f'loading="lazy" src="/assets/logos/{esc(src["id"])}.png">')
        blocks.append(
            f'<div class="src" data-source="{esc(src["id"])}">'
            f'<h3>{logo}{esc(src["label"])}{via}</h3>'
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



def forex_page(cfg, mkt, base, out):
    """The 18-pair table, matching the live site's columns exactly."""
    fx = mkt.get("fx") or {}
    spans = mkt.get("spans", [])
    heads = "".join(f"<th>{esc(x)}</th>" for x in spans)
    rows = []
    for pair in mkt.get("pairs", []):
        v = fx.get(pair)
        if not v:
            continue
        cells = []
        for span in spans:
            ch = v["changes"].get(span)
            if ch is None:
                cells.append('<td class="flat">n/a</td>')
            else:
                cells.append(f'<td class="{dir_class(ch)}">'
                             f'{signed(ch, 2, "%")}</td>')
        # The dot mirrors the daily direction, like the live site's rows.
        daily = v["changes"].get(spans[0]) if spans else None
        dot = dir_class(daily) if daily is not None else "flat"
        rows.append(
            f'<tr><td><div class="fx-pair">'
            f'<span class="fx-dot {dot}" aria-hidden="true"></span>'
            f'<span class="fx-name">{esc(pair)}</span>'
            f'<span class="fx-rate">{money(v["rate"], 4)}</span></div></td>'
            f'{"".join(cells)}</tr>')

    # The live site's forex page carries an Economic Calendar card below the
    # pairs ("Upcoming events for the next 7 days"). Its API fetch is broken
    # there; ours renders the same section from data/events.json.
    from zoneinfo import ZoneInfo
    ev_data = json.loads((HERE / "data" / "events.json").read_text(encoding="utf-8"))
    ev_tz = ZoneInfo(ev_data.get("timezone", "America/New_York"))
    today = datetime.now(timezone.utc).date()
    week, later = [], []
    for e in ev_data["events"]:
        d = datetime.strptime(f'{e["date"]} {e["time"]}', "%Y-%m-%d %H:%M")
        local = d.replace(tzinfo=ev_tz)
        days_out = (local.date() - today).days
        if 0 <= days_out <= 7:
            week.append((local, e))
        elif days_out > 7:
            later.append((local, e))
    week.sort(key=lambda x: x[0])
    later.sort(key=lambda x: x[0])
    # A quiet week would leave his card empty; fall through to the next
    # scheduled releases so there is always something to show.
    cal_sub = "Upcoming events for the next 7 days"
    if not week:
        week = later[:4]
        cal_sub = "Next scheduled releases"
    cal_rows = "".join(
        f'<div class="fxcal-row">'
        f'<span class="fxcal-date">{local.strftime("%a %b")} {local.day}</span>'
        f'<span class="fxcal-name">{esc(e["name"])}</span>'
        f'<span class="ev-badge {esc(e["impact"])}">'
        f'{"HIGH" if e["impact"] == "high" else "MED"}</span>'
        f'<span class="fxcal-when">{local.strftime("%-I:%M %p")} ET</span>'
        f'</div>'
        for local, e in week) or \
        '<p class="empty">No major US releases in the next 7 days.</p>'
    calendar = (
        '<section class="fxbox">'
        '<h2>Economic Calendar</h2>'
        f'<p class="fxcal-sub">{cal_sub}</p>'
        f'{cal_rows}'
        '<p class="fx-note">Times in US Eastern &middot; '
        '<a href="/events/">Full calendar &rarr;</a></p>'
        '</section>')

    asof = market.load_cache().get("fx_date") or ""
    body = (
        '<div class="sr-only"><h1>Forex</h1>'
        '<p>Major currency pairs and how far they have moved.</p></div>'
        + (('<section class="fxbox">'
            '<h2>Major Pairs</h2>'
            '<div class="tablewrap"><table class="fx"><thead><tr><th>Pair</th>'
            f'{heads}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            f'<p class="fx-note">ECB reference rates'
            f'{f", as of {esc(asof)}" if asof else ""} - one rate per business '
            'day, so moves are day-over-day rather than intraday.</p>'
            '</section>')
           if rows else
           '<p class="empty">Rates are temporarily unavailable. '
           'The next build will restore them.</p>')
        + calendar)
    write(out / "forex" / "index.html", shell(
        cfg, title=f"Forex Trading & Economic Calendar - {cfg['site_name']}",
        description=("Live major forex pairs with daily, weekly, monthly, "
                     "year-to-date, one-year and three-year moves, plus the "
                     "week's US economic calendar."),
        canonical=f"{base}/forex/", body=body, current="/forex/",
        ticker=ticker_strip(mkt),
        extra_head=breadcrumbs(base, [("Forex", "/forex/")]),
    ))
    return f"{base}/forex/"


def books_page(cfg, mkt, base, out):
    """The 120-title reading list, with the client's affiliate tag preserved."""
    data = json.loads((HERE / "data" / "books.json").read_text(encoding="utf-8"))
    tag = data["affiliate_tag"]
    cat_order = {c: i for i, c in enumerate(data["categories"])}
    books = sorted(data["books"],
                   key=lambda b: (cat_order.get(b[3], 99), b[0].lower()))

    cat_opts = '<option value="">All</option>' + "".join(
        f'<option value="{esc(c)}">{esc(c)}</option>'
        for c in data["categories"])

    # One gradient per category, so the shelf reads as organised colour.
    HUES = {c: h for c, h in zip(data["categories"],
            [214, 160, 262, 20, 340, 190, 30, 280, 120, 0])}

    covers_map = {}
    cmap_path = HERE / "static" / "covers" / "map.json"
    if cmap_path.exists():
        covers_map = json.loads(cmap_path.read_text(encoding="utf-8"))

    cards = []
    seen_cat = None
    for title, author, year, cat in books:
        if cat != seen_cat:
            seen_cat = cat
            n = sum(1 for b in books if b[3] == cat)
            hh = HUES.get(cat, 214)
            cards.append(
                f'<h2 class="bshelf" data-shelf '
                f'style="--shelf:hsl({hh},65%,46%)">'
                f'<span class="bshelf-dot" aria-hidden="true"></span>'
                f'{esc(cat)}<span class="bshelf-n">{n} books</span></h2>')
        q = urllib.parse.quote(f"{title} {author}")
        href = f"https://amazon.com/s?k={q}&tag={tag}"
        h = HUES.get(cat, 214)
        initial = re.sub(r"^(The|A|An)\s+", "", title)[:1].upper()
        cover_file = covers_map.get(title)
        # His card: full-width 3:4 portrait cover on top, then category,
        # title, author-dot-year and the Amazon link.
        if cover_file and (HERE / "static" / "covers" / cover_file).exists():
            cover = (f'<span class="bcover">'
                     f'<img src="/assets/covers/{esc(cover_file)}" '
                     f'alt="{esc(title)}" loading="lazy"></span>')
        else:
            cover = (f'<span class="bcover bcover-ph" aria-hidden="true" '
                     f'style="background:linear-gradient(160deg,'
                     f'hsl({h},65%,46%),hsl({(h + 40) % 360},60%,32%))">'
                     f'{esc(initial)}</span>')
        cards.append(
            f'<article class="book" data-book data-cat="{esc(cat)}" '
            f'data-year="{year}" data-title="{esc(title.lower())}">'
            f'{cover}<div class="binfo">'
            f'<span class="book-cat">{esc(cat)}</span>'
            f'<h3>{esc(title)}</h3>'
            f'<p class="byline">{esc(author)} &bull; {year}</p>'
            f'<a class="buy" href="{esc(href)}" rel="nofollow sponsored noopener" '
            f'target="_blank">Buy on Amazon &rarr;</a></div></article>')

    ld = json.dumps({
        "@context": "https://schema.org", "@type": "ItemList",
        "name": "Best Finance & Business Books",
        "numberOfItems": len(books),
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1,
             "item": {"@type": "Book", "name": t, "author": {"@type": "Person", "name": a},
                      "datePublished": str(y)}}
            for i, (t, a, y, _) in enumerate(books)
        ],
    })

    # His page head and his three controls, verbatim: search box, category
    # dropdown defaulting to All, sort dropdown. The shelf grouping below
    # is this build's one addition to the layout.
    body = (
        '<div class="page-head"><h1>Best Finance &amp; Business Books</h1>'
        f'<p class="standfirst">Curated by {esc(cfg["site_name"])}</p></div>'
        '<div class="filters bfilters" data-book-filters hidden>'
        '<div class="fsearch">'
        '<label class="sr-only" for="b-q">Search books</label>'
        '<input id="b-q" type="search" autocomplete="off" placeholder="Search title or author">'
        '</div>'
        '<label class="sr-only" for="b-cat">Category</label>'
        f'<select id="b-cat" class="fsel">{cat_opts}</select>'
        '<label class="sr-only" for="b-sort">Order</label>'
        '<select id="b-sort" class="fsel">'
        '<option value="az">Sort A&ndash;Z</option>'
        '<option value="new">Sort Newest</option>'
        '<option value="old">Sort Oldest</option></select>'
        '</div>'
        '<p class="empty" id="b-empty" hidden>No books match those filters.</p>'
        f'<div class="books" id="book-grid">{"".join(cards)}</div>'
    )

    write(out / "books" / "index.html", shell(
        cfg, title=f"{len(books)} best finance and business books - {cfg['site_name']}",
        description=("A curated reading list of finance, investing, economics and "
                     "business books, filterable by category and sortable by year."),
        canonical=f"{base}/books/", body=body, current="/books/",
        ticker=ticker_strip(mkt),
        extra_head=(f'<script type="application/ld+json">{ld}</script>'
                    + breadcrumbs(base, [("Books", "/books/")])),
        scripts=f'<script src="/assets/books.js?v={BUILD_STAMP}" defer></script>',
    ))
    return f"{base}/books/"




def events_page(cfg, mkt, base, out):
    """US economic calendar: the scheduled releases that move markets.

    Data lives in data/events.json and is maintained by hand - these dates
    are published well in advance but do occasionally shift. The page only
    renders future events, and the build warns when the file runs low.
    """
    from zoneinfo import ZoneInfo
    data = json.loads((HERE / "data" / "events.json").read_text(encoding="utf-8"))
    tz = ZoneInfo(data.get("timezone", "America/New_York"))
    today = datetime.now(timezone.utc).date()

    CATS = {"fed": "Fed", "inflation": "Inflation", "jobs": "Jobs",
            "growth": "Growth", "other": "Other"}

    future = []
    for e in data["events"]:
        d = datetime.strptime(f'{e["date"]} {e["time"]}', "%Y-%m-%d %H:%M")
        local = d.replace(tzinfo=tz)
        if local.date() < today:
            continue
        future.append((local, e))
    future.sort(key=lambda x: x[0])
    if len(future) < 5:
        print(f"  NOTE: only {len(future)} future events left in data/events.json "
              f"- time to update it")

    rows, seen_month, ld_items = [], None, []
    for local, e in future:
        utc = local.astimezone(timezone.utc)
        month = local.strftime("%B %Y")
        if month != seen_month:
            rows.append(f'<h2 class="ev-month">{esc(month)}</h2>')
            seen_month = month
        cat = CATS.get(e["category"], "Other")
        hour = local.hour % 12 or 12
        when = f'{hour}:{local.strftime("%M")} {"AM" if local.hour < 12 else "PM"} ET'
        rows.append(
            f'<article class="ev" data-ev data-cat="{esc(e["category"])}" '
            f'data-utc="{utc.strftime("%Y%m%dT%H%M%SZ")}">'
            f'<div class="ev-date"><span class="ev-day">{local.day}</span>'
            f'<span class="ev-wd">{local.strftime("%a")}</span></div>'
            f'<div class="ev-body">'
            f'<div class="ev-line"><h3>{esc(e["name"])}</h3>'
            f'<span class="ev-badge {esc(e["impact"])}">'
            f'{"HIGH" if e["impact"] == "high" else "MED"}</span>'
            f'<span class="ev-cat">{esc(cat)}</span></div>'
            f'<p class="ev-note">{esc(e["note"])}</p>'
            f'<div class="ev-foot"><span class="ev-when">{esc(when)}</span>'
            f'<span class="ev-count" data-count></span>'
            f'<a class="linkbtn ev-cal" target="_blank" rel="noopener" '
            f'href="https://calendar.google.com/calendar/render?action=TEMPLATE'
            f'&text={urllib.parse.quote(e["name"])}'
            f'&dates={utc.strftime("%Y%m%dT%H%M%SZ")}/'
            f'{(utc + timedelta(hours=1)).strftime("%Y%m%dT%H%M%SZ")}'
            f'&details={urllib.parse.quote(e["note"])}&ctz=America/New_York">'
            f'+ Add to calendar</a></div>'
            f'</div></article>')
        ld_items.append({
            "@type": "Event", "name": e["name"],
            "startDate": local.isoformat(),
            "eventStatus": "https://schema.org/EventScheduled",
            "location": {"@type": "VirtualLocation", "url": f"{base}/events/"},
            "description": e["note"],
        })

    ics_lines = ["BEGIN:VCALENDAR", "VERSION:2.0",
                 "PRODID:-//NewsNowNext//Economic Calendar//EN",
                 "X-WR-CALNAME:US Economic Calendar - NewsNowNext",
                 "X-WR-TIMEZONE:UTC"]
    for local, e in future:
        utc = local.astimezone(timezone.utc)
        end = utc + timedelta(hours=1)
        ics_lines += ["BEGIN:VEVENT",
                      f"UID:{utc.strftime('%Y%m%dT%H%M%SZ')}-"
                      f"{re.sub(r'[^A-Za-z0-9]', '', e['name'])[:24]}@newsnownext.org",
                      f"DTSTAMP:{utc.strftime('%Y%m%dT%H%M%SZ')}",
                      f"DTSTART:{utc.strftime('%Y%m%dT%H%M%SZ')}",
                      f"DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}",
                      "SUMMARY:" + e["name"].replace(",", "\\,"),
                      "DESCRIPTION:" + e["note"].replace(",", "\\,"),
                      "END:VEVENT"]
    ics_lines.append("END:VCALENDAR")
    write(out / "events" / "calendar.ics", "\r\n".join(ics_lines))
    host = base.split("//", 1)[-1]

    chips = ['<button class="chip" type="button" data-ev-chip="all" '
             'aria-pressed="true">All</button>'] + [
        f'<button class="chip" type="button" data-ev-chip="{k}" '
        f'aria-pressed="false">{esc(v)}</button>'
        for k, v in CATS.items()
        if any(e["category"] == k for _, e in future)]

    ld = json.dumps({"@context": "https://schema.org", "@type": "ItemList",
                     "name": "US economic calendar",
                     "itemListElement": [
                         {"@type": "ListItem", "position": i + 1, "item": it}
                         for i, it in enumerate(ld_items)]})

    body = (
        '<div class="page-head"><h1>Economic Calendar</h1>'
        '<p class="standfirst">The US releases that move markets, in order. '
        'All times Eastern.</p></div>'
        f'<div class="filters" data-ev-filters>{"".join(chips)}'
        '<p class="fcount"><span id="ev-count-all"></span>'
        f'<a class="linkbtn" href="webcal://{esc(host)}/events/calendar.ics">'
        'Subscribe to this calendar</a></p></div>'
        f'<div class="prose evlist">{"".join(rows)}</div>'
        '<p class="intro"><p>Dates follow the official release calendars and are '
        'maintained by hand; the occasional reschedule is possible. '
        'Add-to-calendar files are generated in your browser.</p></p>')

    write(out / "events" / "index.html", shell(
        cfg, title=f"US economic calendar - Fed, CPI, jobs - {cfg['site_name']}",
        description=("Upcoming US market-moving events: FOMC decisions, CPI, "
                     "jobs reports and GDP, with times and calendar files."),
        canonical=f"{base}/events/", body=body, current="/events/",
        ticker=ticker_strip(mkt),
        extra_head=(f'<script type="application/ld+json">{ld}</script>'
                    + breadcrumbs(base, [("Economic Calendar", "/events/")])),
    ))
    return f"{base}/events/"


def podcasts_page(cfg, mkt, base, out):
    """Curated episode summaries - the only wholly original text on the site,
    and therefore the page most worth indexing."""
    data = json.loads((HERE / "data" / "podcasts.json").read_text(encoding="utf-8"))
    eps = data["episodes"]

    tmap = {}
    tmap_path = HERE / "static" / "podcasts" / "map.json"
    if tmap_path.exists():
        tmap = json.loads(tmap_path.read_text(encoding="utf-8"))

    cards = []
    for e in eps:
        when = datetime.fromisoformat(e["date"])
        thumb = tmap.get(e["url"])
        if thumb and (HERE / "static" / "podcasts" / thumb["file"]).exists():
            play = ('<span class="pod-play" aria-hidden="true">&#9654;</span>'
                    if thumb["kind"] == "youtube" else "")
            kind = "Watch" if thumb["kind"] == "youtube" else "Read"
            media = (f'<a class="pod-thumb" href="{esc(e["url"])}" '
                     f'rel="noopener" target="_blank" tabindex="-1">'
                     f'<img src="/assets/podcasts/{esc(thumb["file"])}" alt="" '
                     f'loading="lazy">{play}'
                     f'<span class="pod-kind">{kind}</span></a>')
        else:
            media = ""
        cards.append(
            f'<article class="pod" data-pod '
            f'data-hay="{esc((e["title"] + " " + e["guest"] + " " + e["host"] + " " + e["summary"]).lower())}" '
            f'data-ts="{int(when.timestamp())}">'
            f'{media}'
            f'<div class="pod-body">'
            f'<h2><a href="{esc(e["url"])}" rel="noopener" target="_blank">'
            f'{esc(e["title"])}</a></h2>'
            # A solo episode lists the same name as guest and host; saying
            # it twice reads like a data bug, so collapse to Host.
            + (f'<p class="pod-meta"><strong>Host</strong> {esc(e["host"])}'
               if e["guest"].strip().lower() == e["host"].strip().lower() else
               f'<p class="pod-meta"><strong>Guest</strong> {esc(e["guest"])}'
               f'<span class="dot">&middot;</span><strong>Host</strong> {esc(e["host"])}')
            + f'<span class="dot">&middot;</span>'
            f'<time datetime="{e["date"]}">{when.strftime("%d %B %Y")}</time></p>'
            f'<p class="pod-sum" data-pod-sum>{esc(e["summary"])}</p>'
            f'<div class="pod-foot">'
            f'<button class="linkbtn" type="button" data-pod-more hidden>'
            f'Show more</button>'
            f'<a class="pod-link" href="{esc(e["url"])}" rel="noopener" '
            f'target="_blank">Listen to the full episode &rarr;</a></div>'
            f'</div></article>')

    ld = json.dumps({
        "@context": "https://schema.org", "@type": "ItemList",
        "name": "Podcast summaries",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1,
             "item": {"@type": "PodcastEpisode", "name": e["title"],
                      "datePublished": e["date"], "abstract": e["summary"],
                      "url": e["url"]}}
            for i, e in enumerate(eps)],
    })

    body = (
        '<div class="page-head"><h1>Podcast summaries</h1>'
        f'<p class="standfirst">{len(eps)} curated insights from top business and '
        'technology podcasts - what was actually said, in a paragraph.</p></div>'
        '<div class="filters" data-pod-filters hidden>'
        '<div class="fsearch"><label class="sr-only" for="p-q">Filter episodes</label>'
        '<input id="p-q" type="search" autocomplete="off" '
        'placeholder="Search guests, hosts or topics…"></div>'
        '<label class="sr-only" for="p-sort">Order</label>'
        '<select id="p-sort" class="fsel">'
        '<option value="new">Newest first</option>'
        '<option value="old">Oldest first</option></select>'
        '<p class="fcount"><span id="p-count"></span></p></div>'
        '<p class="empty" id="p-empty" hidden>No episodes match that search.</p>'
        f'<div class="pods" id="pod-list">{"".join(cards)}</div>')

    write(out / "podcasts" / "index.html", shell(
        cfg, title=f"Podcast summaries - business and tech insights - {cfg['site_name']}",
        description=("Curated summaries of the best business, macro and technology "
                     "podcasts: guest, host and the argument in one paragraph."),
        canonical=f"{base}/podcasts/", body=body, current="/podcasts/",
        ticker=ticker_strip(mkt),
        extra_head=(f'<script type="application/ld+json">{ld}</script>'
                    + breadcrumbs(base, [("Podcasts", "/podcasts/")])),
    ))
    return f"{base}/podcasts/"


WORLD = [
    ("United States", "us", "US"), ("United Kingdom", "uk", "GB"),
    ("China", "china", "CN"), ("France", "france", "FR"),
    ("Germany", "germany", "DE"), ("Switzerland", "switzerland", "CH"),
    ("Japan", "japan", "JP"), ("India", "india", "IN"),
    ("Brazil", "brazil", "BR"), ("Canada", "canada", "CA"),
    ("Australia", "australia", "AU"), ("Israel", "israel", "IL"),
    ("United Arab Emirates", "uae", "AE"), ("Singapore", "singapore", "SG"),
    ("South Africa", "south-africa", "ZA"), ("Mexico", "mexico", "MX"),
    ("Italy", "italy", "IT"), ("Spain", "spain", "ES"),
    ("Turkey", "turkey", "TR"), ("South Korea", "south-korea", "KR"),
]


def world_page(cfg, mkt, base, out, world_items):
    """Local coverage by country. A grid rather than a clickable map: the map
    itself is invisible to search engines, and this renders every headline."""
    cards = []
    for name, slug, cc in WORLD:
        rows = world_items.get(slug, [])
        if not rows:
            continue
        flag = "".join(chr(127397 + ord(c)) for c in cc)
        lis = []
        for it in rows[:8]:
            when = parse_date(it["ts"])
            lis.append(
                f'<li data-item data-src="{esc(it["source"])}" data-region="{esc(slug)}" '
                f'data-ts="{when.timestamp():.0f}">'
                f'<a href="{esc(it["link"])}" rel="nofollow noopener" target="_blank">'
                f'{esc(it["title"])}</a>'
                f'<time datetime="{when.isoformat()}">{esc(stamp(when))}</time>'
                f'<button class="bm bm-sm" type="button" aria-pressed="false" '
                f'aria-label="Read later" data-bm data-title="{esc(it["title"])}" '
                f'data-link="{esc(it["link"])}" data-bm-source="{esc(it["source"])}">'
                f'{BOOKMARK_SVG}</button></li>')
        cards.append(
            f'<section class="card" data-region="{esc(slug)}">'
            f'<div class="card-head"><h2><span class="flag">{flag}</span> {esc(name)}</h2>'
            f'<span class="card-count" data-card-count>{len(rows[:8])}</span></div>'
            f'<div class="src" data-source="{esc(slug)}">'
            f'<ul class="items">{"".join(lis)}</ul></div></section>')

    body = (
        '<div class="page-head"><h1>World News</h1>'
        '<p class="standfirst">Local reporting from around the globe, in English, '
        'straight from each country&rsquo;s own desks.</p></div>'
        + ('<div class="grid">' + "".join(cards) + '</div>' if cards else
           '<p class="empty">Country feeds are temporarily unavailable.</p>'))

    write(out / "world-news" / "index.html", shell(
        cfg, title=f"World News - local reporting by country - {cfg['site_name']}",
        description=("Local English-language news by country: the United States, "
                     "China, France, Germany, Japan, India, Brazil and more."),
        canonical=f"{base}/world-news/", body=body, current="/world-news/",
        ticker=ticker_strip(mkt),
        extra_head=breadcrumbs(base, [("World News", "/world-news/")]),
    ))
    return f"{base}/world-news/"


def simple_page(cfg, mkt, base, out, *, path, title, heading, description,
                body_html, current, index=True):
    write(out / path.strip("/") / "index.html", shell(
        cfg, title=title, description=description,
        canonical=f"{base}{path}", current=current, noindex=not index,
        ticker=ticker_strip(mkt),
        body=(f'<div class="prose"><div class="page-head"><h1>{esc(heading)}</h1>'
              f'<p class="standfirst">{esc(description)}</p></div>{body_html}</div>'),
        extra_head=breadcrumbs(base, [(heading, path)]),
    ))
    return f"{base}{path}"


def breadcrumbs(base, trail):
    items = [{"@type": "ListItem", "position": 1, "name": "Home", "item": f"{base}/"}]
    for i, (name, path) in enumerate(trail, start=2):
        items.append({"@type": "ListItem", "position": i, "name": name,
                      "item": f"{base}{path}"})
    ld = json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList",
                     "itemListElement": items})
    return f'<script type="application/ld+json">{ld}</script>'


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
            f'<div class="wire-body">'
            f'<a href="{esc(it["link"])}" rel="nofollow noopener" target="_blank">'
            f'{esc(it["title"])}</a>'
            f'<span class="src-tag">{esc(it["source"])}{via}</span></div>'
            f'<button class="bm bm-sm" type="button" aria-pressed="false" '
            f'aria-label="Read later" data-bm data-title="{esc(it["title"])}" '
            f'data-link="{esc(it["link"])}" data-bm-source="{esc(it["source"])}">'
            f'{BOOKMARK_SVG}</button></li>'
        )
    if current_day is not None:
        out.append("</ol>")
    return "\n".join(out) or '<p class="empty">Nothing on the wire in this window.</p>'


# ── Build ────────────────────────────────────────────────────────────────

def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  wrote {path.name}")


def build(cfg, items, out: Path, mkt=None):
    base = cfg["base_url"].rstrip("/")
    mkt = mkt or {}
    urls = []

    write(out / "assets" / "site.css", CSS.strip())
    og_src = HERE / "static" / "og.png"
    if og_src.exists():
        (out / "assets").mkdir(parents=True, exist_ok=True)
        (out / "assets" / "og.png").write_bytes(og_src.read_bytes())
        print("  wrote og.png")
    write(out / "manifest.webmanifest", json.dumps({
        "name": cfg["site_name"],
        "short_name": cfg["site_name"],
        "description": cfg.get("tagline", ""),
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#374151",
        "icons": [
            {"src": "/assets/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/assets/icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    }, indent=1))

    # Cache-first for the shell, network-first for pages: the app opens
    # instantly and still works on the subway, showing the last pull.
    sw_version = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    write(out / "sw.js", """
var CACHE = 'nnn-%s';
var SHELL = ['/', '/assets/site.css', '/assets/pages.js', '/assets/filter.js',
             '/offline.html', '/assets/icon-192.png'];
self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(SHELL); })
    .then(function () { return self.skipWaiting(); }));
});
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k !== CACHE; })
      .map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});
self.addEventListener('fetch', function (e) {
  var url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  // Live data and the portfolio backend must never be cache-served.
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/portfolio')) return;
  if (url.pathname.startsWith('/assets/')) {
    // Stale-while-revalidate: paint from cache instantly, refresh it in the
    // background so the next load is never more than one build behind.
    e.respondWith(caches.match(e.request).then(function (hit) {
      var refresh = fetch(e.request).then(function (res) {
        var copy = res.clone();
        caches.open(CACHE).then(function (c) { c.put(e.request, copy); });
        return res;
      }).catch(function () { return hit; });
      return hit || refresh;
    }));
    return;
  }
  e.respondWith(fetch(e.request).then(function (res) {
    var copy = res.clone();
    caches.open(CACHE).then(function (c) { c.put(e.request, copy); });
    return res;
  }).catch(function () {
    return caches.match(e.request).then(function (hit) {
      return hit || caches.match('/offline.html');
    });
  }));
});
""".strip() % sw_version)

    # Cloudflare Pages advanced-mode worker. Two jobs:
    #  - /api/quotes: live CNBC quotes cached ~15s at the edge, so the
    #    ticker can refresh client-side (CNBC 403s browser origins).
    #  - /api/* and /portfolio: proxied to the client's original Railway
    #    backend, which still runs his login + watchlist system. If the
    #    backend does not answer (Railway routes by Host header), the
    #    static page is served instead of an error.
    cnbc_url = market.CNBC.format("|".join(market.CNBC_SYMBOLS.values()))
    write(out / "_worker.js", """
// Generated by build.py - edit there, not here.
// The service's generated Railway domain: routes to his app directly, no
// Host-header tricks (Cloudflare strips those - the old CNAME targets
// only answered to Host www.newsnownext.org and were unreachable here).
var RAILWAY = 'https://newsnownext-production.up.railway.app';
var CNBC_URL = %s;

function num(v) {
  if (v === null || v === undefined) return null;
  var t = String(v).replace(/,/g, '').replace(/%%/g, '').trim();
  if (t === '' || t === 'UNCH' || t === 'N/A' || t === '--') return 0;
  var n = parseFloat(t);
  return isNaN(n) ? null : n;
}

async function quotes(ctx) {
  var cache = caches.default;
  var key = new Request('https://quotes.internal/api/quotes');
  var hit = await cache.match(key);
  if (hit) return hit;
  var r = await fetch(CNBC_URL, {headers: {'User-Agent': 'Mozilla/5.0'}});
  if (!r.ok) return new Response('{}', {status: 502,
    headers: {'content-type': 'application/json'}});
  var raw = await r.json();
  var rows = ((raw.FormattedQuoteResult || {}).FormattedQuote) || [];
  var out = {};
  for (var i = 0; i < rows.length; i++) {
    var q = rows[i];
    var last = num(q.last), change = num(q.change);
    if (last === null || change === null) continue;
    var prev = last - change;
    out[q.symbol] = {price: last, change: change,
                     pct: prev ? change / prev * 100 : 0};
  }
  var res = new Response(JSON.stringify({t: Date.now(), q: out}), {
    headers: {'content-type': 'application/json',
              'cache-control': 'public, s-maxage=15, max-age=5'}});
  ctx.waitUntil(cache.put(key, res.clone()));
  return res;
}

async function railway(request, url) {
  var target = RAILWAY + url.pathname + url.search;
  try {
    return await fetch(target, {
      method: request.method, headers: request.headers,
      body: (request.method === 'GET' || request.method === 'HEAD')
        ? undefined : request.body,
      redirect: 'manual',
    });
  } catch (e) {
    return null;
  }
}

function fromRailway(res) {
  return res && res.status < 500 && !res.headers.get('x-railway-fallback');
}

export default {
  async fetch(request, env, ctx) {
    var url = new URL(request.url);
    if (url.pathname === '/api/quotes') return quotes(ctx);
    if (url.pathname.startsWith('/api/')) {
      var r = await railway(request, url);
      return r || new Response('{"error":"backend unreachable"}', {
        status: 502, headers: {'content-type': 'application/json'}});
    }
    if (url.pathname === '/portfolio' || url.pathname.startsWith('/portfolio/')) {
      var p = await railway(request, url);
      if (fromRailway(p)) return p;
      return env.ASSETS.fetch(request);
    }
    var res = await env.ASSETS.fetch(request);
    // The old app's hashed bundles (its /assets/index-*.js) are not in the
    // static build; let them fall through to the backend.
    if (res.status === 404 && url.pathname.startsWith('/assets/')) {
      var a = await railway(request, url);
      if (fromRailway(a)) return a;
    }
    return res;
  },
};
""".strip() % json.dumps(cnbc_url))

    for icon in ("icon-192.png", "icon-512.png"):
        src = HERE / "static" / icon
        if src.exists():
            (out / "assets" / icon).write_bytes(src.read_bytes())

    # favicon.ico lives at the root because browsers and crawlers probe
    # /favicon.ico regardless of link tags; the SVG rides with the assets.
    for name, rel in (("favicon.svg", "assets/favicon.svg"),
                      ("favicon.ico", "favicon.ico")):
        src = HERE / "static" / name
        if src.exists():
            (out / rel).parent.mkdir(parents=True, exist_ok=True)
            (out / rel).write_bytes(src.read_bytes())

    write(out / "offline.html", shell(
        cfg, title=f"Offline - {cfg['site_name']}",
        description="You are offline.", canonical=f"{base}/offline.html",
        noindex=True,
        body=('<div class="prose"><div class="page-head"><h1>You&rsquo;re offline</h1>'
              '<p class="standfirst">The wire needs a connection. Pages you have '
              'already visited are cached and still open.</p></div></div>'),
    ))

    for sub, pattern in (("logos", "*.png"), ("covers", "*.jpg"),
                         ("podcasts", "*.jpg")):
        src_dir = HERE / "static" / sub
        if not src_dir.is_dir():
            continue
        dest = out / "assets" / sub
        dest.mkdir(parents=True, exist_ok=True)
        n = 0
        for f in src_dir.glob(pattern):
            (dest / f.name).write_bytes(f.read_bytes())
            n += 1
        print(f"  wrote {n} {sub}")
    write(out / "assets" / "filter.js", FILTER_JS.strip())
    write(out / "assets" / "books.js", BOOKS_JS.strip())
    write(out / "assets" / "pages.js", PAGES_JS.strip())

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
    site_ld = json.dumps({
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Organization", "name": cfg["site_name"], "url": f"{base}/",
             "logo": f"{base}/assets/og.png"},
            {"@type": "WebSite", "name": cfg["site_name"], "url": f"{base}/",
             "potentialAction": {
                 "@type": "SearchAction",
                 "target": {"@type": "EntryPoint",
                            "urlTemplate": f"{base}/?q={{search_term_string}}"},
                 "query-input": "required name=search_term_string"}},
        ],
    })
    today = datetime.now(timezone.utc).date()
    syn_path = HERE / "synopsis" / f"{today.isoformat()}.txt"
    brief_html = ""
    if syn_path.exists():
        syn = syn_path.read_text(encoding="utf-8").strip()
        paras = [x.strip() for x in syn.split("\n\n") if x.strip()]
        first = f"<p>{esc(paras[0])}</p>"
        rest = "".join(f"<p>{esc(x)}</p>" for x in paras[1:])
        more = (f'<div class="brief-more" id="brief-more" hidden>{rest}</div>'
                '<button class="linkbtn" id="brief-expand" type="button" '
                'aria-expanded="false">Read the full brief &darr;</button>'
                if rest else "")
        brief_html = (
            '<section class="brief" data-brief>'
            '<div class="brief-head">'
            '<span class="brief-mark" aria-hidden="true">&#9998;</span>'
            '<h2>Today&rsquo;s Brief</h2>'
            f'<span class="brief-date">{today.strftime("%A %d %B %Y")}</span>'
            '<button class="tcollapse" id="brief-collapse" type="button" '
            'aria-expanded="true" aria-label="Collapse brief">&#9650;</button>'
            '</div>'
            f'<div class="brief-body" id="brief-body">{first}{more}'
            f'<p class="brief-links">'
            f'<a href="/recap/{today.isoformat()}.html">Open as a page &rarr;</a>'
            '<a href="/newsletter/">Get it by email &rarr;</a></p>'
            '</div></section>')

    # The h1 exists for crawlers; the live site shows no heading above the
    # wire and the client wants that look kept, so it is visually hidden.
    home_body = (
        '<div class="sr-only">'
        f'<h1>{esc(cfg["site_name"])} - {esc(cfg.get("tagline", "financial news"))}</h1>'
        '<p>Every desk on one page, newest first. '
        'Headlines link straight to the publisher.</p>'
        '</div>'
        + '<section class="foryou" id="foryou" hidden></section>'
        + trending_section(cfg, wire)
        + brief_html
        + filter_bar(cfg, present)
        + '<p class="empty" id="f-empty" hidden>Nothing matches those filters.</p>'
        + f'<div class="grid">{"".join(cards)}</div>'
    )
    write(out / "index.html", shell(
        cfg,
        title=f"{cfg['site_name']} - {cfg.get('tagline', 'Global Financial News Feed')}",
        description=("Financial and world news from every major desk on one page: "
                     "US, UK, China, France, Switzerland and the Middle East."),
        canonical=f"{base}/", body=home_body, current="/",
        ticker=ticker_strip(mkt),
        extra_head=(f"<script>window.__TOPICS__={topic_json};</script>"
                    f'<script type="application/ld+json">{site_ld}</script>'),
        scripts=f'<script src="/assets/filter.js?v={BUILD_STAMP}" defer></script>',
    ))
    urls.append((f"{base}/", datetime.now(timezone.utc)))

    now = datetime.now(timezone.utc)
    if mkt and mkt.get("fx"):
        urls.append((forex_page(cfg, mkt, base, out), now))
    urls.append((books_page(cfg, mkt, base, out), now))
    urls.append((podcasts_page(cfg, mkt, base, out), now))
    urls.append((events_page(cfg, mkt, base, out), now))

    world_items = {}
    for it in items:
        slug = it.get("world_slug")
        if slug:
            world_items.setdefault(slug, []).append(it)
    for slug in world_items:
        world_items[slug].sort(key=lambda i: i["ts"], reverse=True)
    if world_items:
        urls.append((world_page(cfg, mkt, base, out, world_items), now))

    signup = cfg.get("newsletter_signup_url", "")
    if signup:
        form = (f'<form class="nl-form" method="post" action="{esc(signup)}" '
                'target="_blank">'
                '<label class="sr-only" for="nl-email">Email address</label>'
                '<input id="nl-email" name="email" type="email" required '
                'placeholder="you@example.com">'
                '<button class="nl-btn" type="submit">Subscribe free</button></form>')
    else:
        form = ('<form class="nl-form" data-nl-placeholder>'
                '<label class="sr-only" for="nl-email">Email address</label>'
                '<input id="nl-email" type="email" required '
                'placeholder="you@example.com">'
                '<button class="nl-btn" type="submit">Subscribe free</button></form>'
                '<p class="intro"><p>Sending starts once the list provider is '
                'connected - set <code>newsletter_signup_url</code> in '
                'config.json. Addresses entered now are kept in this browser '
                'only.</p></p>')
    urls.append((simple_page(
        cfg, mkt, base, out, path="/newsletter/", current="/newsletter/",
        title=f"The Morning Brief - {cfg['site_name']}",
        heading="The Morning Brief",
        description=("The trading day in one written paragraph, in your inbox "
                     "before the open. Free."),
        body_html=(
            '<div class="note"><p><strong>One paragraph. Every trading day. '
            'Before the open.</strong></p>'
            '<p>What actually moved, why the desks disagreed about it, and the '
            'one number to watch - written by a person, not scraped. The '
            'same brief that appears on the front page, delivered.</p></div>'
            + form +
            '<h2>What you get</h2>'
            '<p>The daily brief, the top consensus story across our 22 desks, '
            'and the next market-moving event from the '
            '<a href="/events/">economic calendar</a>. Nothing else. '
            'Unsubscribe any time.</p>')), now))

    contact_action = cfg.get("contact_form_url", "")
    contact_email = cfg.get("contact_email", "hello@newsnownext.org")
    form_attrs = (f'method="post" action="{esc(contact_action)}"'
                  if contact_action else 'data-contact-form')
    urls.append((simple_page(
        cfg, mkt, base, out, path="/contact/", current="/contact/",
        title=f"Contact - {cfg['site_name']}", heading="Contact",
        description="Suggest a source, report a problem, or talk to us about advertising.",
        body_html=(
            '<div class="contact-grid">'
            '<div class="ccard"><span class="ccard-ico">&#9993;</span>'
            '<h2>Say hello</h2><p>Questions, corrections, anything else.</p>'
            f'<a href="mailto:{esc(contact_email)}">{esc(contact_email)}</a></div>'
            '<div class="ccard"><span class="ccard-ico">&#128240;</span>'
            '<h2>Suggest a source</h2><p>Tell us the outlet and, if you have it, '
            'the RSS URL. We link out and never reproduce article text, so most '
            'desks are happy to be included.</p></div>'
            '<div class="ccard"><span class="ccard-ico">&#128188;</span>'
            '<h2>Advertising</h2><p>One banner slot and a daily newsletter. '
            'Finance audience, no tracking, direct deals only.</p></div>'
            '</div>'
            '<h2 class="contact-form-h">Write to us</h2>'
            f'<form class="cform" {form_attrs}>'
            '<div class="cform-row">'
            '<label>Name<input name="name" type="text" required '
            'autocomplete="name"></label>'
            '<label>Email<input name="email" type="email" required '
            'autocomplete="email"></label></div>'
            '<label>Topic<select name="topic">'
            '<option>General</option><option>Suggest a source</option>'
            '<option>Correction</option><option>Advertising</option>'
            '</select></label>'
            '<label>Message<textarea name="message" rows="5" required>'
            '</textarea></label>'
            '<button class="nl-btn" type="submit">Send message</button>'
            + ('' if contact_action else
               '<p class="intro"><p>Sending opens your email app until a form '
               'endpoint is connected (set <code>contact_form_url</code> in '
               'config.json).</p></p>')
            + '</form>')), now))

    prefs_meta = json.dumps({
        "regions": [{"id": r["id"], "title": r["title"]} for r in cfg["regions"]],
        "sources": [{"id": src["id"], "label": src["label"], "region": r["title"]}
                    for r in cfg["regions"] for src in r["sources"]],
    })
    urls.append((simple_page(
        cfg, mkt, base, out, path="/preferences/", current="/preferences/",
        title=f"News preferences - {cfg['site_name']}", heading="Preferences",
        description="Choose which regions and sources appear on your feed.",
        body_html=(
            '<p>These settings live in this browser only. Nothing is uploaded and '
            'there is no account.</p>'
            f'<script>window.__PREFS_META__={prefs_meta};</script>'
            '<div id="prefs-app" data-prefs></div>'
            '<noscript><p class="empty">Preferences need JavaScript. The feed itself '
            'works without it.</p></noscript>')), now))

    urls.append((simple_page(
        cfg, mkt, base, out, path="/read-later/", current="/read-later/",
        title=f"Read later - {cfg['site_name']}", heading="Read Later",
        description="Headlines you saved to come back to.", index=False,
        body_html=(
            '<div id="later-app" data-later></div>'
            '<noscript><p class="empty">Saved headlines need JavaScript.</p></noscript>')), now))

    urls.append((simple_page(
        cfg, mkt, base, out, path="/portfolio/", current="/portfolio/",
        title=f"Portfolio - {cfg['site_name']}", heading="Portfolio",
        description="Track your holdings against the wire.", index=False,
        body_html=(
            '<div class="note"><p><strong>Coming soon.</strong> Portfolio tracking '
            'needs an account, which needs a backend. It is not part of this build.</p>'
            '<p>Everything else on the site works without signing in, and always '
            'will.</p></div>')), now))

    # ── Topic pages ──────────────────────────────────────────────────
    for topic in cfg["topics"]:
        hits = [i for i in wire if matches(i, topic)][: cfg["max_per_topic"]]
        note_path = HERE / "notes" / f"{topic['slug']}.txt"
        note = note_path.read_text(encoding="utf-8").strip() if note_path.exists() else ""
        note_html = ""
        if note:
            paras = "".join(f"<p>{esc(p.strip())}</p>"
                            for p in note.split("\n\n") if p.strip())
            note_html = f'<div class="intro">{paras}</div>'

        canonical = f"{base}/topics/{topic['slug']}.html"
        write(out / "topics" / f"{topic['slug']}.html", shell(
            cfg,
            title=f"{topic['title']} news - {cfg['site_name']}",
            description=topic["description"], canonical=canonical,
            body=('<div class="prose"><div class="page-head">'
                  f'<h1>{esc(topic["title"])}</h1>'
                  f'<p class="standfirst">{esc(topic["description"])}</p></div>'
                  f'{note_html}{wire_list(hits)}</div>'),
            ticker=ticker_strip(mkt), current="/topics/", noindex=not note,
        ))
        if note:
            urls.append((canonical, datetime.now(timezone.utc)))

    cards_html = "".join(
        f'<li><h2><a href="/topics/{esc(t["slug"])}.html">{esc(t["title"])}</a></h2>'
        f'<p>{esc(t["description"])}</p></li>'
        for t in cfg["topics"]
    )
    write(out / "topics" / "index.html", shell(
        cfg, title=f"Topics - {cfg['site_name']}",
        description="Financial news by topic: oil, crypto, rates, equities, China and tech.",
        canonical=f"{base}/topics/", current="/topics/", ticker=ticker_strip(mkt),
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
        cfg, title=f"Market recap, {pretty} - {cfg['site_name']}",
        description=(synopsis[:155] if synopsis
                     else f"Every headline that crossed the wire on {pretty}."),
        canonical=canonical, ticker=ticker_strip(mkt), current="/recap/", noindex=not synopsis,
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
        cfg, title=f"Daily market recaps - {cfg['site_name']}",
        description="An archive of daily financial market recaps.",
        canonical=f"{base}/recap/", ticker=ticker_strip(mkt), current="/recap/",
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
           f"<title>{esc(cfg['site_name'])} - daily market recap</title>",
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

    write(out / "404.html", shell(
        cfg, title=f"Page not found - {cfg['site_name']}",
        description="That page does not exist.",
        canonical=f"{base}/404.html", noindex=True, ticker=ticker_strip(mkt),
        body=('<div class="prose"><div class="page-head">'
              '<h1>Page not found</h1>'
              '<p class="standfirst">That link has moved or never existed.</p></div>'
              '<div class="note"><p>Try the <a href="/">live feed</a>, '
              '<a href="/topics/">topics</a>, or the '
              '<a href="/recap/">daily recap</a>.</p></div></div>'),
    ))

    write(out / "_headers",
          "/events/calendar.ics\n  Content-Type: text/calendar; charset=utf-8\n"
          "/manifest.webmanifest\n  Content-Type: application/manifest+json\n"
          "/sw.js\n  Cache-Control: no-cache\n")

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
        cache_file = cache_path(cfg)
        if not cache_file.exists():
            sys.exit("No cache yet - run once without --no-fetch.")
        raw = json.loads(cache_file.read_text(encoding="utf-8"))
        print(f"Using cached pull: {len(raw)} items")
    else:
        print("Fetching feeds…")
        raw, failed = collect(cfg)
        if not raw:
            sys.exit("Every feed failed. Nothing to build.")
        cache_file = cache_path(cfg)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(raw), encoding="utf-8")
        if failed:
            print(f"\nNote: {len(failed)} source(s) unavailable: {', '.join(failed)}")

    items = within(raw, cfg["window_hours"])
    print(f"\n{len(items)} headlines in the last {cfg['window_hours']}h")

    print("Market data…")
    mkt = market.collect(offline=args.no_fetch)

    print("Building…")
    count, shown, (has_syn, day) = build(cfg, items, out, mkt)

    print(f"\nDone. {shown} headlines on the home page, "
          f"{count} indexable URL(s) in {out}")
    if not has_syn:
        print(f"Today's recap is noindex - write synopsis/{day}.txt "
              f"(200-300 words) and rerun to publish it.")
    missing = [t["slug"] for t in cfg["topics"]
               if not (HERE / "notes" / f"{t['slug']}.txt").exists()]
    if missing:
        print(f"Topic pages still noindex (no intro written): {', '.join(missing)}")


if __name__ == "__main__":
    main()
