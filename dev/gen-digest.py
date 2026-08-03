#!/usr/bin/env python3
"""
Render today's Morning Brief as a ready-to-send email.

    python3 dev/gen-digest.py            # writes generator/out/digest-YYYY-MM-DD.html

Pulls the three pieces the newsletter promises - the written brief, the top
consensus story across the desks, and the next calendar event - and lays them
out with inline styles that survive email clients. Paste the HTML into
Buttondown/Resend/Mailchimp, or wire it into their API later; this script is
deliberately sender-agnostic.

Fails loudly if today's synopsis has not been written: the email IS the brief,
and sending a hollow email is worse than sending none.
"""

import html
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "generator"
sys.path.insert(0, str(GEN))

from zoneinfo import ZoneInfo  # noqa: E402


def esc(s):
    return html.escape(str(s), quote=True)


def main():
    cfg = json.loads((GEN / "config.json").read_text(encoding="utf-8"))
    base = cfg["base_url"].rstrip("/")
    today = datetime.now(timezone.utc).date()

    syn_path = GEN / "synopsis" / f"{today.isoformat()}.txt"
    if not syn_path.exists():
        sys.exit(f"No brief written for {today} - create generator/synopsis/"
                 f"{today.isoformat()}.txt first. The email IS the brief.")
    paras = [p.strip() for p in
             syn_path.read_text(encoding="utf-8").split("\n\n") if p.strip()]

    # Top consensus story from the trending history the site build maintains.
    top_story = None
    hist_path = GEN / ".cache" / "trending-history.json"
    cache_path = GEN / ".cache" / "items-site.json"
    if hist_path.exists() and cache_path.exists():
        items = json.loads(cache_path.read_text(encoding="utf-8"))
        hist = json.loads(hist_path.read_text(encoding="utf-8"))
        best = max(hist.values(), key=lambda v: v.get("desks", 0), default=None)
        if best and best.get("desks", 0) >= 2:
            # find a matching recent headline for a link
            from build import STOP  # same tokeniser as the site build
            for it in items:
                toks = {w for w in re.findall(r"[a-z0-9]+", it["title"].lower())
                        if len(w) > 2 and w not in STOP}
                key = "-".join(sorted(toks)[:6])
                if key in hist and hist[key]["desks"] == best["desks"]:
                    top_story = {"title": it["title"], "link": it["link"],
                                 "desks": best["desks"]}
                    break

    # Next event from the calendar file.
    ev_data = json.loads((GEN / "data" / "events.json").read_text(encoding="utf-8"))
    tz = ZoneInfo(ev_data.get("timezone", "America/New_York"))
    nxt = None
    for e in sorted(ev_data["events"], key=lambda x: (x["date"], x["time"])):
        local = datetime.strptime(f'{e["date"]} {e["time"]}',
                                  "%Y-%m-%d %H:%M").replace(tzinfo=tz)
        if local.date() >= today:
            nxt = (local, e)
            break

    body_paras = "".join(
        f'<p style="margin:0 0 14px;font-size:15px;line-height:1.65;'
        f'color:#344256">{esc(p)}</p>' for p in paras)

    consensus_html = ""
    if top_story:
        consensus_html = (
            '<h2 style="font-size:13px;letter-spacing:.05em;text-transform:uppercase;'
            'color:#65758b;margin:26px 0 8px">Across the desks</h2>'
            f'<p style="margin:0;font-size:15px;line-height:1.5">'
            f'<a href="{esc(top_story["link"])}" style="color:#2463eb;'
            f'text-decoration:none;font-weight:600">{esc(top_story["title"])}</a>'
            f'<br><span style="font-size:12.5px;color:#9a3412">'
            f'{top_story["desks"]} desks are on this story</span></p>')

    event_html = ""
    if nxt:
        local, e = nxt
        hour = local.hour % 12 or 12
        when = (f'{local.strftime("%A %d %B")}, {hour}:{local.strftime("%M")} '
                f'{"AM" if local.hour < 12 else "PM"} ET')
        event_html = (
            '<h2 style="font-size:13px;letter-spacing:.05em;text-transform:uppercase;'
            'color:#65758b;margin:26px 0 8px">Next on the calendar</h2>'
            f'<p style="margin:0;font-size:15px"><strong>{esc(e["name"])}</strong>'
            f'<br><span style="font-size:13px;color:#65758b">{esc(when)} &middot; '
            f'{esc(e["note"])}</span></p>')

    doc = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#f1f5f9">
<div style="max-width:600px;margin:0 auto;padding:28px 20px;
     font-family:Inter,-apple-system,'Segoe UI',sans-serif">
  <div style="font-weight:900;font-size:22px;line-height:.95;margin-bottom:18px">
    <span style="color:#f97316">NEWS</span><span style="color:#10b981">NOW</span><span style="color:#ef4444">NEXT</span>
  </div>
  <div style="background:#fff;border:1px solid #e1e7ef;border-radius:10px;padding:24px">
    <p style="margin:0 0 4px;font-size:12px;font-weight:700;letter-spacing:.06em;
       text-transform:uppercase;color:#65758b">The Morning Brief</p>
    <h1 style="margin:0 0 16px;font-size:20px;color:#1f2937">
      {esc(today.strftime("%A %d %B %Y"))}</h1>
    {body_paras}
    {consensus_html}
    {event_html}
    <p style="margin:28px 0 0;font-size:13px">
      <a href="{esc(base)}/" style="color:#2463eb">Open the live wire &rarr;</a></p>
  </div>
  <p style="font-size:11.5px;color:#94a3b8;margin-top:14px;text-align:center">
    Headlines link to their publishers. You are receiving this because you
    subscribed at {esc(base)}/newsletter/ &middot; Unsubscribe: {{{{unsubscribe_url}}}}</p>
</div>
</body></html>"""

    out = GEN / "out"
    out.mkdir(exist_ok=True)
    dest = out / f"digest-{today.isoformat()}.html"
    dest.write_text(doc, encoding="utf-8")
    print(f"Wrote {dest.relative_to(ROOT)}")
    print(f"  brief: {len(paras)} paragraphs"
          + (f" · consensus: {top_story['desks']} desks" if top_story else "")
          + (f" · next event: {nxt[1]['name']}" if nxt else ""))


if __name__ == "__main__":
    main()
