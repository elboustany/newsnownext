# NewsNowNext growth package

Three deliverables, all built and working:

```
extension/           Chrome MV3 new-tab extension — the acquisition and retention piece
generator/           Python static site builder — the indexable-content piece
launch/              Store copy, Show HN, Product Hunt, Reddit, X posts, 12-week sequence
pack-extension.sh    Builds the store upload into dist/
```

See `CLAUDE.md` for the working rules — the constraints that must not be
"simplified" away in a later edit.

---

## 1. Extension

**See it in one command — no install**

```bash
python3 dev/devserver.py
```

Then open <http://localhost:8787>. That runs the real extension code as an
ordinary web page (storage shimmed to localStorage, feeds proxied past CORS) and
serves the generated site at <http://localhost:8787/site/topics/oil.html>. This
is the version to put in front of a client on a laptop — nothing to install and
nothing to approve.

**Try it as a real extension**

1. Chrome → `chrome://extensions` → turn on Developer mode
2. Load unpacked → select the `extension/` folder
3. Open a new tab

Do this before shipping: the dev harness fakes `chrome.storage` and the network,
so it cannot catch a permissions or manifest problem.

**Sorting and filtering**

Live text filter (`/` to focus, `esc` to clear, quoted `"exact phrase"`
supported, multiple words are AND), six topic filters sharing the generator's
keyword lists, a time window (6/12/24/72h), source toggles with double-click to
solo, and four orderings:

| Order | What it does |
|---|---|
| **Balanced** (default) | One headline per desk per pass |
| Newest / Oldest | Strict time order, with the session rules drawn in |
| Grouped by source | All of one desk, then the next |

Balanced is the default because strict newest-first let Yahoo Finance take 13 of
the top 15 slots and buried Reuters and Bloomberg. Publication frequency isn't
editorial importance, and the merge is the whole product.

Every setting persists. The generated topic and recap pages carry their own
filter bar — search, source toggles and a newest/oldest flip — which is
progressive enhancement over the server-rendered list, so crawlers still see
every headline.

**What it does**

Replaces the new tab with a single merged wire from eight finance sources,
newest first. Tokyo, London and New York opens are drawn as labelled rules across
the feed — that session timeline is the thing that makes it not just another RSS
reader, and it's what the launch copy leads on. Source filters persist. Headlines
cache in `chrome.storage.local`, so the tab paints instantly and refreshes in the
background when the cache is over five minutes old. Light and dark, responsive,
keyboard-focusable, respects reduced motion.

**Feeds — verified 2026-08-03**

All eight sources were tested live and all eight returned usable RSS. A full
build produced 306 unique headlines over 72 hours. The earlier "unverified feed
URLs" caveat is closed.

One URL changed: the FT's `/rss/home` 301-redirects to `/rss/home/international`,
so both configs now request the destination directly.

If a source breaks later, the extension footer reports how many failed and
hovering shows which; the generator prints `FAIL <source>` and carries on. Fix
the URL in **both** `extension/feeds.js` and `generator/config.json` — the two
lists are deliberately identical in shape.

**Publishing**

```bash
./pack-extension.sh          # writes dist/newsnownext-extension-<version>.zip
```

The script zips the *contents* of `extension/` (which is what the store requires)
and strips macOS metadata (which the store rejects).

- Chrome Web Store developer account: one-off $5
- Review usually takes 1–3 days; new-tab overrides get looked at more closely, so
  the privacy justifications in the launch kit matter
- Bump `version` in `extension/manifest.json` on every resubmission, or the
  upload is rejected

Same package works in Edge (separate store, free, worth doing) and needs only
minor changes for Firefox.

---

## 2. Static page generator

```bash
cd generator
python3 build.py                      # fetch feeds, build pages into ./site
python3 build.py --no-fetch           # rebuild from cache, no network
python3 build.py --config config.test.json   # offline self-test on fixtures
```

Standard library only, no dependencies. Outputs:

```
site/topics/<slug>.html    six topic pages, rolling 72 hours
site/topics/index.html
site/recap/YYYY-MM-DD.html dated daily recap with NewsArticle JSON-LD
site/recap/index.html      archive
site/sitemap.xml           indexable pages only
site/feed.xml              your own RSS of recaps
site/robots.txt
site/assets/site.css
```

**The thin-content guard — this is the important bit**

A topic page with no original writing on it is published with `noindex`. Same for
a daily recap with no synopsis. To make a page indexable you write:

- `generator/notes/<slug>.txt` — 100–200 words on what the page covers
  (`notes/oil.txt` is written as a working example)
- `generator/synopsis/YYYY-MM-DD.txt` — 200–300 words on the day
  (`synopsis/TEMPLATE.txt` has the structure and the rules)

The offline self-test asserts this still works: `oil` has a note and comes out
indexable and in the sitemap, `equities` has none and comes out `noindex`. Run it
after any change to `build.py`.

Right now only `oil` is written. The other five topics and every recap are
noindex until someone writes them — that is the work the build cannot do for you.

The sitemap only ever contains pages that cleared this bar. It's deliberately
annoying: submitting fifty pages of other people's headlines to Google is how a
site like this gets classified as scraped content, and that's very hard to undo.

**Deploying on the Hetzner box**

```cron
*/30 6-22 * * 1-5  cd /srv/nnn/generator && /usr/bin/python3 build.py >> /var/log/nnn.log 2>&1
```

Then serve `generator/site/` under `/topics/` and `/recap/` on the domain, or
rsync it to wherever the site is hosted. Point `base_url` in `config.json` at the
canonical host — note the live site canonicalises to `www.`, so keep that.

---

## 3. Launch kit

`launch/launch-kit.md` — Chrome Web Store copy with the exact privacy
justifications the reviewer asks for, a Show HN post, Product Hunt listing and
maker comment, three Reddit drafts with the risk on each flagged, ten X posts, an
outreach template, and a 12-week posting sequence.

Read section 8 before anything goes out.

---

## Honest caveats

- **Bloomberg and Reuters come via Google News site queries.** That's a common
  approach and it's headline-plus-link only, but it depends on a Google endpoint
  with no stability guarantee. If either matters commercially, licence a real feed.
- **Check the terms on every source before this goes commercial.** Headlines plus
  a link out is the defensible position; snippets and full text are not, and
  aggregators have been sued over exactly this.
- **The build is the cheap half.** Weeks 5–12 of the sequence decide the outcome.

---

## Scope, for the client conversation

**Delivered, one-off**
Chrome extension, static page generator, launch kit. Fixed fee.

**Not included unless separately agreed**
Site redesign or front-end work on newsnownext.org · email digest setup ·
paid advertising · daily writing of the recap synopsis · logo or brand work ·
Firefox and Safari ports.

**Ongoing, monthly**
Running the pipeline, publishing the sequence, monthly reporting.
Three-month minimum, because organic search shows nothing meaningful in four
weeks and you don't want to be judged on an unfair sample.

**One number to agree before starting**
Traffic, email subscribers, or extension installs. Pick one, write it down, and
review against it monthly.
