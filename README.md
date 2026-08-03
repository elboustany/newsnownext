# NewsNowNext

A rebuild of newsnownext.org as a static site, plus a Chrome new-tab extension
that looks like the same product. Same layout, same palette, same region cards -
with search, filters and sorting added, and everything server-rendered so search
engines can actually read it.

```
generator/           Python static site builder - the site
extension/           Chrome MV3 new-tab extension - same look, same sources
launch/              Store copy, Show HN, Product Hunt, Reddit, X posts, sequence
dev/                 Local preview server and the two file generators
dist/                Store upload zips (generated)
pack-extension.sh    Builds the store upload
```

---

## See it, in one command

```bash
python3 dev/devserver.py
```

- **Site** - <http://localhost:8787/site/>
- **Extension** - <http://localhost:8787>

The extension preview runs the real extension code as an ordinary web page
(`chrome.storage` shimmed to localStorage, feeds proxied past CORS), so there is
nothing to install and nothing to approve. A red bar marks it as a preview.

To check it as a real extension - do this before shipping, since the harness
fakes storage and the network - `chrome://extensions` → Developer mode → Load
unpacked → pick `extension/`.

---

## Matching the existing design

The palette, type, grid and card structure were sampled off the running site,
not eyeballed:

| | |
|---|---|
| Type | Inter, 400/500/600/800/900 |
| Body / cards | `#ffffff`, border `#e1e7ef`, radius `8px` |
| Card header | `#f1f5f9` |
| Nav bar | `#374151`, links `#e5e7eb` |
| Logo | NEWS `#f97316`, NOW `#10b981`, NEXT `#ef4444` |
| Source names | `#dc2626` |
| Headlines | `#2463eb`, 14px/500 |
| Timestamps | `#65758b`, 12px, `Aug 3 12:23 PM` |
| Grid | 1 col → 2 at 768px → 3 at 1280px, gap 16/24px |

All of it lives in `generator/theme.py`. Nothing else defines a colour, so the
whole thing re-skins from one file.

**There is deliberately no dark mode.** The live site is light-only, and a page
that flips to dark on a dark-mode machine is exactly the mismatch this build
avoids. `theme.py` says where to add one if it's ever wanted.

---

## The regions

The eight cards mirror the live site: **US News, UK News, Blogs, China News,
France News, Switzerland News, Middle East News**, plus **Markets** - the three
finance desks that had no home in the country cards. Delete that one block in
`config.json` to match the live site exactly.

22 sources, all verified live. Two notes worth keeping:

- Several desks have no open RSS any more (Reuters, Bloomberg, SwissInfo,
  Global Times), so those route through Google News site-restricted search. They
  are labelled *via Google News* in the UI. It works and it is headline-plus-link
  only, but it depends on a Google endpoint with no stability guarantee.
- Google News appends the real publisher to every headline. For a broad query
  that publisher is whoever ran the story, so a Swiss rates headline arrived as
  "… - Bitcoin World" and matched the crypto topic. `clean_title` strips that
  suffix for Google-routed sources only.

---

## Filtering and sorting

Primary controls, always visible:

- **Search** - live, `/` to focus, `esc` to clear, multiple words are AND,
  `"quoted phrases"` supported, matches highlighted
- **Region** - one click to a single country card
- **Order** - newest or oldest first, within every source block

Behind **More filters**, closed by default: six topic filters, and a time window
(6/12/24h). They were kept out of the main bar on purpose - the default view
should look like the site people already know.

Every setting persists. Preferences are validated on load, so an option removed
in a later version can't silently apply a filter nobody chose.

On the site this is progressive enhancement over server-rendered HTML: the full
wire is in the page, and the script only hides and reorders rows that are
already there. No JavaScript still gets every headline.

---

## Build

```bash
cd generator
python3 build.py                             # fetch live feeds, build ./site
python3 build.py --no-fetch                  # rebuild from cache, no network
python3 build.py --config config.test.json   # offline self-test on fixtures
```

Standard library only, no dependencies. Outputs `index.html`, six topic pages,
a dated recap, `sitemap.xml`, `feed.xml`, `robots.txt` and the assets.

Run the self-test after any change to `build.py`. It uses local fixtures
including a deliberately malformed feed, writes to `site-test/`, and must exit 0
with `oil` indexable and `equities` noindex.

**Deploying**

```cron
*/30 6-22 * * 1-5  cd /srv/nnn/generator && /usr/bin/python3 build.py >> /var/log/nnn.log 2>&1
```

Then serve `generator/site/`. Point `base_url` in `config.json` at the real host.

---

## The thin-content guard

A topic page with no original writing is published with `noindex`, and so is a
recap with no synopsis. To make one indexable, write:

- `generator/notes/<slug>.txt` - 100-200 words (`notes/oil.txt` is the example)
- `generator/synopsis/YYYY-MM-DD.txt` - 200-300 words (`synopsis/TEMPLATE.txt`)

The sitemap only ever contains pages that cleared that bar. It is deliberately
annoying: submitting fifty pages of other people's headlines is how a domain
gets classified as scraped content, and that is very hard to undo.

Right now only `oil` is written, so the home page plus three URLs are indexable
and the other five topics are not. That is the work the build cannot do for you.

---

## Generated files

`extension/feeds.js`, `extension/newtab.css` and the manifest's
`host_permissions` are generated - never edit them by hand:

```bash
python3 dev/gen-feeds.py     # feeds.js + host_permissions, from config.json
python3 dev/gen-css.py       # newtab.css, from theme.py
python3 dev/gen-feeds.py --check && python3 dev/gen-css.py --check
```

One source of truth each: sources and topics in `generator/config.json`, the
palette in `generator/theme.py`. Two hand-edited copies never stay in step.

---

## Publishing the extension

```bash
./pack-extension.sh          # dist/newsnownext-extension-<version>.zip
```

- Chrome Web Store developer account: one-off $5
- Review usually takes 1-3 days; new-tab overrides get looked at more closely,
  so the privacy justifications in `launch/launch-kit.md` matter
- Bump `version` in `extension/manifest.json` on every resubmission

---

## Honest caveats

- **Not everything on the live site is rebuilt.** The market ticker strip
  (S&P/NASDAQ/DOW/VIX), Trending Now, Books, Forex, Podcasts, Preferences and
  Read Later are not here. The ticker needs a market-data feed, which is a
  separate decision; the rest were never in scope. Nav links only to pages that
  exist.
- **Check the terms on every source before this goes commercial.** Headline plus
  a link out is the defensible position; snippets and full text are not, and
  aggregators have been sued over exactly this.
- **The build is the cheap half.** Weeks 5-12 of the launch sequence decide the
  outcome.
