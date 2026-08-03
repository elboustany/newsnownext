"""
Client-side filtering and sorting for the region cards.

Progressive enhancement, deliberately: every headline is already in the HTML
the server sent, so a crawler sees the full page and a reader with no
JavaScript still gets the whole wire. This only hides and reorders rows that
are already there.

The primary controls are search, region and order. Everything else — topics,
time window, session markers — sits inside a collapsed <details>, because the
main view should look like the site people already know.
"""

FILTER_JS = r"""
(function () {
  var root = document.querySelector('[data-filters]');
  if (!root) return;
  root.hidden = false;

  var q        = root.querySelector('#f-q');
  var sortSel  = root.querySelector('#f-sort');
  var winSel   = root.querySelector('#f-window');
  var sessions = root.querySelector('#f-sessions');
  var countEl  = root.querySelector('#f-count');
  var clearBtn = root.querySelector('#f-clear');
  var regionSel = root.querySelector('#f-region');
  var topicSel  = root.querySelector('#f-topic');

  // Must stay `section[data-region]`. Each <li> also carries data-region so the
  // region filter can test it directly, and a bare [data-region] selector
  // therefore matches every headline as if it were a card — which then hides
  // all of them, because an <li> contains no [data-item] descendants.
  var cards = [].slice.call(document.querySelectorAll('section[data-region]'));
  // .src scope matters: bookmark buttons also carry data-* attributes, and
  // a bare attribute selector once matched 247 buttons and crashed apply().
  var srcs  = [].slice.call(document.querySelectorAll('.src[data-source]'));
  var items = [].slice.call(document.querySelectorAll('[data-item]'));

  var TOPICS = window.__TOPICS__ || {};
  var state = { q: '', region: null, topic: null, sort: 'newest', window: 0, sessions: false };
  var KEY = 'nnn:filters';

  items.forEach(function (li) {
    var a = li.querySelector('a');
    li._a = a;
    li._raw = a.textContent;
    li._hay = (a.textContent + ' ' + (li.getAttribute('data-src') || '')).toLowerCase();
    li._ts = +li.getAttribute('data-ts') || 0;
    var block = li.closest('[data-source]');
    li._sid = block ? block.getAttribute('data-source') : '';
  });

  /* ── persistence ──────────────────────────────────────────────── */

  // Only accept values this build still understands. Preferences outlive the
  // code that wrote them, and restoring an option that no longer exists blanks
  // the control and silently applies a filter the reader never chose.
  try {
    var saved = JSON.parse(localStorage.getItem(KEY) || '{}');
    var regions = {}, topics = {};
    [].slice.call(regionSel.options).forEach(function (o) { if (o.value) regions[o.value] = 1; });
    [].slice.call(topicSel.options).forEach(function (o) { if (o.value) topics[o.value] = 1; });
    if (saved.sort === 'newest' || saved.sort === 'oldest') state.sort = saved.sort;
    if ([0, 6, 12, 24].indexOf(Number(saved.window)) > -1) state.window = Number(saved.window);
    if (regions[saved.region]) state.region = saved.region;
    if (topics[saved.topic]) state.topic = saved.topic;
    state.sessions = saved.sessions === true;
    state.hiddenSources = Array.isArray(saved.hiddenSources)
      ? saved.hiddenSources.filter(function (x) { return typeof x === 'string'; })
      : [];
    state.pins = Array.isArray(saved.pins)
      ? saved.pins.filter(function (x) { return typeof x === 'string'; })
      : [];
    state.follows = Array.isArray(saved.follows)
      ? saved.follows.filter(function (x) { return typeof x === 'string'; })
      : [];
  } catch (e) {}

  // Deep link: /?q=yen pre-fills the search. Used by the assistant and by
  // the WebSite SearchAction schema; never persisted.
  try {
    var qs = new URLSearchParams(location.search).get('q');
    if (qs) state.q = qs;
  } catch (e) {}

  function save() {
    // Merge, never overwrite: the preferences page stores pins, hidden
    // sources and followed keywords under the same key.
    try {
      var cur = JSON.parse(localStorage.getItem(KEY) || '{}');
      cur.region = state.region; cur.topic = state.topic;
      cur.sort = state.sort; cur.window = state.window;
      cur.sessions = state.sessions;
      localStorage.setItem(KEY, JSON.stringify(cur));
    } catch (e) {}
  }

  /* ── matching ─────────────────────────────────────────────────── */

  function esc(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

  function terms() {
    return (state.q.toLowerCase().match(/"[^"]+"|\S+/g) || [])
      .map(function (t) { return t.replace(/^"|"$/g, '').trim(); })
      .filter(Boolean);
  }

  function escHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // Rebuild from the raw headline every time so highlights never nest, and
  // escape each slice so a headline containing < or & cannot inject markup.
  function markUp(text, re) {
    if (!re) return escHtml(text);
    var out = '', last = 0, m;
    re.lastIndex = 0;
    while ((m = re.exec(text)) !== null) {
      out += escHtml(text.slice(last, m.index)) + '<mark>' + escHtml(m[0]) + '</mark>';
      last = m.index + m[0].length;
      if (m.index === re.lastIndex) re.lastIndex++;
    }
    return out + escHtml(text.slice(last));
  }

  function topicHit(li) {
    if (!state.topic) return true;
    var re = TOPICS[state.topic];
    if (!re) return true;
    return new RegExp(re, 'i').test(li._raw);
  }

  /* ── apply ────────────────────────────────────────────────────── */

  function apply() {
    var t = terms();
    var re = t.length ? new RegExp('(' + t.map(esc).join('|') + ')', 'ig') : null;
    var cutoff = state.window ? Date.now() - state.window * 3600 * 1000 : 0;
    var shown = 0;

    items.forEach(function (li) {
      var ok = true;
      if (state.hiddenSources.length &&
          state.hiddenSources.indexOf(li._sid) > -1) ok = false;
      if (ok && state.region && li.getAttribute('data-region') !== state.region) ok = false;
      if (ok && cutoff && li._ts * 1000 < cutoff) ok = false;
      if (ok && !topicHit(li)) ok = false;
      if (ok && t.length) {
        for (var i = 0; i < t.length; i++) {
          if (li._hay.indexOf(t[i]) === -1) { ok = false; break; }
        }
      }
      li.hidden = !ok;
      if (ok) shown++;
      li._a.innerHTML = markUp(li._raw, ok ? re : null);
    });

    // A source block with nothing left in it is noise; so is an empty card.
    srcs.forEach(function (block) {
      var list = block.querySelector('ul');
      var any = [].slice.call(list.children).some(function (li) { return !li.hidden; });
      block.hidden = !any;
    });

    cards.forEach(function (card) {
      var live = [].slice.call(card.querySelectorAll('[data-item]'))
        .filter(function (li) { return !li.hidden; }).length;
      card.hidden = live === 0;
      var c = card.querySelector('[data-card-count]');
      if (c) c.textContent = live;
    });

    var n = cards.filter(function (c) { return !c.hidden; }).length;
    var sections = n + (n === 1 ? ' section' : ' sections');
    countEl.textContent = shown === items.length
      ? items.length + ' headlines across ' + sections
      : shown + ' of ' + items.length + ' headlines across ' + sections;

    var dirty = state.q || state.region || state.topic ||
                state.window || state.sort !== 'newest';
    clearBtn.hidden = !dirty;

    var empty = document.getElementById('f-empty');
    if (empty) empty.hidden = shown > 0;
  }

  function reorder() {
    var asc = state.sort === 'oldest';
    srcs.forEach(function (block) {
      var list = block.querySelector('ul');
      [].slice.call(list.children)
        .sort(function (a, b) { return asc ? a._ts - b._ts : b._ts - a._ts; })
        .forEach(function (li) { list.appendChild(li); });
    });
  }

  /* ── wiring ───────────────────────────────────────────────────── */

  function syncControls() {
    q.value = state.q;
    sortSel.value = state.sort;
    if (winSel) winSel.value = String(state.window);
    regionSel.value = state.region || '';
    topicSel.value = state.topic || '';
  }

  var timer;
  q.addEventListener('input', function () {
    state.q = q.value;
    apply();
    clearTimeout(timer);
    timer = setTimeout(save, 400);
  });
  q.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { state.q = ''; q.value = ''; apply(); save(); }
  });

  sortSel.addEventListener('change', function () {
    state.sort = sortSel.value; reorder(); save();
  });

  if (winSel) winSel.addEventListener('change', function () {
    state.window = Number(winSel.value); apply(); save();
  });

  if (sessions) sessions.addEventListener('change', function () {
    state.sessions = sessions.checked;
    document.body.setAttribute('data-sessions', state.sessions ? '1' : '0');
    save();
  });

  regionSel.addEventListener('change', function () {
    state.region = regionSel.value || null; apply(); save();
  });
  topicSel.addEventListener('change', function () {
    state.topic = topicSel.value || null; apply(); save();
  });

  clearBtn.addEventListener('click', function () {
    state.q = ''; state.region = null; state.topic = null;
    state.sort = 'newest'; state.window = 0;
    syncControls(); reorder(); apply(); save();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && e.target !== q && !/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) {
      e.preventDefault(); q.focus(); q.select();
    }
  });

  // Favourite regions float to the top of the grid, in the order pinned.
  if (state.pins.length) {
    var grid = document.querySelector('.grid');
    if (grid) {
      state.pins.slice().reverse().forEach(function (id) {
        var card = grid.querySelector('section[data-region="' + id + '"]');
        if (card) grid.insertBefore(card, grid.firstChild);
      });
    }
  }

  // "For you": followed keywords matched against the whole wire, hottest
  // first, with a badge when the trending engine shows desk consensus.
  (function () {
    var box = document.getElementById('foryou');
    if (!box || !state.follows.length) return;
    var res = state.follows.map(function (kw) {
      return { kw: kw, re: new RegExp('(?<![a-z0-9])' + esc(kw) + '(?![a-z0-9])', 'i') };
    });
    var hot = {};
    [].slice.call(document.querySelectorAll(
      '[data-trend-group="all"] .tcard')).forEach(function (c) {
      var a = c.querySelector('.thl');
      var m = c.querySelector('.tmeta');
      if (a && m && /desks/.test(m.textContent)) hot[a.getAttribute('href')] = true;
    });
    var seen = {}, matches = [];
    items.forEach(function (li) {
      if (state.hiddenSources.indexOf(li._sid) > -1) return;
      for (var i = 0; i < res.length; i++) {
        if (res[i].re.test(li._raw)) {
          var href = li._a.getAttribute('href');
          if (seen[href]) return;
          seen[href] = true;
          matches.push({ li: li, href: href });
          return;
        }
      }
    });
    if (!matches.length) return;
    matches.sort(function (a, b) { return b.li._ts - a.li._ts; });
    var html = '<h2>For you <span class="fy-kw">' +
      state.follows.map(escHtml).join(' · ') + '</span></h2><ul>';
    matches.slice(0, 6).forEach(function (m) {
      html += '<li><a href="' + m.href + '" rel="nofollow noopener" ' +
        'target="_blank">' + escHtml(m.li._raw) + '</a>' +
        '<span class="fy-src">' + escHtml(m.li.getAttribute('data-src') || '') +
        '</span>' + (hot[m.href] ? '<span class="fy-hot">desks agree</span>' : '') +
        '</li>';
    });
    html += '</ul><a class="linkbtn fy-edit" href="/preferences/">Edit keywords</a>';
    box.innerHTML = html;
    box.hidden = false;
  })();

  syncControls();
  reorder();
  apply();
})();
"""
