import { REGIONS, FEEDS, TOPICS } from "./feeds.js";

/* Renders the same region cards as the site, from the same source list.
   Fetches run inside the extension, so there is no proxy and no server.  */

const CACHE_KEY = "wire:v2";
const PREFS_KEY = "wire:prefs";
const STALE_MS = 5 * 60 * 1000;         // refetch if the cache is older
const WINDOW_MS = 72 * 60 * 60 * 1000;  // keep the widest window the UI offers
const PER_SOURCE = 12;                  // headlines per source, as on the site

const el = {
  grid: document.getElementById("grid"),
  q: document.getElementById("f-q"),
  sort: document.getElementById("f-sort"),
  window: document.getElementById("f-window"),
  regions: document.getElementById("f-regions"),
  topics: document.getElementById("f-topics"),
  count: document.getElementById("f-count"),
  clear: document.getElementById("f-clear"),
  empty: document.getElementById("f-empty"),
  status: document.getElementById("status"),
  refresh: document.getElementById("refresh"),
};

let bySource = {};                       // {source_id: [item]}
let prefs = { q: "", region: null, topic: null, sort: "newest", window: 0 };

const escRe = s => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

const TOPIC_RE = new Map(TOPICS.map(t => [
  t.slug,
  new RegExp("(?<![a-z0-9])(" + t.keywords.map(escRe).join("|") + ")(?![a-z0-9])", "i"),
]));

/* ── Fetch ───────────────────────────────────────────────────────────── */

// Strip the " - Publisher" suffix Google News appends to every headline.
// For a site-restricted query the publisher is the source label, but a broad
// query ("switzerland economy") returns whatever outlet ran it — so a Swiss
// rates story arrives as "… - Bitcoin World" and then matches the crypto
// topic. Strip it for anything via Google News; leave native feeds alone,
// where a trailing dash is usually part of the headline.
function cleanTitle(title, feed) {
  const t = title.trim().replace(/\s+/g, " ");
  if (feed.via === "Google News") {
    return t.replace(/\s+[-–—]\s+[^-–—]{2,40}$/, "").trim();
  }
  const head = escRe(feed.label.split(" ")[0]);
  return t.replace(new RegExp("\\s+[-–—]\\s+" + head + "[^-–—]*$", "i"), "").trim();
}

function parseFeed(xml, feed) {
  const doc = new DOMParser().parseFromString(xml, "text/xml");
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
      title: cleanTitle(rawTitle, feed),
      link,
      ts: Number.isFinite(ts) ? ts : Date.now(),
      source: feed.label,
      sourceId: feed.id,
      regionId: feed.regionId,
      via: feed.via || null,
    });
  }
  return out;
}

async function fetchFeed(feed) {
  const res = await fetch(feed.url, { cache: "no-cache" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return parseFeed(await res.text(), feed);
}

// Dedupe within a source only. On a page laid out by desk, two desks covering
// the same story is information, not noise.
function group(lists) {
  const out = {};
  const cutoff = Date.now() - WINDOW_MS;
  for (const list of lists) {
    for (const it of list) {
      if (it.ts < cutoff) continue;
      (out[it.sourceId] ||= []).push(it);
    }
  }
  for (const id of Object.keys(out)) {
    const seen = new Set();
    out[id] = out[id]
      .sort((a, b) => b.ts - a.ts)
      .filter(it => {
        const k = it.title.toLowerCase().replace(/[^a-z0-9]+/g, "").slice(0, 60);
        if (!k || seen.has(k)) return false;
        seen.add(k);
        return true;
      })
      .slice(0, PER_SOURCE);
  }
  return out;
}

async function load({ force = false } = {}) {
  const cached = (await chrome.storage.local.get(CACHE_KEY))[CACHE_KEY];
  if (cached?.bySource && Object.keys(cached.bySource).length) {
    bySource = cached.bySource;
    render();
    setStatus(cached.ts, cached.failed);
  } else {
    skeletons();
  }

  if (cached && Date.now() - cached.ts < STALE_MS && !force) return;

  el.refresh.disabled = true;
  const results = await Promise.allSettled(FEEDS.map(fetchFeed));
  el.refresh.disabled = false;

  const lists = [], failed = [];
  results.forEach((r, i) => {
    if (r.status === "fulfilled" && r.value.length) lists.push(r.value);
    else failed.push(FEEDS[i].label);
  });

  if (!lists.length) {
    if (!Object.keys(bySource).length) {
      el.grid.innerHTML = "";
      el.grid.setAttribute("aria-busy", "false");
      el.count.textContent =
        "No sources reachable. Check your connection, then refresh.";
    }
    setStatus(cached?.ts ?? null, failed);
    return;
  }

  bySource = group(lists);
  const ts = Date.now();
  await chrome.storage.local.set({ [CACHE_KEY]: { ts, bySource, failed } });
  render();
  setStatus(ts, failed);
}

function setStatus(ts, failed = []) {
  const when = ts
    ? new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : "never";
  const miss = failed.length ? ` · ${failed.length} unavailable` : "";
  el.status.textContent = `Updated ${when}${miss}`;
  el.status.title = failed.length ? `Not responding: ${failed.join(", ")}` : "";
}

/* ── Render ──────────────────────────────────────────────────────────── */

function skeletons() {
  el.grid.innerHTML = "";
  for (let i = 0; i < 6; i++) {
    const d = document.createElement("div");
    d.className = "skeleton";
    el.grid.appendChild(d);
  }
}

// 'Aug 3 12:23 PM' — the format the site uses.
function stamp(ts) {
  const d = new Date(ts);
  const h = d.getHours() % 12 || 12;
  const ampm = d.getHours() < 12 ? "AM" : "PM";
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${d.toLocaleString([], { month: "short" })} ${d.getDate()} ${h}:${mm} ${ampm}`;
}

function render() {
  el.grid.innerHTML = "";
  el.grid.setAttribute("aria-busy", "false");

  for (const region of REGIONS) {
    const blocks = [];

    for (const src of region.sources) {
      const rows = bySource[src.id] || [];
      if (!rows.length) continue;

      const ul = document.createElement("ul");
      ul.className = "items";
      for (const it of rows) {
        const li = document.createElement("li");
        li.dataset.item = "";
        li.dataset.src = it.source;
        li.dataset.region = region.id;

        const a = document.createElement("a");
        a.href = it.link;
        a.rel = "noreferrer";
        a.textContent = it.title;

        const time = document.createElement("time");
        time.dateTime = new Date(it.ts).toISOString();
        time.textContent = stamp(it.ts);

        li._a = a;
        li._raw = it.title;
        li._hay = (it.title + " " + it.source).toLowerCase();
        li._ts = it.ts;

        li.append(a, time);
        ul.appendChild(li);
      }

      const block = document.createElement("div");
      block.className = "src";
      block.dataset.source = src.id;
      const h3 = document.createElement("h3");
      h3.textContent = src.label;
      if (src.via) {
        const via = document.createElement("span");
        via.className = "via";
        via.textContent = `via ${src.via}`;
        h3.appendChild(via);
      }
      block.append(h3, ul);
      blocks.push(block);
    }

    if (!blocks.length) continue;

    const card = document.createElement("section");
    card.className = "card";
    card.dataset.region = region.id;

    const head = document.createElement("div");
    head.className = "card-head";
    const h2 = document.createElement("h2");
    h2.textContent = region.title;
    const count = document.createElement("span");
    count.className = "card-count";
    count.dataset.cardCount = "";
    head.append(h2, count);

    card.append(head, ...blocks);
    el.grid.appendChild(card);
  }

  reorder();
  apply();
}

/* ── Filter ──────────────────────────────────────────────────────────── */

function terms() {
  return (prefs.q.toLowerCase().match(/"[^"]+"|\S+/g) || [])
    .map(t => t.replace(/^"|"$/g, "").trim())
    .filter(Boolean);
}

function escHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// Rebuild from the raw headline each time so highlights never nest, and escape
// each slice so a headline containing < or & cannot inject markup.
function markUp(text, re) {
  if (!re) return escHtml(text);
  let out = "", last = 0, m;
  re.lastIndex = 0;
  while ((m = re.exec(text)) !== null) {
    out += escHtml(text.slice(last, m.index)) + "<mark>" + escHtml(m[0]) + "</mark>";
    last = m.index + m[0].length;
    if (m.index === re.lastIndex) re.lastIndex++;
  }
  return out + escHtml(text.slice(last));
}

function apply() {
  const t = terms();
  const re = t.length ? new RegExp("(" + t.map(escRe).join("|") + ")", "ig") : null;
  const cutoff = prefs.window ? Date.now() - prefs.window * 3600 * 1000 : 0;
  const topicRe = prefs.topic ? TOPIC_RE.get(prefs.topic) : null;

  const items = [...el.grid.querySelectorAll("[data-item]")];
  let shown = 0;

  for (const li of items) {
    let ok = true;
    if (prefs.region && li.dataset.region !== prefs.region) ok = false;
    if (ok && cutoff && li._ts < cutoff) ok = false;
    if (ok && topicRe && !topicRe.test(li._raw)) ok = false;
    if (ok && t.length) ok = t.every(x => li._hay.includes(x));
    li.hidden = !ok;
    if (ok) shown++;
    li._a.innerHTML = markUp(li._raw, ok ? re : null);
  }

  for (const block of el.grid.querySelectorAll("[data-source]")) {
    block.hidden = ![...block.querySelectorAll("[data-item]")].some(li => !li.hidden);
  }

  // Must stay `section[data-region]` — each <li> also carries data-region, so a
  // bare [data-region] selector would treat every headline as a card and hide
  // the lot, since an <li> has no [data-item] descendants.
  const cards = [...el.grid.querySelectorAll("section[data-region]")];
  for (const card of cards) {
    const live = [...card.querySelectorAll("[data-item]")]
      .filter(li => !li.hidden).length;
    card.hidden = live === 0;
    const c = card.querySelector("[data-card-count]");
    if (c) c.textContent = String(live);
  }

  const n = cards.filter(c => !c.hidden).length;
  const sections = `${n} section${n === 1 ? "" : "s"}`;
  el.count.textContent = !items.length
    ? "Loading…"
    : shown === items.length
      ? `${items.length} headlines across ${sections}`
      : `${shown} of ${items.length} headlines across ${sections}`;

  el.empty.hidden = shown > 0 || !items.length;
  el.clear.hidden = !(prefs.q || prefs.region || prefs.topic ||
                      prefs.window || prefs.sort !== "newest");
}

function reorder() {
  const asc = prefs.sort === "oldest";
  for (const ul of el.grid.querySelectorAll("ul.items")) {
    [...ul.children]
      .sort((a, b) => (asc ? a._ts - b._ts : b._ts - a._ts))
      .forEach(li => ul.appendChild(li));
  }
}

/* ── Controls ────────────────────────────────────────────────────────── */

function chip(label, value, attr, pressed) {
  const b = document.createElement("button");
  b.className = "chip";
  b.type = "button";
  b.textContent = label;
  b.setAttribute(attr, value);
  b.setAttribute("aria-pressed", String(pressed));
  return b;
}

function renderChips() {
  el.regions.innerHTML = "";
  for (const r of REGIONS) {
    const b = chip(r.title, r.id, "data-region-btn", prefs.region === r.id);
    b.addEventListener("click", () => {
      prefs.region = prefs.region === r.id ? null : r.id;
      renderChips(); apply(); save();
    });
    el.regions.appendChild(b);
  }

  el.topics.innerHTML = "";
  for (const t of TOPICS) {
    const b = chip(t.title, t.slug, "data-topic-btn", prefs.topic === t.slug);
    b.addEventListener("click", () => {
      prefs.topic = prefs.topic === t.slug ? null : t.slug;
      renderChips(); apply(); save();
    });
    el.topics.appendChild(b);
  }
}

async function save() {
  await chrome.storage.local.set({
    [PREFS_KEY]: {
      region: prefs.region, topic: prefs.topic,
      sort: prefs.sort, window: prefs.window,
    },
  });
}

let timer;
el.q.addEventListener("input", () => {
  prefs.q = el.q.value;
  apply();
  clearTimeout(timer);
  timer = setTimeout(save, 400);
});

el.sort.addEventListener("change", () => {
  prefs.sort = el.sort.value; reorder(); save();
});

el.window.addEventListener("change", () => {
  prefs.window = Number(el.window.value); apply(); save();
});

el.clear.addEventListener("click", () => {
  prefs = { q: "", region: null, topic: null, sort: "newest", window: 0 };
  el.q.value = "";
  el.sort.value = "newest";
  el.window.value = "0";
  renderChips(); reorder(); apply(); save();
});

el.refresh.addEventListener("click", () => load({ force: true }));

document.addEventListener("keydown", (ev) => {
  const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(ev.target.tagName);
  if (ev.key === "Escape" && prefs.q) {
    prefs.q = ""; el.q.value = ""; el.q.blur(); apply(); save();
    return;
  }
  if (typing || ev.metaKey || ev.ctrlKey || ev.altKey) return;
  if (ev.key === "/") { ev.preventDefault(); el.q.focus(); el.q.select(); }
  if (ev.key === "r") { ev.preventDefault(); load({ force: true }); }
});

/* ── Start ───────────────────────────────────────────────────────────── */

// Only accept values this build still understands. Preferences outlive the
// code that wrote them: an earlier version stored sort:"balanced", which is no
// longer an option, and restoring it blanks the select and silently applies a
// filter the reader never chose.
function sanitise(saved) {
  const out = { q: "", region: null, topic: null, sort: "newest", window: 0 };
  if (!saved || typeof saved !== "object") return out;
  if (["newest", "oldest"].includes(saved.sort)) out.sort = saved.sort;
  if ([0, 6, 12, 24].includes(Number(saved.window))) out.window = Number(saved.window);
  if (REGIONS.some(r => r.id === saved.region)) out.region = saved.region;
  if (TOPICS.some(t => t.slug === saved.topic)) out.topic = saved.topic;
  return out;
}

(async function start() {
  prefs = sanitise((await chrome.storage.local.get(PREFS_KEY))[PREFS_KEY]);
  el.sort.value = prefs.sort;
  el.window.value = String(prefs.window);
  renderChips();
  await load();
})();
