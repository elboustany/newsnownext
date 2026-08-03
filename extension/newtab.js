import { FEEDS, TOPICS, SESSIONS } from "./feeds.js";

const CACHE_KEY = "wire:v1";
const FILTER_KEY = "wire:muted";
const PREFS_KEY = "wire:prefs";
const FRESH_MS = 30 * 60 * 1000;   // headlines under 30m get the signal colour
const STALE_MS = 5 * 60 * 1000;    // refetch if the cache is older than this
// Hold the widest window the UI offers, then narrow at render time, so
// changing the window control is instant and never needs the network.
const WINDOW_MS = 72 * 60 * 60 * 1000;
const MAX_ITEMS = 500;             // cache ceiling
const MAX_RENDER = 200;            // painted ceiling

const el = {
  wire: document.getElementById("wire"),
  state: document.getElementById("state"),
  sources: document.getElementById("sources"),
  topics: document.getElementById("topics"),
  q: document.getElementById("q"),
  sort: document.getElementById("sort"),
  window: document.getElementById("window"),
  count: document.getElementById("count"),
  clearAll: document.getElementById("clearAll"),
  clock: document.getElementById("clock"),
  clockZone: document.getElementById("clockZone"),
  sessionState: document.getElementById("sessionState"),
  status: document.getElementById("status"),
  refresh: document.getElementById("refresh")
};

let items = [];
let muted = new Set();
let prefs = { sort: "balanced", window: 24, topic: null, q: "" };

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
    render({ animate: true });
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
  render({ animate: true });
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

/* ── Filtering and ordering ──────────────────────────────────────────── */

const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

// Same word-boundary matching the generator uses, so "Oil" in the extension and
// /topics/oil.html select the same headlines.
const TOPIC_RE = new Map(
  TOPICS.map(t => [
    t.slug,
    new RegExp(`(?<![a-z0-9])(${t.keywords.map(esc).join("|")})(?![a-z0-9])`, "i")
  ])
);

function searchTerms(q) {
  // Quoted runs stay together; everything else is an AND term.
  return (q.toLowerCase().match(/"[^"]+"|\S+/g) || [])
    .map(t => t.replace(/^"|"$/g, "").trim())
    .filter(Boolean);
}

function passes(it, terms) {
  if (muted.has(it.sourceId)) return false;
  if (Date.now() - it.ts > prefs.window * 3600 * 1000) return false;
  if (prefs.topic && !TOPIC_RE.get(prefs.topic).test(it.title)) return false;
  if (terms.length) {
    const hay = `${it.title} ${it.source}`.toLowerCase();
    if (!terms.every(t => hay.includes(t))) return false;
  }
  return true;
}

// Round-robin one headline per source per pass. Without this the wire is
// whichever desk publishes most often — Yahoo pushes Reuters and Bloomberg off
// the first screen entirely, which defeats the point of merging eight sources.
function balance(list) {
  const buckets = new Map();
  for (const it of list) {
    if (!buckets.has(it.sourceId)) buckets.set(it.sourceId, []);
    buckets.get(it.sourceId).push(it);
  }
  const active = [...buckets.values()];
  for (const b of active) b.sort((a, z) => z.ts - a.ts);

  const out = [];
  while (active.length) {
    active.sort((a, z) => z[0].ts - a[0].ts);        // freshest desk leads each pass
    for (const b of active) out.push(b.shift());
    for (let i = active.length - 1; i >= 0; i--) {
      if (!active[i].length) active.splice(i, 1);
    }
  }
  return out;
}

function order(list) {
  switch (prefs.sort) {
    case "oldest":
      return [...list].sort((a, z) => a.ts - z.ts);
    case "source":
      return [...list].sort((a, z) =>
        a.source.localeCompare(z.source) || z.ts - a.ts);
    case "balanced":
      return balance(list);
    default:
      return [...list].sort((a, z) => z.ts - a.ts);
  }
}

function selection() {
  const terms = searchTerms(prefs.q);
  const kept = items.filter(it => passes(it, terms));
  return { rows: order(kept).slice(0, MAX_RENDER), matched: kept.length, terms };
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

function render({ animate = false } = {}) {
  const { rows, matched, terms } = selection();
  el.wire.setAttribute("aria-busy", "false");
  el.wire.dataset.animate = animate ? "1" : "0";
  el.wire.innerHTML = "";
  updateCount(rows.length, matched);

  if (!rows.length) {
    el.wire.appendChild(emptyState());
    return;
  }

  const frag = document.createDocumentFragment();

  if (prefs.sort === "source") {
    // Grouped: a source heading instead of session rules, which mean nothing
    // once the wire is no longer in time order.
    let current = null;
    for (const it of rows) {
      if (it.source !== current) {
        current = it.source;
        frag.appendChild(groupNode(current));
      }
      frag.appendChild(itemNode(it, terms));
    }
  } else if (prefs.sort === "balanced") {
    for (const it of rows) frag.appendChild(itemNode(it, terms));
  } else {
    // Time-ordered: drop the session rules in where the stream crosses them.
    const asc = prefs.sort === "oldest";
    const stamps = rows.map(i => i.ts);
    const rules = sessionRulesFor({
      newest: Math.max(...stamps),
      oldest: Math.min(...stamps)
    });
    if (asc) rules.reverse();

    let r = 0;
    for (const it of rows) {
      while (r < rules.length &&
             (asc ? rules[r].ms < it.ts : rules[r].ms > it.ts)) {
        frag.appendChild(ruleNode(rules[r]));
        r++;
      }
      frag.appendChild(itemNode(it, terms));
    }
  }

  el.wire.appendChild(frag);
}

function groupNode(label) {
  const div = document.createElement("div");
  div.className = "group-rule";
  div.textContent = label;
  return div;
}

function emptyState() {
  const p = document.createElement("p");
  p.className = "state";
  if (!items.length) {
    p.textContent = "Nothing on the wire yet.";
  } else if (muted.size >= FEEDS.length) {
    p.textContent = "Every source is switched off. Turn one back on above.";
  } else {
    const bits = [];
    if (prefs.q) bits.push(`“${prefs.q}”`);
    if (prefs.topic) bits.push(TOPICS.find(t => t.slug === prefs.topic).title);
    bits.push(`the last ${prefs.window}h`);
    p.textContent = `Nothing matching ${bits.join(" in ")}.`;
  }
  return p;
}

function updateCount(shown, matched) {
  const filtered = prefs.q || prefs.topic || muted.size || prefs.window !== 24;
  const capped = matched > shown ? ` (showing ${shown})` : "";
  el.count.textContent = items.length
    ? `${matched} of ${items.length} headlines${capped}`
    : "—";
  el.clearAll.hidden = !filtered;
}

// Wrap search hits so the reader can see why a headline matched.
function highlight(text, terms) {
  if (!terms.length) return document.createTextNode(text);
  const frag = document.createDocumentFragment();
  const re = new RegExp(`(${terms.map(esc).join("|")})`, "ig");
  let last = 0;
  for (const m of text.matchAll(re)) {
    if (m.index > last) frag.append(text.slice(last, m.index));
    const mark = document.createElement("mark");
    mark.textContent = m[0];
    frag.append(mark);
    last = m.index + m[0].length;
  }
  if (last < text.length) frag.append(text.slice(last));
  return frag;
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

function itemNode(it, terms = []) {
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
  a.append(highlight(it.title, terms));

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

/* ── Controls ────────────────────────────────────────────────────────── */

function chip(label, pressed, title) {
  const b = document.createElement("button");
  b.className = "chip";
  b.type = "button";
  b.textContent = label;
  b.setAttribute("aria-pressed", String(pressed));
  if (title) b.title = title;
  return b;
}

async function saveMuted() {
  await chrome.storage.local.set({ [FILTER_KEY]: [...muted] });
}

async function savePrefs() {
  await chrome.storage.local.set({ [PREFS_KEY]: prefs });
}

function renderSourceChips() {
  el.sources.innerHTML = "";
  for (const f of FEEDS) {
    const on = !muted.has(f.id);
    const b = chip(f.label, on, `Click to ${on ? "hide" : "show"} ${f.label}. ` +
                                `Double-click to show only ${f.label}.`);
    b.addEventListener("click", async (ev) => {
      if (ev.detail > 1) return;                 // let dblclick own the solo
      muted.has(f.id) ? muted.delete(f.id) : muted.add(f.id);
      await saveMuted();
      renderSourceChips();
      render();
    });
    b.addEventListener("dblclick", async () => {
      const soloed = muted.size === FEEDS.length - 1 && !muted.has(f.id);
      muted = soloed ? new Set()                 // second double-click restores
                     : new Set(FEEDS.filter(x => x.id !== f.id).map(x => x.id));
      await saveMuted();
      renderSourceChips();
      render();
    });
    el.sources.appendChild(b);
  }

  if (muted.size) {
    const all = document.createElement("button");
    all.className = "linkbtn";
    all.type = "button";
    all.textContent = "all";
    all.addEventListener("click", async () => {
      muted = new Set();
      await saveMuted();
      renderSourceChips();
      render();
    });
    el.sources.appendChild(all);
  }
}

function renderTopicChips() {
  el.topics.innerHTML = "";
  const opts = [{ slug: null, title: "All" }, ...TOPICS];
  for (const t of opts) {
    const b = chip(t.title, prefs.topic === t.slug);
    b.addEventListener("click", async () => {
      prefs.topic = prefs.topic === t.slug ? null : t.slug;
      await savePrefs();
      renderTopicChips();
      render();
    });
    el.topics.appendChild(b);
  }
}

function syncControls() {
  el.q.value = prefs.q;
  el.sort.value = prefs.sort;
  el.window.value = String(prefs.window);
  renderTopicChips();
  renderSourceChips();
}

let searchTimer;
el.q.addEventListener("input", () => {
  prefs.q = el.q.value;
  render();                                      // instant
  clearTimeout(searchTimer);                     // persist once typing settles
  searchTimer = setTimeout(savePrefs, 400);
});

el.sort.addEventListener("change", async () => {
  prefs.sort = el.sort.value;
  await savePrefs();
  render();
});

el.window.addEventListener("change", async () => {
  prefs.window = Number(el.window.value);
  await savePrefs();
  render();
});

el.clearAll.addEventListener("click", async () => {
  prefs = { ...prefs, q: "", topic: null, window: 24 };
  muted = new Set();
  await Promise.all([savePrefs(), saveMuted()]);
  syncControls();
  render();
});

el.refresh.addEventListener("click", () => loadWire({ force: true }));

document.addEventListener("keydown", (ev) => {
  const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(ev.target.tagName);
  if (ev.key === "Escape" && prefs.q) {
    prefs.q = "";
    el.q.value = "";
    el.q.blur();
    savePrefs();
    render();
    return;
  }
  if (typing || ev.metaKey || ev.ctrlKey || ev.altKey) return;
  if (ev.key === "/") { ev.preventDefault(); el.q.focus(); el.q.select(); }
  if (ev.key === "r") { ev.preventDefault(); loadWire({ force: true }); }
});

/* ── Start ───────────────────────────────────────────────────────────── */

(async function start() {
  const stored = await chrome.storage.local.get(FILTER_KEY);
  muted = new Set(Array.isArray(stored[FILTER_KEY]) ? stored[FILTER_KEY] : []);
  const saved = (await chrome.storage.local.get(PREFS_KEY))[PREFS_KEY];
  if (saved && typeof saved === "object") prefs = { ...prefs, ...saved };
  syncControls();
  await loadWire();
})();
