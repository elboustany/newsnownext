import { FEEDS, SESSIONS } from "./feeds.js";

const CACHE_KEY = "wire:v1";
const FILTER_KEY = "wire:muted";
const FRESH_MS = 30 * 60 * 1000;   // headlines under 30m get the signal colour
const STALE_MS = 5 * 60 * 1000;    // refetch if the cache is older than this
const WINDOW_MS = 36 * 60 * 60 * 1000;
const MAX_ITEMS = 120;

const el = {
  wire: document.getElementById("wire"),
  state: document.getElementById("state"),
  sources: document.getElementById("sources"),
  clock: document.getElementById("clock"),
  clockZone: document.getElementById("clockZone"),
  sessionState: document.getElementById("sessionState"),
  status: document.getElementById("status"),
  refresh: document.getElementById("refresh")
};

let items = [];
let muted = new Set();

/* ── Clock and session state ─────────────────────────────────────────── */

const localZone = Intl.DateTimeFormat().resolvedOptions().timeZone || "local";
el.clockZone.textContent = localZone.split("/").pop().replace(/_/g, " ");

function tickClock() {
  el.clock.textContent = new Date().toLocaleTimeString([], { hour12: false });
}
tickClock();
setInterval(tickClock, 1000);

// Minutes that `timeZone` is offset from UTC at the given instant.
function tzOffset(date, timeZone) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone, hour12: false,
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit"
  }).formatToParts(date).reduce((a, p) => (a[p.type] = p.value, a), {});
  const asUTC = Date.UTC(
    +parts.year, +parts.month - 1, +parts.day,
    +parts.hour % 24, +parts.minute, +parts.second
  );
  return (asUTC - Math.floor(date.getTime() / 1000) * 1000) / 60000;
}

// The instant a session boundary occurs, for the exchange-local day that
// contains `ref`, optionally shifted by `dayShift` days.
function boundaryInstant(session, ref, dayShift = 0) {
  const offset = tzOffset(ref, session.tz);
  const local = new Date(ref.getTime() + offset * 60000);
  const utcMs = Date.UTC(
    local.getUTCFullYear(), local.getUTCMonth(), local.getUTCDate() + dayShift,
    session.h, session.m
  );
  return new Date(utcMs - offset * 60000);
}

function isWeekday(date, tz) {
  const d = new Intl.DateTimeFormat("en-US", { timeZone: tz, weekday: "short" })
    .format(date);
  return d !== "Sat" && d !== "Sun";
}

function renderSessionState() {
  const now = new Date();
  const markets = [
    { label: "Tokyo",  tz: "Asia/Tokyo",       open: [9, 0],  close: [15, 0] },
    { label: "London", tz: "Europe/London",    open: [8, 0],  close: [16, 30] },
    { label: "New York", tz: "America/New_York", open: [9, 30], close: [16, 0] }
  ];
  el.sessionState.innerHTML = "";
  for (const m of markets) {
    const parts = new Intl.DateTimeFormat("en-US", {
      timeZone: m.tz, hour12: false, hour: "2-digit", minute: "2-digit"
    }).formatToParts(now).reduce((a, p) => (a[p.type] = p.value, a), {});
    const mins = (+parts.hour % 24) * 60 + +parts.minute;
    const open = mins >= m.open[0] * 60 + m.open[1] &&
                 mins < m.close[0] * 60 + m.close[1] &&
                 isWeekday(now, m.tz);
    const node = document.createElement("span");
    node.className = "session" + (open ? " open" : "");
    node.textContent = m.label;
    node.title = open ? `${m.label} is open` : `${m.label} is closed`;
    el.sessionState.appendChild(node);
  }
}
renderSessionState();
setInterval(renderSessionState, 60000);

/* ── Fetching ────────────────────────────────────────────────────────── */

function cleanTitle(title, sourceLabel) {
  let t = title.trim().replace(/\s+/g, " ");
  // Google News appends " - Publisher" to every headline.
  t = t.replace(/\s+[-–—]\s+[^-–—]{2,40}$/, (m) =>
    new RegExp(sourceLabel.split(" ")[0], "i").test(m) ? "" : m);
  return t.trim();
}

function parseFeed(xmlText, feed) {
  const doc = new DOMParser().parseFromString(xmlText, "text/xml");
  if (doc.querySelector("parsererror")) throw new Error("malformed feed");

  const nodes = [...doc.querySelectorAll("item"), ...doc.querySelectorAll("entry")];
  const out = [];

  for (const n of nodes) {
    const rawTitle = n.querySelector("title")?.textContent || "";
    if (!rawTitle.trim()) continue;

    let link = n.querySelector("link")?.textContent?.trim();
    if (!link) link = n.querySelector("link")?.getAttribute("href") || "";
    if (!link) continue;

    const dateText =
      n.querySelector("pubDate")?.textContent ||
      n.querySelector("updated")?.textContent ||
      n.querySelector("published")?.textContent || "";
    const ts = Date.parse(dateText);

    out.push({
      title: cleanTitle(rawTitle, feed.label),
      link,
      ts: Number.isFinite(ts) ? ts : Date.now(),
      source: feed.label,
      sourceId: feed.id,
      via: feed.via || null
    });
  }
  return out;
}

async function fetchFeed(feed) {
  const res = await fetch(feed.url, { cache: "no-cache" });
  if (!res.ok) throw new Error(`${feed.label}: HTTP ${res.status}`);
  return parseFeed(await res.text(), feed);
}

function merge(lists) {
  const seen = new Map();
  const cutoff = Date.now() - WINDOW_MS;
  for (const list of lists) {
    for (const it of list) {
      if (it.ts < cutoff) continue;
      const key = it.title.toLowerCase().replace(/[^a-z0-9]+/g, "").slice(0, 60);
      if (!key) continue;
      const prior = seen.get(key);
      if (!prior || it.ts > prior.ts) seen.set(key, it);
    }
  }
  return [...seen.values()].sort((a, b) => b.ts - a.ts).slice(0, MAX_ITEMS);
}

async function loadWire({ force = false } = {}) {
  const cached = (await chrome.storage.local.get(CACHE_KEY))[CACHE_KEY];
  if (cached?.items?.length) {
    items = cached.items;
    render();
    setStatus(cached.ts, cached.failed);
  }

  const fresh = cached && Date.now() - cached.ts < STALE_MS;
  if (fresh && !force) return;

  el.refresh.disabled = true;
  const results = await Promise.allSettled(FEEDS.map(fetchFeed));
  el.refresh.disabled = false;

  const lists = [];
  const failed = [];
  results.forEach((r, i) => {
    if (r.status === "fulfilled") lists.push(r.value);
    else failed.push(FEEDS[i].label);
  });

  if (!lists.length) {
    if (!items.length) {
      el.state.textContent = "No feeds reachable. Check your connection, then refresh.";
      el.wire.setAttribute("aria-busy", "false");
    }
    setStatus(cached?.ts ?? null, FEEDS.map(f => f.label));
    return;
  }

  items = merge(lists);
  const ts = Date.now();
  await chrome.storage.local.set({ [CACHE_KEY]: { ts, items, failed } });
  render();
  setStatus(ts, failed);
}

function setStatus(ts, failed = []) {
  const when = ts
    ? new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false })
    : "never";
  const miss = failed.length ? ` · ${failed.length} source${failed.length > 1 ? "s" : ""} unavailable` : "";
  el.status.textContent = `Updated ${when}${miss}`;
  el.status.title = failed.length ? `Not responding: ${failed.join(", ")}` : "";
}

/* ── Rendering ───────────────────────────────────────────────────────── */

function relTime(ts) {
  const mins = Math.round((Date.now() - ts) / 60000);
  if (mins < 1) return "now";
  if (mins < 60) return `${mins}m`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  return `${Math.round(hrs / 24)}d`;
}

function sessionRulesFor(range) {
  const rules = [];
  const now = new Date();
  for (const s of SESSIONS) {
    for (const shift of [0, -1]) {
      const at = boundaryInstant(s, now, shift);
      const ms = at.getTime();
      if (ms > range.newest || ms < range.oldest) continue;
      if (!isWeekday(at, s.tz)) continue;
      rules.push({ ms, label: s.label });
    }
  }
  return rules.sort((a, b) => b.ms - a.ms);
}

function render() {
  const visible = items.filter(it => !muted.has(it.sourceId));
  el.wire.setAttribute("aria-busy", "false");
  el.wire.innerHTML = "";

  if (!visible.length) {
    const p = document.createElement("p");
    p.className = "state";
    p.textContent = items.length
      ? "Every source is switched off. Turn one back on above."
      : "Nothing on the wire yet.";
    el.wire.appendChild(p);
    return;
  }

  const rules = sessionRulesFor({
    newest: visible[0].ts,
    oldest: visible[visible.length - 1].ts
  });
  let r = 0;
  const frag = document.createDocumentFragment();

  for (const it of visible) {
    while (r < rules.length && rules[r].ms > it.ts) {
      frag.appendChild(ruleNode(rules[r]));
      r++;
    }
    frag.appendChild(itemNode(it));
  }
  el.wire.appendChild(frag);
}

function ruleNode(rule) {
  const div = document.createElement("div");
  div.className = "session-rule";
  const t = document.createElement("span");
  t.className = "t";
  t.textContent = new Date(rule.ms)
    .toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
  const l = document.createElement("span");
  l.className = "l";
  l.textContent = rule.label;
  div.append(t, l);
  return div;
}

function itemNode(it) {
  const div = document.createElement("article");
  div.className = "item" + (Date.now() - it.ts < FRESH_MS ? " fresh" : "");

  const t = document.createElement("time");
  t.className = "t";
  t.dateTime = new Date(it.ts).toISOString();
  t.textContent = relTime(it.ts);
  t.title = new Date(it.ts).toLocaleString();

  const body = document.createElement("div");
  body.className = "body";

  const a = document.createElement("a");
  a.className = "h";
  a.href = it.link;
  a.rel = "noreferrer";
  a.textContent = it.title;

  const meta = document.createElement("div");
  meta.className = "meta";
  const src = document.createElement("span");
  src.className = "src";
  src.textContent = it.source;
  meta.appendChild(src);
  if (it.via) {
    const via = document.createElement("span");
    via.className = "via";
    via.textContent = ` via ${it.via}`;
    meta.appendChild(via);
  }

  body.append(a, meta);
  div.append(t, body);
  return div;
}

/* ── Source filter ───────────────────────────────────────────────────── */

function renderChips() {
  el.sources.innerHTML = "";
  for (const f of FEEDS) {
    const b = document.createElement("button");
    b.className = "chip";
    b.type = "button";
    b.textContent = f.label;
    b.setAttribute("aria-pressed", String(!muted.has(f.id)));
    b.addEventListener("click", async () => {
      muted.has(f.id) ? muted.delete(f.id) : muted.add(f.id);
      b.setAttribute("aria-pressed", String(!muted.has(f.id)));
      await chrome.storage.local.set({ [FILTER_KEY]: [...muted] });
      render();
    });
    el.sources.appendChild(b);
  }
}

el.refresh.addEventListener("click", () => loadWire({ force: true }));

(async function start() {
  const stored = (await chrome.storage.local.get(FILTER_KEY))[FILTER_KEY];
  muted = new Set(Array.isArray(stored) ? stored : []);
  renderChips();
  await loadWire();
})();
