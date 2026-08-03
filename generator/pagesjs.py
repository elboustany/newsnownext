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

  /* ── Nav dropdowns (also the clock chip) ─────────────────────────── */
  var menus = [].slice.call(document.querySelectorAll('[data-menu]'));
  function closeMenus(except) {
    menus.forEach(function (m) {
      if (m === except) return;
      var b = m.querySelector('.menu-btn'), pop = m.querySelector('.menu-pop');
      if (b && pop) { b.setAttribute('aria-expanded', 'false'); pop.hidden = true; }
    });
  }
  menus.forEach(function (m) {
    var b = m.querySelector('.menu-btn'), pop = m.querySelector('.menu-pop');
    if (!b || !pop) return;
    b.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = pop.hidden;
      closeMenus(m);
      pop.hidden = !open;
      b.setAttribute('aria-expanded', String(open));
    });
  });
  document.addEventListener('click', function () { closeMenus(null); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeMenus(null);
  });

  /* ── Market clocks ───────────────────────────────────────────────── */
  var clockbox = document.querySelector('[data-clocks]');
  if (clockbox) {
    var rows = [].slice.call(clockbox.querySelectorAll('.clock-row'));
    var mini = clockbox.querySelector('[data-clock-mini]');
    function fmt(tz) {
      return new Intl.DateTimeFormat('en-GB', {
        timeZone: tz, hour: '2-digit', minute: '2-digit', hour12: false
      }).format(new Date());
    }
    function marketOpen(tz, o, c) {
      var parts = new Intl.DateTimeFormat('en-US', {
        timeZone: tz, hour: '2-digit', minute: '2-digit',
        hour12: false, weekday: 'short'
      }).formatToParts(new Date()).reduce(function (a, p) {
        a[p.type] = p.value; return a;
      }, {});
      if (parts.weekday === 'Sat' || parts.weekday === 'Sun') return false;
      var mins = (+parts.hour % 24) * 60 + (+parts.minute);
      return mins >= o && mins < c;
    }
    function tick() {
      rows.forEach(function (r) {
        var tz = r.getAttribute('data-tz');
        r.querySelector('.ctime').textContent = fmt(tz);
        r.classList.toggle('open',
          marketOpen(tz, +r.getAttribute('data-open'), +r.getAttribute('data-close')));
      });
      if (mini && rows[0]) mini.textContent = 'NY ' + fmt(rows[0].getAttribute('data-tz'));
    }
    tick();
    setInterval(tick, 30000);
  }

  /* ── Economic calendar ───────────────────────────────────────────── */
  var evRoot = document.querySelector('[data-ev-filters]');
  if (evRoot) {
    var evs = [].slice.call(document.querySelectorAll('[data-ev]'));
    var months = [].slice.call(document.querySelectorAll('.ev-month'));
    var evChips = [].slice.call(evRoot.querySelectorAll('[data-ev-chip]'));
    var evCount = document.getElementById('ev-count-all');

    // Countdown chips, computed from the UTC instant baked into each row.
    evs.forEach(function (e) {
      var t = e.getAttribute('data-utc');
      var when = new Date(Date.UTC(+t.slice(0, 4), +t.slice(4, 6) - 1, +t.slice(6, 8),
                                   +t.slice(9, 11), +t.slice(11, 13)));
      var days = Math.floor((when - Date.now()) / 86400000);
      var label = days < 0 ? '' : days === 0 ? 'Today'
                : days === 1 ? 'Tomorrow' : 'In ' + days + ' days';
      e.querySelector('[data-count]').textContent = label;
    });

    function evApply(cat) {
      var shown = 0;
      evs.forEach(function (e) {
        var ok = cat === 'all' || e.getAttribute('data-cat') === cat;
        e.hidden = !ok;
        if (ok) shown++;
      });
      // hide month headings with nothing under them
      months.forEach(function (m) {
        var any = false, n = m.nextElementSibling;
        while (n && !n.classList.contains('ev-month')) {
          if (n.hasAttribute('data-ev') && !n.hidden) { any = true; break; }
          n = n.nextElementSibling;
        }
        m.hidden = !any;
      });
      evCount.textContent = shown + ' upcoming event' + (shown === 1 ? '' : 's');
    }
    evChips.forEach(function (c) {
      c.addEventListener('click', function () {
        evChips.forEach(function (o) { o.setAttribute('aria-pressed', String(o === c)); });
        evApply(c.getAttribute('data-ev-chip'));
      });
    });
    evApply('all');

    // Add-to-calendar: build a one-event .ics in the browser.
    [].slice.call(document.querySelectorAll('[data-ics]')).forEach(function (b) {
      b.addEventListener('click', function () {
        var row = b.closest('[data-ev]');
        var t = row.getAttribute('data-utc');
        var end = new Date(Date.UTC(+t.slice(0, 4), +t.slice(4, 6) - 1, +t.slice(6, 8),
                                    +t.slice(9, 11), +t.slice(11, 13)) + 3600000);
        var pad = function (n) { return String(n).padStart(2, '0'); };
        var dtend = end.getUTCFullYear() + pad(end.getUTCMonth() + 1) +
                    pad(end.getUTCDate()) + 'T' + pad(end.getUTCHours()) +
                    pad(end.getUTCMinutes()) + '00Z';
        var name = b.getAttribute('data-name');
        var ics = ['BEGIN:VCALENDAR', 'VERSION:2.0',
                   'PRODID:-//NewsNowNext//Economic Calendar//EN', 'BEGIN:VEVENT',
                   'UID:' + t + '-' + name.replace(/\W+/g, '') + '@newsnownext.org',
                   'DTSTAMP:' + t, 'DTSTART:' + t, 'DTEND:' + dtend,
                   'SUMMARY:' + name.replace(/,/g, '\\,'),
                   'DESCRIPTION:' + b.getAttribute('data-note').replace(/,/g, '\\,'),
                   'END:VEVENT', 'END:VCALENDAR'].join('\r\n');
        var a = document.createElement('a');
        a.href = URL.createObjectURL(new Blob([ics], { type: 'text/calendar' }));
        a.download = name.toLowerCase().replace(/\W+/g, '-') + '.ics';
        document.body.appendChild(a);
        a.click();
        setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
      });
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

  /* ── Ask AI ──────────────────────────────────────────────────────── */
  var fab = document.getElementById('ai-fab');
  var panel = document.getElementById('ai-panel');
  if (fab && panel) {
    var aiq = document.getElementById('ai-q');
    function toggle(open) {
      panel.hidden = !open;
      fab.setAttribute('aria-expanded', String(open));
      if (open) aiq.focus();
    }
    fab.addEventListener('click', function () { toggle(panel.hidden); });
    document.getElementById('ai-x').addEventListener('click', function () { toggle(false); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !panel.hidden) toggle(false);
    });

    // On the feed, run the query through the live filter; elsewhere, carry it
    // to the feed as /?q=…
    function ask(q) {
      q = q.trim();
      if (!q) return;
      var wire = document.querySelector('[data-filters] #f-q');
      if (wire) {
        wire.value = q;
        wire.dispatchEvent(new Event('input'));
        toggle(false);
        wire.scrollIntoView({ block: 'center', behavior: 'smooth' });
      } else {
        location.href = '/?q=' + encodeURIComponent(q);
      }
    }
    document.getElementById('ai-form').addEventListener('submit', function (e) {
      e.preventDefault();
      ask(aiq.value);
    });
    [].slice.call(document.querySelectorAll('[data-ai-q]')).forEach(function (b) {
      b.addEventListener('click', function () { ask(b.getAttribute('data-ai-q')); });
    });
  }

  /* ── Trending ────────────────────────────────────────────────────── */
  var trend = document.querySelector('[data-trend]');
  if (trend) {
    var tChips = [].slice.call(trend.querySelectorAll('[data-trend-chip]'));
    var tGroups = [].slice.call(trend.querySelectorAll('[data-trend-group]'));
    tChips.forEach(function (c) {
      c.addEventListener('click', function () {
        var v = c.getAttribute('data-trend-chip');
        tChips.forEach(function (o) {
          o.setAttribute('aria-pressed', String(o === c));
        });
        tGroups.forEach(function (g) {
          g.hidden = g.getAttribute('data-trend-group') !== v;
        });
      });
    });
    var coll = trend.querySelector('.tcollapse');
    var body = trend.querySelector('.trend-body');
    function setOpen(open) {
      body.hidden = !open;
      coll.setAttribute('aria-expanded', String(open));
      coll.innerHTML = open ? '&#9650;' : '&#9660;';
      try { localStorage.setItem('nnn:trend', open ? 'open' : 'shut'); } catch (e) {}
    }
    coll.addEventListener('click', function () { setOpen(body.hidden); });
    try {
      if (localStorage.getItem('nnn:trend') === 'shut') setOpen(false);
    } catch (e) {}
  }

  /* ── Read-later bookmarks ────────────────────────────────────────── */
  var bms = [].slice.call(document.querySelectorAll('[data-bm]'));
  if (bms.length) {
    var BKEY = 'nnn:later';
    function readList() {
      try { return JSON.parse(localStorage.getItem(BKEY) || '[]'); }
      catch (e) { return []; }
    }
    function writeList(l) {
      try { localStorage.setItem(BKEY, JSON.stringify(l)); } catch (e) {}
    }
    var have = {};
    readList().forEach(function (it) { have[it.link] = true; });
    bms.forEach(function (b) {
      var link = b.getAttribute('data-link');
      b.setAttribute('aria-pressed', String(!!have[link]));
      b.addEventListener('click', function () {
        var list = readList();
        var idx = list.findIndex(function (it) { return it.link === link; });
        if (idx > -1) {
          list.splice(idx, 1);
          b.setAttribute('aria-pressed', 'false');
        } else {
          list.unshift({ title: b.getAttribute('data-title'), link: link,
                         source: b.getAttribute('data-source') });
          b.setAttribute('aria-pressed', 'true');
        }
        writeList(list);
      });
    });
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
