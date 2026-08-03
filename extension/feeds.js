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

// Topic filters. These must stay identical to `topics` in
// generator/config.json — same slugs, same keywords — so a reader filtering the
// extension to "Oil" sees the same selection as /topics/oil.html.
// `dev/check-sync.py` fails if the two drift apart.
export const TOPICS = [
  {
    slug: "oil",
    title: "Oil",
    keywords: ["oil", "crude", "brent", "wti", "opec", "natural gas", "lng",
               "refinery", "barrel", "pipeline", "energy prices"]
  },
  {
    slug: "crypto",
    title: "Crypto",
    keywords: ["bitcoin", "btc", "ethereum", "ether", "crypto", "stablecoin",
               "binance", "coinbase", "defi", "digital asset", "tokenised",
               "tokenized"]
  },
  {
    slug: "rates",
    title: "Rates",
    keywords: ["fed", "federal reserve", "fomc", "ecb", "bank of england",
               "bank of japan", "boj", "interest rate", "rate cut", "rate hike",
               "inflation", "cpi", "yield", "treasury", "bond"]
  },
  {
    slug: "equities",
    title: "Equities",
    keywords: ["stocks", "shares", "equities", "s&p", "nasdaq", "dow", "ftse",
               "dax", "nikkei", "earnings", "ipo", "buyback", "index",
               "wall street"]
  },
  {
    slug: "china",
    title: "China & Asia",
    keywords: ["china", "chinese", "beijing", "pboc", "yuan", "renminbi",
               "hong kong", "japan", "yen", "korea", "india", "asia"]
  },
  {
    slug: "ai-and-tech",
    title: "AI & tech",
    keywords: ["ai", "artificial intelligence", "chip", "semiconductor",
               "nvidia", "openai", "data centre", "data center", "cloud",
               "apple", "microsoft", "meta", "alphabet", "tesla"]
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
