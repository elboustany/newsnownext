#!/usr/bin/env python3
"""
NewsNowNext static page builder.

Turns the live feeds into pages a search engine can actually index:
topic pages, a dated daily recap, an index, a sitemap and an RSS feed.

Standard library only. Python 3.9+.

    python3 build.py                 # build everything
    python3 build.py --no-fetch      # rebuild pages from the last cached pull
    python3 build.py --config other.json

A recap page is only marked indexable once a human synopsis exists at
synopsis/YYYY-MM-DD.txt. Without one the page is generated but carries
noindex, because a page of other people's headlines with no original
writing on it is the exact thing search engines demote.
"""

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime, format_datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
UA = "NewsNowNextBuilder/1.0 (+https://www.newsnownext.org)"
CACHE = HERE / ".cache" / "items.json"

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "dc": "http://purl.org/dc/elements/1.1/",
}


# ── Fetch and parse ──────────────────────────────────────────────────────

def fetch(url, timeout=20):
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


def clean_title(title, label):
    t = re.sub(r"\s+", " ", title).strip()
    # Google News suffixes every headline with " - Publisher".
    head = label.split()[0]
    t = re.sub(rf"\s+[-–—]\s+{re.escape(head)}[^-–—]*$", "", t, flags=re.I)
    return t.strip()


def parse_feed(raw, feed):
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        raise ValueError(f"{feed['label']}: malformed XML ({e})")

    out = []
    nodes = root.iter("item")
    entries = list(root.iter(f"{{{NS['atom']}}}entry"))

    for n in list(nodes) + entries:
        title = text_of(n.find("title")) or text_of(n.find(f"{{{NS['atom']}}}title"))
        if not title:
            continue

        link_node = n.find("link")
        link = text_of(link_node)
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
            "title": clean_title(title, feed["label"]),
            "link": link,
            "ts": when.isoformat(),
            "source": feed["label"],
            "source_id": feed["id"],
            "via": feed.get("via"),
        })
    return out


def collect(cfg):
    items, failures = [], []
    for feed in cfg["feeds"]:
        try:
            items.extend(parse_feed(fetch(feed["url"]), feed))
            print(f"  ok    {feed['label']}")
        except Exception as e:                      # noqa: BLE001 - report and continue
            failures.append(feed["label"])
            print(f"  FAIL  {feed['label']}: {e}", file=sys.stderr)
    return items, failures


def dedupe(items, window_hours):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    seen = {}
    for it in items:
        when = parse_date(it["ts"])
        if not when or when < cutoff:
            continue
        key = re.sub(r"[^a-z0-9]+", "", it["title"].lower())[:60]
        if not key:
            continue
        if key not in seen or when > parse_date(seen[key]["ts"]):
            seen[key] = it
    return sorted(seen.values(), key=lambda i: i["ts"], reverse=True)


# ── Topic matching ───────────────────────────────────────────────────────

def matches(item, topic):
    hay = item["title"].lower()
    for kw in topic["keywords"]:
        if re.search(rf"(?<![a-z0-9]){re.escape(kw.lower())}(?![a-z0-9])", hay):
            return True
    return False


# ── HTML ─────────────────────────────────────────────────────────────────

CSS = """
:root{--paper:#E9EBE4;--raised:#F3F5EE;--ink:#16191A;--soft:#5C6259;--faint:#8B9086;
--rule:#C9CDC0;--signal:#B23A2E;
--display:"Helvetica Neue Condensed","Arial Narrow","Roboto Condensed",Helvetica,Arial,sans-serif;
--body:ui-sans-serif,system-ui,"Segoe UI",Helvetica,Arial,sans-serif;
--data:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
@media(prefers-color-scheme:dark){:root{--paper:#14171A;--raised:#1B1F22;--ink:#E7E9E3;
--soft:#9AA096;--faint:#6B7168;--rule:#2C3136;--signal:#D9614F}}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--body);font-size:16px;line-height:1.55}
.wrap{max-width:760px;margin:0 auto;padding:0 24px 72px}
header.top{display:flex;justify-content:space-between;align-items:baseline;gap:16px;
padding:32px 0 14px;border-bottom:2px solid var(--ink);flex-wrap:wrap}
.brand{font-family:var(--display);font-size:24px;font-weight:700;letter-spacing:.02em;
text-decoration:none;color:var(--ink)}
.brand em{font-style:normal;color:var(--signal)}
nav.topics{display:flex;flex-wrap:wrap;gap:14px;padding:12px 0;border-bottom:1px solid var(--rule);
font-family:var(--data);font-size:11px;letter-spacing:.1em;text-transform:uppercase}
nav.topics a{color:var(--soft);text-decoration:none}
nav.topics a:hover,nav.topics a[aria-current]{color:var(--signal)}
h1{font-family:var(--display);font-size:38px;line-height:1.1;letter-spacing:-.01em;margin:34px 0 10px}
.standfirst{font-size:18px;color:var(--soft);margin:0 0 8px}
.synopsis{background:var(--raised);border-left:3px solid var(--signal);padding:18px 20px;margin:26px 0}
.synopsis p{margin:0 0 12px}.synopsis p:last-child{margin:0}
.daymark{font-family:var(--data);font-size:11px;letter-spacing:.14em;text-transform:uppercase;
color:var(--signal);margin:34px 0 6px;padding-bottom:6px;border-bottom:1px solid var(--rule)}
ol.wire{list-style:none;margin:0;padding:0}
ol.wire li{display:grid;grid-template-columns:66px 1fr;padding:11px 0;border-bottom:1px solid var(--rule)}
ol.wire time{font-family:var(--data);font-size:12px;color:var(--faint);padding-top:4px;
border-right:1px solid var(--rule);padding-right:14px;text-align:right}
ol.wire .b{padding-left:16px;min-width:0}
ol.wire a{font-family:var(--display);font-size:19px;font-weight:600;line-height:1.28;
color:var(--ink);text-decoration:none;display:block}
ol.wire a:hover{text-decoration:underline;text-underline-offset:3px}
ol.wire .src{margin-top:4px;font-family:var(--data);font-size:10px;letter-spacing:.12em;
text-transform:uppercase;color:var(--faint)}
footer.bot{margin-top:44px;padding-top:14px;border-top:1px solid var(--rule);
font-family:var(--data);font-size:11px;letter-spacing:.08em;color:var(--faint)}
footer.bot a{color:var(--soft)}
.cards{display:grid;gap:2px;margin:26px 0 0;padding:0;list-style:none}
.cards li{border-bottom:1px solid var(--rule);padding:16px 0}
.cards h2{font-family:var(--display);font-size:22px;margin:0 0 4px}
.cards h2 a{color:var(--ink);text-decoration:none}
.cards h2 a:hover{color:var(--signal)}
.cards p{margin:0;color:var(--soft);font-size:15px}
@media(max-width:640px){h1{font-size:29px}ol.wire li{grid-template-columns:52px 1fr}
ol.wire a{font-size:17px}}
.wirefilter{margin:26px 0 0;padding:14px 0 0;border-top:1px solid var(--rule)}
.wfrow{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:8px}
.wfsr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
#wf-q{flex:1 1 220px;font-family:var(--body);font-size:15px;color:var(--ink);
background:var(--raised);border:1px solid var(--rule);border-radius:2px;padding:8px 11px}
#wf-q:focus{outline:none;border-color:var(--signal);box-shadow:0 0 0 1px var(--signal)}
.wfchip,.wforder,.wfall{font-family:var(--data);font-size:10px;letter-spacing:.12em;
text-transform:uppercase;padding:5px 10px;border:1px solid var(--rule);background:transparent;
color:var(--soft);cursor:pointer;border-radius:2px}
.wfchip:hover,.wforder:hover,.wfall:hover{border-color:var(--ink);color:var(--ink)}
.wfchip[aria-pressed=false]{opacity:.45;text-decoration:line-through}
.wfcount{font-family:var(--data);font-size:10px;letter-spacing:.1em;text-transform:uppercase;
color:var(--faint);margin:0}
ol.wire li[hidden],p.daymark[hidden]{display:none}
ol.wire mark{background:rgba(178,58,46,.22);color:inherit;border-radius:1px;padding:0 1px}
"""

# Client-side filtering for the wire lists. Kept out of the page HTML so pages
# stay diffable, and gated on `data-wirefilter` so it is a no-op where the bar
# was not rendered. The list is server-rendered either way — this only hides
# rows that are already in the document, so nothing here affects what a crawler
# sees.
FILTER_JS = r"""
(function () {
  var bar = document.querySelector('[data-wirefilter]');
  if (!bar) return;
  bar.hidden = false;

  var q      = bar.querySelector('#wf-q');
  var order  = bar.querySelector('.wforder');
  var allBtn = bar.querySelector('.wfall');
  var count  = bar.querySelector('.wfcount');
  var chips  = [].slice.call(bar.querySelectorAll('.wfchip'));
  var rows   = [].slice.call(document.querySelectorAll('ol.wire li'));
  var lists  = [].slice.call(document.querySelectorAll('[data-day-list]'));
  var off    = Object.create(null);
  // Whatever follows the last day block (the footer). Day blocks are re-inserted
  // before it so reordering never moves them out of the article.
  var anchor = lists.length ? lists[lists.length - 1].nextSibling : null;

  rows.forEach(function (li) {
    var a = li.querySelector('a');
    li._text = (a.textContent + ' ' + li.getAttribute('data-src')).toLowerCase();
    li._raw = a.textContent;          // headline is plain text, no markup
    li._a = a;
  });

  function escHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // Rebuild from the raw headline each time so highlights never nest, and
  // escape every slice so a headline containing < or & cannot inject markup.
  function markUp(text, re) {
    if (!re) return escHtml(text);
    var out = '', last = 0, m;
    re.lastIndex = 0;
    while ((m = re.exec(text)) !== null) {
      out += escHtml(text.slice(last, m.index)) + '<mark>' + escHtml(m[0]) + '</mark>';
      last = m.index + m[0].length;
      if (m.index === re.lastIndex) re.lastIndex++;   // guard zero-length match
    }
    return out + escHtml(text.slice(last));
  }

  function terms() {
    return (q.value.toLowerCase().match(/"[^"]+"|\S+/g) || [])
      .map(function (t) { return t.replace(/^"|"$/g, '').trim(); })
      .filter(Boolean);
  }

  function esc(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

  function apply() {
    var t = terms(), shown = 0;
    var re = t.length ? new RegExp('(' + t.map(esc).join('|') + ')', 'ig') : null;

    rows.forEach(function (li) {
      var ok = !off[li.getAttribute('data-src')] &&
               t.every(function (x) { return li._text.indexOf(x) > -1; });
      li.hidden = !ok;
      if (ok) shown++;
      li._a.innerHTML = markUp(li._raw, ok ? re : null);
    });

    // A day heading with nothing left under it is noise.
    lists.forEach(function (ol) {
      var any = [].slice.call(ol.children).some(function (li) { return !li.hidden; });
      ol.hidden = !any;
      var head = ol.previousElementSibling;
      if (head && head.hasAttribute('data-day')) head.hidden = !any;
    });

    count.textContent = shown === rows.length
      ? rows.length + ' headlines'
      : shown + ' of ' + rows.length + ' headlines';
    allBtn.hidden = shown === rows.length;
  }

  function reorder() {
    var desc = order.getAttribute('data-order') === 'desc';
    desc = !desc;
    order.setAttribute('data-order', desc ? 'desc' : 'asc');
    order.textContent = desc ? 'Newest first' : 'Oldest first';

    // Rows within each day…
    lists.forEach(function (ol) {
      [].slice.call(ol.children)
        .sort(function (a, b) {
          var x = +a.getAttribute('data-ts'), y = +b.getAttribute('data-ts');
          return desc ? y - x : x - y;
        })
        .forEach(function (li) { ol.appendChild(li); });
    });

    // …and the day blocks themselves, or "oldest first" still shows the most
    // recent day at the top and reads as broken. Re-insert before `anchor`
    // (the footer) rather than appending, which would move them past it.
    if (lists.length < 2) return;
    var parent = lists[0].parentNode;
    var blocks = lists.map(function (ol) {
      var first = ol.querySelector('li');
      return {
        head: ol.previousElementSibling,
        list: ol,
        ts: first ? +first.getAttribute('data-ts') : 0
      };
    });
    blocks.sort(function (a, b) { return desc ? b.ts - a.ts : a.ts - b.ts; });
    blocks.forEach(function (b) {
      if (b.head && b.head.hasAttribute('data-day')) parent.insertBefore(b.head, anchor);
      parent.insertBefore(b.list, anchor);
    });
  }

  q.addEventListener('input', apply);
  q.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { q.value = ''; apply(); }
  });
  order.addEventListener('click', reorder);
  chips.forEach(function (c) {
    c.addEventListener('click', function () {
      var s = c.getAttribute('data-src');
      off[s] = !off[s];
      c.setAttribute('aria-pressed', String(!off[s]));
      apply();
    });
  });
  allBtn.addEventListener('click', function () {
    q.value = '';
    off = Object.create(null);
    chips.forEach(function (c) { c.setAttribute('aria-pressed', 'true'); });
    apply();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && e.target !== q) { e.preventDefault(); q.focus(); }
  });

  apply();
})();
"""

def esc(s):
    return html.escape(s, quote=True)


def page(cfg, *, title, description, canonical, body, noindex=False,
         topic_slug=None, extra_head=""):
    def nav_link(t):
        current = ' aria-current="page"' if t["slug"] == topic_slug else ""
        return '<a href="/topics/{}.html"{}>{}</a>'.format(
            t["slug"], current, esc(t["title"]))

    nav = "".join(nav_link(t) for t in cfg["topics"])
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
<link rel="stylesheet" href="/assets/site.css">
{extra_head}
</head>
<body>
<div class="wrap">
<header class="top">
  <a class="brand" href="/">NEWS<em>NOW</em>NEXT</a>
  <a href="/" style="font-family:var(--data);font-size:11px;letter-spacing:.12em;
     text-transform:uppercase;color:var(--soft);text-decoration:none">Live feed &rarr;</a>
</header>
<nav class="topics">{nav}<a href="/recap/">Daily recap</a></nav>
{body}
<footer class="bot">
  Headlines link out to their publishers. {esc(cfg['site_name'])} does not host article text.
  &nbsp;·&nbsp; <a href="/feed.xml">RSS</a>
</footer>
</div>
<script src="/assets/filter.js" defer></script>
</body>
</html>
"""


def filter_bar(items):
    """Search box and source toggles for a wire list.

    Progressive enhancement: it is inert without JavaScript and the full list is
    already in the HTML, so a crawler sees every headline either way.
    """
    if not items:
        return ""
    sources = sorted({i["source"] for i in items})
    chips = "".join(
        f'<button class="wfchip" type="button" aria-pressed="true" '
        f'data-src="{esc(s)}">{esc(s)}</button>'
        for s in sources
    )
    return (
        '<div class="wirefilter" data-wirefilter hidden>'
        '<div class="wfrow">'
        '<label class="wfsr" for="wf-q">Filter these headlines</label>'
        '<input id="wf-q" type="search" autocomplete="off" placeholder="Filter these headlines…">'
        '<button class="wforder" type="button" data-order="desc">Newest first</button>'
        '</div>'
        f'<div class="wfrow wfchips">{chips}'
        '<button class="wfall" type="button" hidden>Show all</button></div>'
        '<p class="wfcount" role="status"></p>'
        '</div>'
    )


def wire_list(items, tz_label="UTC"):
    out = []
    current_day = None
    for it in items:
        when = parse_date(it["ts"])
        day = when.strftime("%A %d %B %Y")
        if day != current_day:
            if current_day is not None:
                out.append("</ol>")
            out.append(f'<p class="daymark" data-day>{esc(day)}</p>'
                       f'<ol class="wire" data-day-list>')
            current_day = day
        via = f' <span>via {esc(it["via"])}</span>' if it.get("via") else ""
        out.append(
            f'<li data-src="{esc(it["source"])}" data-ts="{when.timestamp():.0f}">'
            f'<time datetime="{when.isoformat()}">{when.strftime("%H:%M")}</time>'
            f'<div class="b"><a href="{esc(it["link"])}" rel="nofollow noopener" target="_blank">'
            f'{esc(it["title"])}</a>'
            f'<div class="src">{esc(it["source"])}{via}</div></div></li>'
        )
    if current_day is not None:
        out.append("</ol>")
    return "\n".join(out) or "<p>Nothing on the wire in this window.</p>"


# ── Build ────────────────────────────────────────────────────────────────

def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  wrote {path}")


def build(cfg, items, out: Path):
    base = cfg["base_url"].rstrip("/")
    urls = []

    write(out / "assets" / "site.css", CSS.strip())
    write(out / "assets" / "filter.js", FILTER_JS.strip())

    # Topic pages
    for topic in cfg["topics"]:
        hits = [i for i in items if matches(i, topic)][: cfg["max_per_topic"]]
        note_path = HERE / "notes" / f"{topic['slug']}.txt"
        note = note_path.read_text(encoding="utf-8").strip() if note_path.exists() else ""
        note_html = ""
        if note:
            paras = "".join(f"<p>{esc(p.strip())}</p>" for p in note.split("\n\n") if p.strip())
            note_html = f'<div class="synopsis">{paras}</div>'

        canonical = f"{base}/topics/{topic['slug']}.html"
        body = (
            f"<h1>{esc(topic['title'])}</h1>"
            f'<p class="standfirst">{esc(topic["description"])}</p>'
            f"{note_html}{filter_bar(hits)}{wire_list(hits)}"
        )
        write(
            out / "topics" / f"{topic['slug']}.html",
            page(cfg, title=f"{topic['title']} news — {cfg['site_name']}",
                 description=topic["description"], canonical=canonical,
                 body=body, topic_slug=topic["slug"],
                 noindex=not note),        # thin until someone writes the intro
        )
        if note:
            urls.append((canonical, datetime.now(timezone.utc)))

    # Topic index
    cards = "".join(
        f'<li><h2><a href="/topics/{t["slug"]}.html">{esc(t["title"])}</a></h2>'
        f'<p>{esc(t["description"])}</p></li>'
        for t in cfg["topics"]
    )
    write(out / "topics" / "index.html",
          page(cfg, title=f"Topics — {cfg['site_name']}",
               description="Financial news by topic: oil, crypto, rates, equities, China and tech.",
               canonical=f"{base}/topics/",
               body=f"<h1>Topics</h1><ul class=\"cards\">{cards}</ul>"))
    urls.append((f"{base}/topics/", datetime.now(timezone.utc)))

    # Daily recap
    today = datetime.now(timezone.utc).date()
    syn_path = HERE / "synopsis" / f"{today.isoformat()}.txt"
    synopsis = syn_path.read_text(encoding="utf-8").strip() if syn_path.exists() else ""
    day_items = [i for i in items if parse_date(i["ts"]).date() == today]

    syn_html = ""
    if synopsis:
        paras = "".join(f"<p>{esc(p.strip())}</p>" for p in synopsis.split("\n\n") if p.strip())
        syn_html = f'<div class="synopsis">{paras}</div>'

    pretty = today.strftime("%d %B %Y")
    canonical = f"{base}/recap/{today.isoformat()}.html"
    ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": f"Market recap, {pretty}",
        "datePublished": datetime.now(timezone.utc).isoformat(),
        "publisher": {"@type": "Organization", "name": cfg["site_name"]},
        "url": canonical,
    })
    recap_body = (
        f"<h1>Market recap, {esc(pretty)}</h1>"
        f'<p class="standfirst">What crossed the wire today, in order.</p>'
        f"{syn_html}{filter_bar(day_items)}{wire_list(day_items)}"
    )
    recap_html = page(
        cfg, title=f"Market recap, {pretty} — {cfg['site_name']}",
        description=(synopsis[:155] if synopsis
                     else f"Every financial headline that crossed the wire on {pretty}."),
        canonical=canonical, body=recap_body, noindex=not synopsis,
        extra_head=f'<script type="application/ld+json">{ld}</script>',
    )
    write(out / "recap" / f"{today.isoformat()}.html", recap_html)
    if synopsis:
        urls.append((canonical, datetime.now(timezone.utc)))

    # Recap archive index
    archive = sorted(
        (p for p in (out / "recap").glob("*.html") if p.stem != "index"),
        reverse=True,
    )
    links = "".join(
        f'<li><h2><a href="/recap/{p.name}">'
        f'{esc(datetime.fromisoformat(p.stem).strftime("%d %B %Y"))}</a></h2></li>'
        for p in archive if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem)
    )
    write(out / "recap" / "index.html",
          page(cfg, title=f"Daily market recaps — {cfg['site_name']}",
               description="An archive of daily financial market recaps.",
               canonical=f"{base}/recap/",
               body=f"<h1>Daily recaps</h1><ul class=\"cards\">{links}</ul>"))
    urls.append((f"{base}/recap/", datetime.now(timezone.utc)))

    # Sitemap
    sm = ["<?xml version='1.0' encoding='UTF-8'?>",
          "<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>"]
    for loc, when in urls:
        sm.append(f"<url><loc>{esc(loc)}</loc>"
                  f"<lastmod>{when.date().isoformat()}</lastmod></url>")
    sm.append("</urlset>")
    write(out / "sitemap.xml", "\n".join(sm))

    # Own RSS feed of recaps
    now = datetime.now(timezone.utc)
    rss = ["<?xml version='1.0' encoding='UTF-8'?>", "<rss version='2.0'><channel>",
           f"<title>{esc(cfg['site_name'])} — daily market recap</title>",
           f"<link>{esc(base)}/recap/</link>",
           "<description>A short written summary of each trading day.</description>",
           f"<lastBuildDate>{format_datetime(now)}</lastBuildDate>"]
    for p in archive[:30]:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem):
            continue
        d = datetime.fromisoformat(p.stem).replace(tzinfo=timezone.utc)
        rss.append(f"<item><title>Market recap, {d.strftime('%d %B %Y')}</title>"
                   f"<link>{esc(base)}/recap/{p.name}</link>"
                   f"<guid>{esc(base)}/recap/{p.name}</guid>"
                   f"<pubDate>{format_datetime(d)}</pubDate></item>")
    rss.append("</channel></rss>")
    write(out / "feed.xml", "\n".join(rss))

    write(out / "robots.txt", f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")

    return len(urls), (bool(synopsis), today.isoformat())


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
        items = json.loads(CACHE.read_text(encoding="utf-8"))
        print(f"Using cached pull: {len(items)} items")
    else:
        print("Fetching feeds…")
        raw, failed = collect(cfg)
        if not raw:
            sys.exit("Every feed failed. Nothing to build.")
        items = raw
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(items), encoding="utf-8")
        if failed:
            print(f"Note: {len(failed)} feed(s) unavailable: {', '.join(failed)}")

    items = dedupe(items, cfg["window_hours"])
    print(f"{len(items)} unique headlines in the last {cfg['window_hours']}h")

    print("Building…")
    count, (has_syn, day) = build(cfg, items, out)

    print(f"\nDone. {count} indexable URL(s) in {out}")
    if not has_syn:
        print(f"Today's recap is noindex — write generator/synopsis/{day}.txt "
              f"(200–300 words) and rerun to publish it.")
    missing = [t["slug"] for t in cfg["topics"]
               if not (HERE / "notes" / f"{t['slug']}.txt").exists()]
    if missing:
        print(f"Topic pages still noindex (no intro written): {', '.join(missing)}")
        print("Add generator/notes/<slug>.txt with 100–200 words to publish each one.")


if __name__ == "__main__":
    main()
