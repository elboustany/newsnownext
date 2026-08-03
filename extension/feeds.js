// GENERATED FILE — do not edit by hand.
// Source of truth: generator/config.json
// Regenerate:      python3 dev/gen-feeds.py
//
// Bloomberg, Reuters and several others have no open RSS any more, so those
// come through Google News site-restricted search. Where that is the case the
// source carries a `via` label and the UI shows it.

export const REGIONS = [
  {
    id: "markets",
    title: "Markets",
    sources: [
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
        id: "investing",
        label: "Investing.com",
        url: "https://www.investing.com/rss/news.rss"
      }
    ]
  },
  {
    id: "us",
    title: "US News",
    sources: [
      {
        id: "cnbc",
        label: "CNBC",
        url: "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"
      },
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
      }
    ]
  },
  {
    id: "uk",
    title: "UK News",
    sources: [
      {
        id: "bbc",
        label: "BBC",
        url: "https://feeds.bbci.co.uk/news/business/rss.xml"
      },
      {
        id: "ft",
        label: "Financial Times",
        url: "https://www.ft.com/rss/home/international"
      }
    ]
  },
  {
    id: "blogs",
    title: "Blogs",
    sources: [
      {
        id: "seekingalpha",
        label: "Seeking Alpha",
        url: "https://seekingalpha.com/feed.xml"
      },
      {
        id: "googletop",
        label: "Google Top Stories",
        via: "Google News",
        url: "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
      },
      {
        id: "zerohedge",
        label: "ZeroHedge",
        url: "https://feeds.feedburner.com/zerohedge/feed"
      },
      {
        id: "projectsyndicate",
        label: "Project Syndicate",
        url: "https://www.project-syndicate.org/rss"
      }
    ]
  },
  {
    id: "china",
    title: "China News",
    sources: [
      {
        id: "scmp",
        label: "South China Morning Post",
        url: "https://www.scmp.com/rss/91/feed"
      },
      {
        id: "globaltimes",
        label: "Global Times",
        via: "Google News",
        url: "https://news.google.com/rss/search?q=when:2d+site:globaltimes.cn&hl=en-US&gl=US&ceid=US:en"
      },
      {
        id: "chinagoogle",
        label: "China News (Google)",
        via: "Google News",
        url: "https://news.google.com/rss/search?q=when:1d+china+economy+OR+markets&hl=en-US&gl=US&ceid=US:en"
      }
    ]
  },
  {
    id: "france",
    title: "France News",
    sources: [
      {
        id: "lemonde",
        label: "Le Monde",
        url: "https://www.lemonde.fr/economie/rss_full.xml"
      },
      {
        id: "france24",
        label: "France 24",
        url: "https://www.france24.com/en/rss"
      }
    ]
  },
  {
    id: "switzerland",
    title: "Switzerland News",
    sources: [
      {
        id: "swissinfo",
        label: "SwissInfo",
        via: "Google News",
        url: "https://news.google.com/rss/search?q=when:7d+site:swissinfo.ch&hl=en-US&gl=US&ceid=US:en"
      },
      {
        id: "swissgoogle",
        label: "Switzerland News (Google)",
        via: "Google News",
        url: "https://news.google.com/rss/search?q=when:2d+switzerland+economy+OR+SNB+OR+franc&hl=en-US&gl=US&ceid=US:en"
      }
    ]
  },
  {
    id: "middleeast",
    title: "Middle East News",
    sources: [
      {
        id: "aljazeera",
        label: "Al Jazeera",
        url: "https://www.aljazeera.com/xml/rss/all.xml"
      },
      {
        id: "haaretz",
        label: "Haaretz",
        url: "https://www.haaretz.com/cmlink/1.4605102"
      },
      {
        id: "almonitor",
        label: "Al Monitor",
        url: "https://www.al-monitor.com/rss"
      }
    ]
  }
];

export const TOPICS = [
  {
    slug: "oil",
    title: "Oil and energy",
    keywords: [
      "oil",
      "crude",
      "brent",
      "wti",
      "opec",
      "natural gas",
      "lng",
      "refinery",
      "barrel",
      "pipeline",
      "energy prices"
    ]
  },
  {
    slug: "crypto",
    title: "Crypto",
    keywords: [
      "bitcoin",
      "btc",
      "ethereum",
      "ether",
      "crypto",
      "stablecoin",
      "binance",
      "coinbase",
      "defi",
      "digital asset",
      "tokenised",
      "tokenized"
    ]
  },
  {
    slug: "rates",
    title: "Central banks and rates",
    keywords: [
      "fed",
      "federal reserve",
      "fomc",
      "ecb",
      "bank of england",
      "bank of japan",
      "boj",
      "interest rate",
      "rate cut",
      "rate hike",
      "inflation",
      "cpi",
      "yield",
      "treasury",
      "bond"
    ]
  },
  {
    slug: "equities",
    title: "Equities",
    keywords: [
      "stocks",
      "shares",
      "equities",
      "s&p",
      "nasdaq",
      "dow",
      "ftse",
      "dax",
      "nikkei",
      "earnings",
      "ipo",
      "buyback",
      "index",
      "wall street"
    ]
  },
  {
    slug: "china",
    title: "China and Asia",
    keywords: [
      "china",
      "chinese",
      "beijing",
      "pboc",
      "yuan",
      "renminbi",
      "hong kong",
      "japan",
      "yen",
      "korea",
      "india",
      "asia"
    ]
  },
  {
    slug: "ai-and-tech",
    title: "AI and tech",
    keywords: [
      "ai",
      "artificial intelligence",
      "chip",
      "semiconductor",
      "nvidia",
      "openai",
      "data centre",
      "data center",
      "cloud",
      "apple",
      "microsoft",
      "meta",
      "alphabet",
      "tesla"
    ]
  }
];

// Flat list, for fetching and for the source filter.
export const FEEDS = REGIONS.flatMap(r =>
  r.sources.map(s => ({ ...s, regionId: r.id, region: r.title })));
