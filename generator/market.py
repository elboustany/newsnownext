"""
Market and FX data, from free keyless sources.

Two providers, chosen because neither needs an account:

  * Indices, commodities and treasury yields — Yahoo Finance's chart endpoint.
    Same symbols the live site's own /api/market returns (GSPC, IXIC, GDAXI,
    STOXX50E …), because its backend proxies Yahoo too.
  * FX — the ECB's daily reference rates via Frankfurter, which also serves
    historical dates. That is what makes the six timeframe columns on the
    forex table possible without a paid plan.

Everything is cached to data/market-cache.json. A failed fetch never blanks the
page: the last known value is reused and flagged stale, because a ticker
showing nothing looks broken and a ticker showing a made-up number is worse.

Honest limits, both surfaced in the UI rather than hidden:
  * ECB publishes one reference rate per business day around 16:00 CET, so FX
    moves are day-over-day, not intraday.
  * Yahoo rate-limits aggressively per IP. It returns 429 from some hosts
    (including sandboxes and shared CI runners) while working fine from an
    ordinary VPS. If the deploy host is throttled, set FMP_API_KEY and the
    fetcher uses Financial Modeling Prep instead — the provider the live site
    was already coded against.
"""

import json
import os
import urllib.parse
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "data" / "market-cache.json"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{}?interval=1d&range=5d"
FRANKFURTER = "https://api.frankfurter.dev/v1/{}?base=EUR&symbols={}"
FMP = "https://financialmodelingprep.com/api/v3/quote/{}?apikey={}"

# The four ticker tabs, exactly as the live site groups them.
TABS = [
    ("markets", "Markets", [
        ("^GSPC", "S&P 500", "SP"),
        ("^IXIC", "NASDAQ", "NQ"),
        ("^DJI", "DOW JONES", "DJ"),
        ("^VIX", "VIX", "VX"),
    ]),
    ("europe", "Europe", [
        ("^FTSE", "FTSE 100", "UK"),
        ("^GDAXI", "DAX", "DE"),
        ("^FCHI", "CAC 40", "FR"),
        ("^STOXX50E", "STOXX 50", "EU"),
    ]),
    ("rates", "Fixed Income", [
        ("^IRX", "US 3MO", "3M"),
        ("^FVX", "US 5YR", "5Y"),
        ("^TNX", "US 10YR", "10Y"),
        ("^TYX", "US 30YR", "30Y"),
    ]),
    ("commodities", "Commodities", [
        ("GC=F", "GOLD", "AU"),
        ("SI=F", "SILVER", "AG"),
        ("CL=F", "OIL", "OIL"),
        ("NG=F", "NAT GAS", "NG"),
    ]),
]

# CNBC's public quote service returns every instrument in one keyless call and,
# unlike Yahoo, does not rate-limit server-side. Yahoo stays as a fallback.
CNBC_SYMBOLS = {
    "^GSPC": ".SPX", "^IXIC": ".IXIC", "^DJI": ".DJI", "^VIX": ".VIX",
    "^FTSE": ".FTSE", "^GDAXI": ".GDAXI", "^FCHI": ".FCHI", "^STOXX50E": ".STOXX50E",
    "^IRX": "US3M", "^FVX": "US5Y", "^TNX": "US10Y", "^TYX": "US30Y",
    "GC=F": "@GC.1", "SI=F": "@SI.1", "CL=F": "@CL.1", "NG=F": "@NG.1",
}
CNBC = ("https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol"
        "?symbols={}&requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1"
        "&output=json&events=1")


def _num(v):
    """CNBC formats numbers for humans: '7,489.72', '4.678%', 'UNCH'."""
    if v is None:
        return None
    t = str(v).replace(",", "").replace("%", "").strip()
    if t in ("", "UNCH", "N/A", "--"):
        return 0.0
    try:
        return float(t)
    except ValueError:
        return None


def _cnbc_quotes():
    """One call for every symbol. Returns {our_symbol: (price, prev)}."""
    raw = _get(CNBC.format("|".join(CNBC_SYMBOLS.values())), tries=2)
    rows = raw.get("FormattedQuoteResult", {}).get("FormattedQuote", [])
    back = {v: k for k, v in CNBC_SYMBOLS.items()}
    out = {}
    for q in rows:
        ours = back.get(q.get("symbol"))
        if not ours:
            continue
        last, change = _num(q.get("last")), _num(q.get("change"))
        if last is None or change is None:
            continue
        out[ours] = (last, last - change)      # derive previous close
    return out


# The 18 pairs on the live forex page, in its order.
PAIRS = [
    "EUR/USD", "USD/JPY", "GBP/USD", "USD/TRY", "USD/CHF", "USD/CAD",
    "EUR/JPY", "AUD/USD", "NZD/USD", "EUR/GBP", "EUR/CHF", "AUD/JPY",
    "GBP/JPY", "CHF/JPY", "EUR/CAD", "AUD/CAD", "CAD/JPY", "NZD/JPY",
]

CURRENCIES = sorted({c for p in PAIRS for c in p.split("/")} - {"EUR"})

# Column headings on the live forex table, and how far back each looks.
SPANS = [("Daily", 1), ("1 Week", 7), ("1 Month", 30),
         ("YTD", None), ("1 Year", 365), ("3 Years", 1095)]


def _get(url, timeout=20, tries=3):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            # 429 means this IP is throttled; it will not clear in a few
            # seconds, and retrying 16 symbols x 3 turned a build into minutes.
            # Give up on this symbol immediately and let the cache cover it.
            if e.code == 429:
                raise
            last = e
        except Exception as e:                      # noqa: BLE001 - retried below
            last = e
        if attempt < tries - 1:
            time.sleep(1.5 * (attempt + 1))
    raise last


def load_cache():
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"quotes": {}, "fx": {}, "fetched": None}


def save_cache(cache):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True), encoding="utf-8")


# ── Quotes ───────────────────────────────────────────────────────────────

def _yahoo_quote(symbol):
    d = _get(YAHOO.format(urllib.parse.quote(symbol)))
    m = d["chart"]["result"][0]["meta"]
    price = m.get("regularMarketPrice")
    prev = m.get("chartPreviousClose") or m.get("previousClose")
    if price is None or prev is None:
        raise ValueError("incomplete quote")
    return float(price), float(prev)


def _fmp_quotes(symbols, key):
    """One batched call — the free plan counts calls, not symbols."""
    out = {}
    data = _get(FMP.format(",".join(symbols), key))
    for row in data:
        price, prev = row.get("price"), row.get("previousClose")
        if price is not None and prev is not None:
            out[row["symbol"]] = (float(price), float(prev))
    return out


def fetch_quotes(cache):
    """Return {symbol: {price, change, pct, stale}} for every ticker symbol."""
    symbols = [s for _, _, rows in TABS for s, _, _ in rows]
    fresh, key = {}, os.environ.get("FMP_API_KEY")

    if key:
        try:
            fresh = _fmp_quotes(symbols, key)
            print(f"  market: {len(fresh)}/{len(symbols)} via FMP")
        except Exception as e:                      # noqa: BLE001
            print(f"  market: FMP failed ({e}); falling back to Yahoo")

    if not fresh:
        try:
            fresh = _cnbc_quotes()
            print(f"  market: {len(fresh)}/{len(symbols)} via CNBC")
        except Exception as e:                      # noqa: BLE001
            print(f"  market: CNBC failed ({e}); falling back to Yahoo")

    if len(fresh) < len(symbols):
        ok = len(fresh)
        for sym in [s for s in symbols if s not in fresh]:
            try:
                fresh[sym] = _yahoo_quote(sym)
                ok += 1
            except Exception:                       # noqa: BLE001 - cache covers it
                pass
            time.sleep(0.7)                         # be polite; avoids burst 429s
        if ok < len(symbols):
            print(f"  market: {ok}/{len(symbols)} after Yahoo fallback")

    out = {}
    for sym in symbols:
        if sym in fresh:
            price, prev = fresh[sym]
            cache["quotes"][sym] = {"price": price, "prev": prev,
                                    "at": datetime.now(timezone.utc).isoformat()}
            stale = False
        elif sym in cache["quotes"]:
            price = cache["quotes"][sym]["price"]
            prev = cache["quotes"][sym]["prev"]
            stale = True
        else:
            out[sym] = None                         # never invent a number
            continue
        change = price - prev
        pct = (change / prev * 100) if prev else 0.0
        out[sym] = {"price": price, "change": change, "pct": pct, "stale": stale}
    return out


# ── FX ───────────────────────────────────────────────────────────────────

def _ecb(day):
    """EUR-based reference rates for a date ('latest' or YYYY-MM-DD).

    Returns (rates, effective_date). Frankfurter answers a non-business day
    with the previous publication, so the date it echoes back is the one that
    actually applies — which matters for the daily column below.
    """
    d = _get(FRANKFURTER.format(day, ",".join(CURRENCIES)))
    return d["rates"], d["date"]


def _ecb_previous(latest_date):
    """The publication before `latest_date`.

    Asking for `today - 1` is wrong: ECB publishes once per business day, so on
    any weekend or holiday that resolves to the same snapshot as `latest` and
    every daily change comes out as exactly 0.00%. Walk back through a short
    range and take the last date that differs.
    """
    start = (date.fromisoformat(latest_date) - timedelta(days=10)).isoformat()
    url = (f"https://api.frankfurter.dev/v1/{start}..{latest_date}"
           f"?base=EUR&symbols={','.join(CURRENCIES)}")
    series = _get(url)["rates"]
    earlier = sorted(d for d in series if d < latest_date)
    if not earlier:
        return None, None
    return series[earlier[-1]], earlier[-1]


def _cross(rates, pair):
    """Derive any pair from EUR-based rates. EUR itself is the base, so 1.0."""
    base, quote = pair.split("/")
    b = 1.0 if base == "EUR" else rates.get(base)
    q = 1.0 if quote == "EUR" else rates.get(quote)
    if not b or not q:
        return None
    return q / b


def fetch_fx(cache):
    """Return {pair: {rate, changes:{span: pct}, stale}} for all 18 pairs."""
    today = date.today()
    ok, stale = 0, False

    # Anchor on the latest publication, not on today's calendar date.
    try:
        latest, latest_date = _ecb("latest")
        cache["fx"]["latest"] = latest
        cache["fx"]["latest_date"] = latest_date
        ok += 1
    except Exception:                               # noqa: BLE001
        latest = cache["fx"].get("latest")
        latest_date = cache["fx"].get("latest_date")
        stale = True
    if not latest or not latest_date:
        return {}

    spans = {}                                      # label -> rates
    try:
        prev_rates, _ = _ecb_previous(latest_date)
        if prev_rates:
            spans["Daily"] = prev_rates
            cache["fx"]["prev"] = prev_rates
            ok += 1
    except Exception:                               # noqa: BLE001
        if cache["fx"].get("prev"):
            spans["Daily"] = cache["fx"]["prev"]
            stale = True

    anchor = date.fromisoformat(latest_date)
    for label, days in SPANS:
        if label == "Daily":
            continue
        day = (date(anchor.year, 1, 1).isoformat() if days is None
               else (anchor - timedelta(days=days)).isoformat())
        try:
            rates, _ = _ecb(day)
            spans[label] = rates
            cache["fx"][day] = rates
            ok += 1
        except Exception:                           # noqa: BLE001
            if cache["fx"].get(day):
                spans[label] = cache["fx"][day]
                stale = True
        time.sleep(0.3)

    print(f"  fx: {ok}/{len(SPANS) + 1} ECB snapshots (as of {latest_date})")

    out = {}
    for pair in PAIRS:
        now = _cross(latest, pair)
        if now is None:
            continue
        changes = {}
        for label, _ in SPANS:
            then = _cross(spans.get(label) or {}, pair)
            changes[label] = ((now - then) / then * 100) if then else None
        out[pair] = {"rate": now, "changes": changes, "stale": stale}
    cache["fx_date"] = latest_date
    return out


# ── Entry point ──────────────────────────────────────────────────────────

def collect(offline=False):
    cache = load_cache()
    if offline:
        print("  market: offline, using cache only")
        quotes, fx = {}, {}
        for sym, row in cache.get("quotes", {}).items():
            change = row["price"] - row["prev"]
            quotes[sym] = {"price": row["price"], "change": change,
                           "pct": (change / row["prev"] * 100) if row["prev"] else 0,
                           "stale": True}
    else:
        quotes = fetch_quotes(cache)
        fx = fetch_fx(cache)
        cache["fetched"] = datetime.now(timezone.utc).isoformat()
        save_cache(cache)

    return {"tabs": TABS, "quotes": quotes, "fx": fx, "pairs": PAIRS,
            "spans": [s for s, _ in SPANS],
            "fetched": cache.get("fetched")}
