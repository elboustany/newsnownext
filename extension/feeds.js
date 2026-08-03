// Feed sources. Edit freely — `id` must stay unique, `label` is what users see.
//
// Bloomberg and Reuters do not publish open RSS feeds any more, so those two
// are pulled through Google News site-restricted search, which returns their
// headlines with a redirect link. If the client has a licensed feed for either,
// swap the url and drop the `via` field.

export const FEEDS = [
  {
    id: "reuters",
    label: "Reuters",
    via: "Google News",
    url: "https://news.google.com/rss/search?q=when:1d+site:reuters.com+(markets+OR+economy+OR+stocks)&hl=en-US&gl=US&ceid=US:en"
  },
  {
    id: "bloomberg",
    label: "Bloomberg",
    via: "Google News",
    url: "https://news.google.com/rss/search?q=when:1d+site:bloomberg.com+(markets+OR+economy+OR+stocks)&hl=en-US&gl=US&ceid=US:en"
  },
  {
    id: "cnbc",
    label: "CNBC",
    url: "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"
  },
  {
    id: "marketwatch",
    label: "MarketWatch",
    url: "https://feeds.content.dowjones.io/public/rss/mw_topstories"
  },
  {
    id: "yahoo",
    label: "Yahoo Finance",
    url: "https://finance.yahoo.com/news/rssindex"
  },
  {
    id: "zerohedge",
    label: "ZeroHedge",
    url: "https://feeds.feedburner.com/zerohedge/feed"
  },
  {
    id: "investing",
    label: "Investing.com",
    url: "https://www.investing.com/rss/news.rss"
  },
  {
    id: "ft",
    label: "Financial Times",
    // /rss/home 301s to this; requesting it directly saves a redirect hop.
    url: "https://www.ft.com/rss/home/international"
  }
];

// Trading sessions, drawn as rules across the timeline.
// Times are local to the exchange; the UI converts them for the reader.
export const SESSIONS = [
  { id: "tokyo",  label: "Tokyo open",   tz: "Asia/Tokyo",       h: 9,  m: 0 },
  { id: "london", label: "London open",  tz: "Europe/London",    h: 8,  m: 0 },
  { id: "ny",     label: "New York open",tz: "America/New_York", h: 9,  m: 30 },
  { id: "nyc",    label: "New York close",tz: "America/New_York",h: 16, m: 0 }
];
