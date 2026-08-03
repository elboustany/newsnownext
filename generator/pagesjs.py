"""
Shared behaviour for the promo banner, podcasts, preferences and read-later.

All progressive enhancement: the pages render fully server-side and these only
add interaction. Preferences and Read Later are browser-local by design —
there is no account and nothing is uploaded.
"""

PAGES_JS = r"""
(function () {
  /* ── Ticker tabs ─────────────────────────────────────────────────── */
  var strip = document.querySelector('[data-ticker]');
  if (strip) {
    var tabs = [].slice.call(strip.querySelectorAll('[data-tab]'));
    tabs.forEach(function (t) {
      t.addEventListener('click', function () {
        tabs.forEach(function (o) {
          var on = o === t;
          o.setAttribute('aria-selected', String(on));
          var panel = document.getElementById('panel-' + o.getAttribute('data-tab'));
          if (panel) panel.hidden = !on;
        });
        try { localStorage.setItem('nnn:tab', t.getAttribute('data-tab')); } catch (e) {}
      });
    });
    try {
      var saved = localStorage.getItem('nnn:tab');
      if (saved) {
        var want = tabs.filter(function (t) { return t.getAttribute('data-tab') === saved; })[0];
        if (want) want.click();
      }
    } catch (e) {}

    // Arrow-key navigation, expected of a role="tablist".
    strip.addEventListener('keydown', function (e) {
      var i = tabs.indexOf(document.activeElement);
      if (i < 0) return;
      var next = e.key === 'ArrowRight' ? i + 1 : e.key === 'ArrowLeft' ? i - 1 : -1;
      if (next < 0 || next >= tabs.length) return;
      e.preventDefault();
      tabs[next].focus();
      tabs[next].click();
    });
  }

  /* ── Promo banner ────────────────────────────────────────────────── */
  var promo = document.getElementById('promo');
  var x = document.getElementById('promo-x');
  if (promo && x) {
    try {
      if (localStorage.getItem('nnn:promo') === 'off') promo.hidden = true;
    } catch (e) {}
    x.addEventListener('click', function () {
      promo.hidden = true;
      try { localStorage.setItem('nnn:promo', 'off'); } catch (e) {}
    });
  }

  function escHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  /* ── Podcasts ────────────────────────────────────────────────────── */
  var pf = document.querySelector('[data-pod-filters]');
  if (pf) {
    pf.hidden = false;
    var pq = document.getElementById('p-q');
    var ps = document.getElementById('p-sort');
    var pc = document.getElementById('p-count');
    var pe = document.getElementById('p-empty');
    var list = document.getElementById('pod-list');
    var pods = [].slice.call(list.querySelectorAll('[data-pod]'));

    function papply() {
      var terms = (pq.value.toLowerCase().match(/"[^"]+"|\S+/g) || [])
        .map(function (t) { return t.replace(/^"|"$/g, '').trim(); }).filter(Boolean);
      var shown = 0;
      pods.forEach(function (p) {
        var hay = p.getAttribute('data-hay');
        var ok = terms.every(function (t) { return hay.indexOf(t) > -1; });
        p.hidden = !ok;
        if (ok) shown++;
      });
      pc.textContent = shown === pods.length
        ? pods.length + ' episodes'
        : shown + ' of ' + pods.length + ' episodes';
      pe.hidden = shown > 0;
    }
    function psort() {
      var asc = ps.value === 'old';
      pods.slice().sort(function (a, b) {
        var x = +a.getAttribute('data-ts'), y = +b.getAttribute('data-ts');
        return asc ? x - y : y - x;
      }).forEach(function (p) { list.appendChild(p); });
    }
    pq.addEventListener('input', papply);
    pq.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { pq.value = ''; papply(); }
    });
    ps.addEventListener('change', psort);
    papply();
  }

  /* ── Preferences ─────────────────────────────────────────────────── */
  var prefs = document.querySelector('[data-prefs]');
  if (prefs) {
    var KEY = 'nnn:filters';
    var REGIONS = [
      ['markets', 'Markets'], ['us', 'US News'], ['uk', 'UK News'],
      ['blogs', 'Blogs'], ['china', 'China News'], ['france', 'France News'],
      ['switzerland', 'Switzerland News'], ['middleeast', 'Middle East News']
    ];
    var saved = {};
    try { saved = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) {}

    var html = '<div class="frow" style="margin:14px 0"><span class="flabel">Default region</span>' +
      '<nav class="chips" id="pref-regions">' +
      '<button class="chip" type="button" data-r="" aria-pressed="' +
        String(!saved.region) + '">All</button>';
    REGIONS.forEach(function (r) {
      html += '<button class="chip" type="button" data-r="' + r[0] + '" aria-pressed="' +
        String(saved.region === r[0]) + '">' + escHtml(r[1]) + '</button>';
    });
    html += '</nav></div><p class="fcount" id="pref-msg"></p>';
    prefs.innerHTML = html;

    var msg = document.getElementById('pref-msg');
    [].slice.call(prefs.querySelectorAll('[data-r]')).forEach(function (b) {
      b.addEventListener('click', function () {
        var v = b.getAttribute('data-r') || null;
        var s = {};
        try { s = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) {}
        s.region = v;
        try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) {}
        [].slice.call(prefs.querySelectorAll('[data-r]')).forEach(function (o) {
          o.setAttribute('aria-pressed', String((o.getAttribute('data-r') || null) === v));
        });
        msg.textContent = 'Saved. The feed will open on ' +
          (v ? b.textContent : 'all regions') + '.';
      });
    });
  }

  /* ── Read later ──────────────────────────────────────────────────── */
  var later = document.querySelector('[data-later]');
  if (later) {
    var LKEY = 'nnn:later';
    var saved2 = [];
    try { saved2 = JSON.parse(localStorage.getItem(LKEY) || '[]'); } catch (e) {}
    if (!saved2.length) {
      later.innerHTML = '<p class="empty">Nothing saved yet. ' +
        'Use the bookmark on any headline to keep it here.</p>';
    } else {
      later.innerHTML = '<ul class="items">' + saved2.map(function (it) {
        return '<li><a href="' + escHtml(it.link) + '" rel="nofollow noopener" ' +
          'target="_blank">' + escHtml(it.title) + '</a>' +
          '<time>' + escHtml(it.source || '') + '</time></li>';
      }).join('') + '</ul>';
    }
  }
})();
"""
