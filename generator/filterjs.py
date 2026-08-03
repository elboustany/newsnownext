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
  var regionBtns = [].slice.call(root.querySelectorAll('[data-region-btn]'));
  var topicBtns  = [].slice.call(root.querySelectorAll('[data-topic-btn]'));

  // Must stay `section[data-region]`. Each <li> also carries data-region so the
  // region filter can test it directly, and a bare [data-region] selector
  // therefore matches every headline as if it were a card — which then hides
  // all of them, because an <li> contains no [data-item] descendants.
  var cards = [].slice.call(document.querySelectorAll('section[data-region]'));
  var srcs  = [].slice.call(document.querySelectorAll('[data-source]'));
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
  });

  /* ── persistence ──────────────────────────────────────────────── */

  // Only accept values this build still understands. Preferences outlive the
  // code that wrote them, and restoring an option that no longer exists blanks
  // the control and silently applies a filter the reader never chose.
  try {
    var saved = JSON.parse(localStorage.getItem(KEY) || '{}');
    var regions = {}, topics = {};
    [].slice.call(root.querySelectorAll('[data-region-btn]')).forEach(function (b) {
      regions[b.getAttribute('data-region-btn')] = 1;
    });
    [].slice.call(root.querySelectorAll('[data-topic-btn]')).forEach(function (b) {
      topics[b.getAttribute('data-topic-btn')] = 1;
    });
    if (saved.sort === 'newest' || saved.sort === 'oldest') state.sort = saved.sort;
    if ([0, 6, 12, 24].indexOf(Number(saved.window)) > -1) state.window = Number(saved.window);
    if (regions[saved.region]) state.region = saved.region;
    if (topics[saved.topic]) state.topic = saved.topic;
    state.sessions = saved.sessions === true;
  } catch (e) {}

  function save() {
    try {
      localStorage.setItem(KEY, JSON.stringify({
        region: state.region, topic: state.topic,
        sort: state.sort, window: state.window, sessions: state.sessions
      }));
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
      if (state.region && li.getAttribute('data-region') !== state.region) ok = false;
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
    if (sessions) sessions.checked = state.sessions;
    document.body.setAttribute('data-sessions', state.sessions ? '1' : '0');
    regionBtns.forEach(function (b) {
      b.setAttribute('aria-pressed',
        String(state.region === (b.getAttribute('data-region-btn') || null)));
    });
    topicBtns.forEach(function (b) {
      b.setAttribute('aria-pressed',
        String(state.topic === (b.getAttribute('data-topic-btn') || null)));
    });
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

  regionBtns.forEach(function (b) {
    b.addEventListener('click', function () {
      var v = b.getAttribute('data-region-btn') || null;
      state.region = state.region === v ? null : v;
      syncControls(); apply(); save();
    });
  });

  topicBtns.forEach(function (b) {
    b.addEventListener('click', function () {
      var v = b.getAttribute('data-topic-btn') || null;
      state.topic = state.topic === v ? null : v;
      syncControls(); apply(); save();
    });
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

  syncControls();
  reorder();
  apply();
})();
"""
