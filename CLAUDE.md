# NewsNowNext growth package

Organic-growth tooling for **newsnownext.org**, a client site (a friend of the
owner). Three independent deliverables, no shared build system, no dependencies.

```
extension/    Chrome MV3 new-tab extension  — acquisition + retention
generator/    Python static site builder    — indexable content
launch/       Copy for every launch channel — distribution
dev/          Local preview server + sync checker (never shipped)
dist/         Store upload zips (generated)
```

## Why this exists

newsnownext.org is client-rendered, so crawlers see an empty shell, and a page of
other people's headlines is the thin-content pattern search engines demote. The
generator produces pages the site actually owns; the extension is the
distribution channel that doesn't depend on ranking at all.

## Commands

```bash
python3 dev/devserver.py                     # preview at http://localhost:8787
python3 dev/check-sync.py                    # feeds/topics must match across halves
./pack-extension.sh                          # build dist/ zip for the store

cd generator
python3 build.py                             # fetch live feeds, build ./site
python3 build.py --no-fetch                  # rebuild from cache, no network
python3 build.py --config config.test.json   # offline self-test on fixtures
```

Run the offline self-test after any change to `build.py`. It uses local fixtures
(including a deliberately malformed feed), writes to `site-test/`, and must exit
0 with `oil` indexable and `equities` noindex — that asserts the thin-content
guard still works.

`dev/devserver.py` runs the extension as an ordinary web page by shimming
`chrome.storage` onto localStorage and proxying the feeds past CORS. Nothing in
`extension/` knows it exists, so what you see is the shipping code. It also
serves the generated site at `/site/` and `/assets/`. Use it to iterate on UI
without reloading an unpacked extension every time — but verify anything
storage- or permission-related in real Chrome before shipping.

## Rules that are load-bearing

**Never publish a page with no original writing on it.** `build.py` enforces
this: a topic page without `notes/<slug>.txt` and a recap without
`synopsis/YYYY-MM-DD.txt` are generated with `noindex` and kept out of
`sitemap.xml`. Do not "fix" this by removing the guard. Submitting fifty pages of
scraped headlines is how a domain gets classified as scraped content, and that is
very hard to undo.

**Headline plus link out only.** Never store, render or generate article text or
long snippets from any source, anywhere in this repo. Aggregators — NewsNow
included — have been sued over exactly this. It is the whole legal position.

**Keep the two definitions in sync.** `extension/feeds.js` and
`generator/config.json` hold the same eight sources *and* the same six topic
keyword lists. A reader who filters the extension to "Oil" and then opens
`/topics/oil.html` must see the same selection. Change one, change the other,
and run `python3 dev/check-sync.py` — it fails on any drift.

**Balanced is the default sort for a reason.** Sorted strictly newest-first,
Yahoo Finance took 13 of the top 15 slots and pushed Reuters and Bloomberg off
the first screen, because publication frequency is not editorial importance.
`balance()` in `newtab.js` round-robins one headline per desk per pass. Don't
change the default back to `newest` without re-checking that distribution.

**Bump `version` in `extension/manifest.json` on every store resubmission.**
Chrome rejects a re-upload at the same version.

## State, as of 2026-08-03

All eight feeds verified live from this machine (HTTP 200, non-empty): Reuters,
Bloomberg, CNBC, MarketWatch, Yahoo Finance, ZeroHedge, Investing.com, FT.
A full live build produced 306 unique headlines over 72h. The earlier
"feed URLs unverified" caveat is resolved.

Reuters and Bloomberg come via Google News site-restricted search because neither
publishes open RSS any more. That works and is headline-plus-link only, but it
depends on a Google endpoint with no stability guarantee — if either source
matters commercially, licence a real feed.

Icons (16/48/128) are real and on-brand — a wire motif with the signal-red rule,
matching the extension UI.

Not yet done: store screenshots (five, 1280×800, listed in `launch/launch-kit.md`
§1), notes for the other five topics — only `notes/oil.txt` is written, so the
rest stay noindex — and no synopsis has ever been written, so no recap has ever
been indexable.
