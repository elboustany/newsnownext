# NewsNowNext

A from-scratch rebuild of **newsnownext.org**, plus a Chrome new-tab extension
in the same visual language. Client work (a friend of the owner); it will be
deployed somewhere other than the current Replit host.

```
generator/    Python static site builder - the site
extension/    Chrome MV3 new-tab extension - same look, same sources
launch/       Copy for every launch channel
dev/          Preview server + the two file generators (never shipped)
dist/         Store upload zips (generated)
```

## Why this exists

The live site is a client-rendered SPA, so crawlers get an empty shell and none
of the content is indexable. This build server-renders everything.

## Commands

```bash
python3 dev/devserver.py                     # site at /site/, extension at /
python3 dev/gen-feeds.py                     # regenerate extension/feeds.js
python3 dev/gen-css.py                       # regenerate extension/newtab.css
./pack-extension.sh                          # store upload zip

cd generator
python3 build.py                             # fetch live feeds, build ./site
python3 build.py --no-fetch                  # rebuild from cache
python3 build.py --config config.test.json   # offline self-test on fixtures
```

Before committing:

```bash
python3 dev/gen-feeds.py --check && python3 dev/gen-css.py --check
cd generator && python3 build.py --config config.test.json
```

The self-test must exit 0 with `oil` indexable and `thin-check` noindex -
that asserts the thin-content guard still works. `thin-check` exists only in
config.test.json and must never get a notes/ file.

## Rules that are load-bearing

**Match the existing design exactly.** The palette, type, grid and card
structure were sampled off the running site. The client's first reaction to a
redesign was that it was too different - visual invention is not wanted here.
All tokens live in `generator/theme.py`; nothing else defines a colour.

**The nav stays flat and verbatim.** Nine links, this order: News, Books,
Forex, World News, Podcasts, Contact, Preferences, Read Later (bookmark
icon), Portfolio. A regroup into Markets/Discover/More dropdowns was shipped
once and the client rejected it in three messages ("Ne change pas le design /
Ni les boutons / Ni le contenu"). Extra pages link from the footer and the
ticker's Events tab. Both AD banners (Market Intelligence Pro on top,
Financial News Premium fixed at the bottom) are his placeholder ads,
reproduced verbatim including the em dashes - do not reword or replace them,
and the home page shows no visible h1 (it is sr-only, for crawlers).

**No dark mode.** The live site is light-only. A page that flips to dark on a
dark-mode machine is the exact mismatch this build exists to avoid.

**Keep the regions.** The eight cards mirror the live site's country layout.
`Markets` is the only addition and is one config block to remove. Do not merge
regions into a single wire - the country structure is what the client asked to
keep.

**New features go behind `More filters`.** Search, region and order are the
primary bar; topics and the time window are collapsed by default. The default
view should look like the site people already know.

**Never publish a page with no original writing on it.** `build.py` enforces
this: a topic page without `notes/<slug>.txt` and a recap without
`synopsis/YYYY-MM-DD.txt` get `noindex` and stay out of `sitemap.xml`. Do not
"fix" this by removing the guard.

**Headline plus link out only.** Never store, render or generate article text or
long snippets from any source. Aggregators have been sued over exactly this.

**Generated files.** `extension/feeds.js`, `extension/newtab.css` and the
manifest's `host_permissions` are generated from `generator/config.json` and
`generator/theme.py`. Edit the source, run the generator.

**`section[data-region]`, never bare `[data-region]`.** Each `<li>` also carries
`data-region` so the region filter can test it directly. A bare selector treats
every headline as a card, finds no `[data-item]` inside it, and hides the entire
page - with the counter still reading correctly, because it is computed before
that loop. This bug has been introduced once already.

**Bump `version` in `extension/manifest.json` on every store resubmission.**

## The ultimate version (branch note)

`v1.0-parity` (tag + `parity-version` branch) is the closest match to the live
site. `main` is the ultimate version on top of it: Today's Brief on the home
page fed by the synopsis file, house-ad banner selling the newsletter,
/newsletter/ page (set `newsletter_signup_url` in config.json to go live),
`dev/gen-digest.py` renders the send-ready email, trending gained
Consensus/Exclusives groups and cross-build velocity via
.cache/trending-history.json, bookmarks on every headline, webcal calendar
feed at /events/calendar.ics, PWA (manifest + sw.js + offline page), and
Preferences that actually personalise the feed (default region, pinned
region order, hidden sources, followed keywords -> the For You strip).

Bookmark buttons use data-bm-* attributes ON PURPOSE: they once carried
data-source and the filter's [data-source] selector matched 247 buttons and
crashed apply(). Same lesson as data-region. Keep selectors structural.

## State, as of 2026-08-03

22 sources across 8 regions, all verified live; 248 headlines on the home page.
Extension is v2.0.0.

Global Times' own RSS returns 200 but its item dates are months stale and its
topic feeds 404, so it routes through Google News. Reuters, Bloomberg and
SwissInfo likewise have no usable open RSS.

Not built: the market ticker strip (needs a market-data feed - a separate
decision), Trending Now, Books, Forex, Podcasts, Preferences, Read Later.

All six topic notes are written (short by design - they exist for crawlers,
rendered as small muted text so they never compete with the wire). Recap
synopses remain unwritten, so recaps stay noindex until someone writes them.
17 URLs in the sitemap. Source logos are fetched once at build time into
static/logos/ and shipped as local assets - never hotlinked.
