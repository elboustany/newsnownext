# NewsNowNext — launch kit

Everything below is drafted and ready to post. Nothing here works if it goes out
from a brand-new account with no history, so read the "before you post anything"
section first.

---

## Before you post anything

Three things, in this order, or the rest is wasted:

1. **Ship the extension first.** Every post below has a call to action. "Install
   the new tab" converts far better than "visit my site", and it gives you a
   Chrome Web Store listing that accumulates its own search traffic.
2. **Use accounts with history.** Reddit and Hacker News both bury links from
   accounts that have only ever promoted one thing. If the client has no
   presence, use yours, and post as someone who built a tool — not as the brand.
3. **Get one topic page indexed.** Write the intro notes so at least two topic
   pages come out of the build indexable. There is no point sending traffic to a
   site with nothing crawlable on it.

---

## 1. Chrome Web Store listing

**Name**
NewsNowNext — Market Wire

**Short description** (132 char limit)
Every new tab becomes a live financial wire: Reuters, Bloomberg, CNBC, MarketWatch and more, on one timeline.

**Detailed description**

> Eight tabs of financial news, replaced by the one you already open.
>
> NewsNowNext turns every new tab into a single live wire of market headlines,
> pulled from Reuters, Bloomberg, CNBC, MarketWatch, Yahoo Finance, the FT,
> Investing.com and ZeroHedge, sorted newest first.
>
> **A timeline, not a homepage.** Headlines sit against the trading day, with
> Tokyo, London and New York opens marked across the feed, so you can see what
> broke before the bell and what came after it.
>
> **Mute what you don't read.** Switch any source off and it stays off.
>
> **Fast and quiet.** Headlines are cached, so the page appears instantly and
> refreshes in the background. No account, no tracking, no ads.
>
> Every headline links straight to the publisher. NewsNowNext does not host or
> reproduce article text.

**Category:** News & Weather
**Language:** English

**Screenshots to prepare** (1280×800, five of them):
1. The full wire mid-session, London open rule visible
2. Dark mode
3. Source chips with two muted
4. Close crop of a session rule — this is the thing nobody else has
5. The wire on a narrow window

**Privacy justification** (the review team will ask):
- `storage` — caches headlines and remembers which sources the user muted, locally
- host permissions — fetches the RSS feeds listed; no other requests are made
- Single purpose: display a financial news feed on the new tab page

---

## 2. Show HN

**Title**
`Show HN: A new tab page that turns the trading day into a timeline`

**Body**

> I built this because I had eight finance tabs open every morning and still
> missed things — mostly because a headline at 06:00 and the same headline at
> 14:30 mean completely different things, and no aggregator shows you which side
> of the open a story landed on.
>
> So the feed is a timeline. Tokyo, London and New York opens are drawn as rules
> across it. Everything is sorted newest first, source filters persist, and it
> caches so the tab opens instantly.
>
> Sources are Reuters, Bloomberg, CNBC, MarketWatch, Yahoo Finance, FT,
> Investing.com and ZeroHedge. Bloomberg and Reuters killed their public RSS, so
> those two come through Google News site queries — if anyone knows a cleaner
> legitimate route, I'd genuinely like to hear it.
>
> No account, no tracking, no article text stored — headlines link out.
>
> Chrome extension: [link]  ·  Web version: https://www.newsnownext.org

**Timing:** Tuesday–Thursday, 07:00–09:00 US Eastern. Be at your desk for the
next four hours — replying to the first ten comments is most of what determines
whether it stays on the front page.

**Have an answer ready for:** "isn't this just an RSS reader?" The honest answer
is yes, with an opinionated default source list and the session timeline. Don't
oversell it; HN punishes that harder than it punishes simplicity.

---

## 3. Product Hunt

**Tagline** (60 char)
Your new tab, as a live financial wire

**Description**
NewsNowNext replaces the Chrome new tab with a single timeline of market
headlines from eight major finance desks. Trading session opens are drawn across
the feed, so you can see what broke before the bell. Mute any source. No account,
no tracking.

**First comment from the maker**

> Hi Product Hunt 👋
>
> This started as a personal annoyance: I had Reuters, CNBC, MarketWatch and four
> others open every morning, and I was still reading the same story three times
> without noticing when it actually broke.
>
> The fix that worked was treating news as a timeline instead of a list. The
> session rules across the feed are the whole idea — a headline before the London
> open and one after it are different pieces of information.
>
> It's free, there's no account, and headlines link straight to the publisher.
> Happy to answer anything, and I'm collecting requests for extra sources.

**Ship it on a Tuesday or Wednesday, 00:01 PT.**

---

## 4. Reddit

Check each subreddit's self-promotion rule the week you post — they change, and
several finance subs ban tool links outright. These are written as contributions,
not adverts, which is the only version that survives.

**r/SideProject** — safest, permissive
> Title: I turned my new tab into a financial news timeline instead of a list
>
> Body: short build story, what was hard (Bloomberg and Reuters have no public
> RSS any more), screenshot, link. Ask what sources people would add.

**r/webdev or r/chrome_extensions** — lead with the technical problem
> Title: MV3 extensions can fetch cross-origin RSS directly — no proxy needed
>
> Body: the actual finding, with the manifest snippet, then mention the extension
> at the end as the thing you built while learning it. This one earns links.

**r/algotrading, r/investing, r/stocks** — highest value, highest risk.
Do not link on the first post. Comment usefully for two weeks first, then post
only if the sub explicitly allows tools. A ban here costs more than the traffic
is worth.

---

## 5. X / Twitter — 10 posts

Post 1–3 in launch week, then roughly two a week.

1. Eight finance tabs every morning. Now it's one, and it's the tab I was going to open anyway. [screenshot]
2. A headline at 06:00 and the same headline at 14:30 are not the same information. So the feed is a timeline, with the session opens drawn across it.
3. Bloomberg and Reuters both retired their public RSS feeds. Half the work on this was routing around that. Here's what I ended up with:
4. Dark mode, because nobody checking overnight Asia news wants a white screen. [screenshot]
5. Shipped: mute any source and it stays muted. The most requested thing, and the smallest change.
6. What's on the wire this morning, in order: [3 headlines + link to today's recap]
7. The new tab page is the most valuable real estate in a browser and almost everyone wastes it on a search box they never use.
8. Added [source] after someone asked in the comments. What else is missing?
9. Rolling 72 hours per topic, so you can see how a story built instead of only where it ended up. [link to a topic page]
10. Free, no account, no tracking, headlines link straight to the publisher. [link]

**Reply targets:** finance and macro accounts posting "here's what I read every
morning" threads. Don't drop the link cold — answer the question first, mention
the tool only if it fits.

---

## 6. Newsletter and community outreach

Twenty targets, personalised, sent over two weeks. Macro and markets newsletter
writers, finance Discords, trading Telegram groups.

**Template**

> Subject: A new tab page for your morning read
>
> Hi [name],
>
> You mentioned [specific thing they wrote] — the bit about [detail] is exactly
> the problem I ended up building for.
>
> I made a Chrome extension that turns the new tab into a single wire of
> headlines from eight finance desks, with the trading session opens marked
> across the timeline. Free, no account.
>
> [link]
>
> Not asking for a mention. If it's useful, use it; if it's not, I'd rather know
> why than not hear back.
>
> [you]

The last line is not modesty — it is the line that gets replies.

---

## 7. Sequence

| Week | Do this |
|---|---|
| 0 | Extension submitted for review. Two topic notes written. Screenshots made. |
| 1 | Store approval → Show HN Tuesday, r/SideProject Thursday. Post X 1–3. |
| 2 | Product Hunt. r/webdev technical post. Begin newsletter outreach (10). |
| 3 | Second outreach batch (10). Daily recap published every weekday from here. |
| 4 | Review search console. Write notes for the topics actually getting impressions. |
| 5–12 | Two X posts a week, one recap a day, one outreach batch a fortnight. Report monthly. |

Weeks 5–12 are the part that decides the outcome and the part everyone skips.

---

## 8. What not to do

- **Don't buy backlinks.** For a site with no original content, a spike in links
  is the fastest route to a manual penalty.
- **Don't syndicate the headlines to social automatically.** Publisher-headline
  bots get reported. Post your own recaps instead.
- **Don't publish AI-written recaps unedited.** Mass-produced market summaries
  are precisely what the spam policies target. The build enforces this: no
  synopsis file, no indexable recap.
- **Don't post to the big finance subs in week one.** One ban closes the highest
  value channel permanently.
