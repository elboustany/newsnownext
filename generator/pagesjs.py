"""
Shared behaviour for the promo banner, podcasts, preferences and read-later.

All progressive enhancement: the pages render fully server-side and these only
add interaction. Preferences and Read Later are browser-local by design -
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

  /* ── Today's Brief: collapse + read-more ────────────────────────── */
  var brief = document.querySelector('[data-brief]');
  if (brief) {
    var bBody = document.getElementById('brief-body');
    var bColl = document.getElementById('brief-collapse');
    function setBrief(open) {
      bBody.hidden = !open;
      bColl.setAttribute('aria-expanded', String(open));
      bColl.innerHTML = open ? '&#9650;' : '&#9660;';
      try { localStorage.setItem('nnn:brief', open ? 'open' : 'shut'); } catch (e) {}
    }
    bColl.addEventListener('click', function () { setBrief(bBody.hidden); });
    // Collapsed by default; only readers who opened it stay opened.
    var bSaved = null;
    try { bSaved = localStorage.getItem('nnn:brief'); } catch (e) {}
    setBrief(bSaved === 'open');
    if (bSaved === null) {
      try { localStorage.removeItem('nnn:brief'); } catch (e) {}
    }
    var bx = document.getElementById('brief-expand');
    if (bx) {
      bx.addEventListener('click', function () {
        var more = document.getElementById('brief-more');
        more.hidden = !more.hidden;
        bx.setAttribute('aria-expanded', String(!more.hidden));
        bx.innerHTML = more.hidden
          ? 'Read the full brief &darr;' : 'Show less &uarr;';
      });
    }
  }

  /* ── Back to top ─────────────────────────────────────────────────── */
  var toTop = document.getElementById('totop');
  if (toTop) {
    var ticking = false;
    window.addEventListener('scroll', function () {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () {
        toTop.hidden = window.scrollY < 600;
        ticking = false;
      });
    }, { passive: true });
    toTop.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  /* ── Contact form without a backend: compose an email ────────────── */
  var cform = document.querySelector('[data-contact-form]');
  if (cform) {
    cform.addEventListener('submit', function (e) {
      e.preventDefault();
      var f = new FormData(cform);
      var subj = '[' + (f.get('topic') || 'General') + '] Message from ' +
                 (f.get('name') || 'the site');
      var body = (f.get('message') || '') + '\n\n' +
                 (f.get('name') || '') + '\n' + (f.get('email') || '');
      location.href = 'mailto:hello@newsnownext.org?subject=' +
        encodeURIComponent(subj) + '&body=' + encodeURIComponent(body);
    });
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
                         source: b.getAttribute('data-bm-source'),
                         savedAt: Date.now() });
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
  if (prefs && window.__PREFS_META__) {
    var META = window.__PREFS_META__;
    var KEY = 'nnn:filters';
    function readP() {
      try { return JSON.parse(localStorage.getItem(KEY) || '{}'); }
      catch (e) { return {}; }
    }
    function writeP(patch) {
      var cur = readP();
      for (var k in patch) cur[k] = patch[k];
      try { localStorage.setItem(KEY, JSON.stringify(cur)); } catch (e) {}
      var msg = document.getElementById('pref-msg');
      if (msg) msg.textContent = 'Saved.';
    }
    var st = readP();
    st.pins = Array.isArray(st.pins) ? st.pins : [];
    st.hiddenSources = Array.isArray(st.hiddenSources) ? st.hiddenSources : [];
    st.follows = Array.isArray(st.follows) ? st.follows : [];

    function chipRow(id, title) {
      return '<div class="frow" style="margin:14px 0 4px">' +
        '<span class="flabel">' + title + '</span></div>' +
        '<nav class="chips" id="' + id + '"></nav>';
    }
    prefs.innerHTML =
      chipRow('pref-region', 'Default region') +
      chipRow('pref-pins', 'Favourite regions - shown first on the feed') +
      chipRow('pref-sources', 'Sources - click to hide from your feed') +
      '<div class="frow" style="margin:14px 0 4px">' +
      '<span class="flabel">Followed keywords - build your "For you" strip</span></div>' +
      '<form id="pref-kw-form" class="frow" style="gap:8px">' +
      '<input id="pref-kw" type="text" placeholder="e.g. yen, opec, nvidia" ' +
      'style="font:inherit;font-size:14px;padding:8px 12px;border:1px solid ' +
      'var(--border);border-radius:999px" autocomplete="off">' +
      '<button class="chip" type="submit">Add</button></form>' +
      '<nav class="chips" id="pref-kws" style="margin-top:8px"></nav>' +
      '<p class="fcount" id="pref-msg" style="margin-top:14px"></p>';

    function draw() {
      var reg = document.getElementById('pref-region');
      reg.innerHTML = '';
      [{ id: '', title: 'All' }].concat(META.regions).forEach(function (r) {
        var b = document.createElement('button');
        b.className = 'chip'; b.type = 'button'; b.textContent = r.title;
        b.setAttribute('aria-pressed', String((st.region || '') === r.id));
        b.addEventListener('click', function () {
          st.region = r.id || null; writeP({ region: st.region }); draw();
        });
        reg.appendChild(b);
      });

      var pins = document.getElementById('pref-pins');
      pins.innerHTML = '';
      META.regions.forEach(function (r) {
        var i = st.pins.indexOf(r.id);
        var b = document.createElement('button');
        b.className = 'chip'; b.type = 'button';
        b.textContent = (i > -1 ? (i + 1) + '. ' : '') + r.title;
        b.setAttribute('aria-pressed', String(i > -1));
        b.addEventListener('click', function () {
          var j = st.pins.indexOf(r.id);
          if (j > -1) st.pins.splice(j, 1); else st.pins.push(r.id);
          writeP({ pins: st.pins }); draw();
        });
        pins.appendChild(b);
      });

      var srcs = document.getElementById('pref-sources');
      srcs.innerHTML = '';
      META.sources.forEach(function (x) {
        var hid = st.hiddenSources.indexOf(x.id) > -1;
        var b = document.createElement('button');
        b.className = 'chip'; b.type = 'button';
        b.textContent = (hid ? '✕ ' : '') + x.label;
        b.title = x.region;
        b.setAttribute('aria-pressed', String(hid));
        b.addEventListener('click', function () {
          var j = st.hiddenSources.indexOf(x.id);
          if (j > -1) st.hiddenSources.splice(j, 1); else st.hiddenSources.push(x.id);
          writeP({ hiddenSources: st.hiddenSources }); draw();
        });
        srcs.appendChild(b);
      });

      var kws = document.getElementById('pref-kws');
      kws.innerHTML = '';
      st.follows.forEach(function (k) {
        var b = document.createElement('button');
        b.className = 'chip'; b.type = 'button';
        b.setAttribute('aria-pressed', 'true');
        b.textContent = k + ' ✕';
        b.addEventListener('click', function () {
          st.follows = st.follows.filter(function (x) { return x !== k; });
          writeP({ follows: st.follows }); draw();
        });
        kws.appendChild(b);
      });
    }
    document.getElementById('pref-kw-form').addEventListener('submit', function (e) {
      e.preventDefault();
      var v = document.getElementById('pref-kw').value.trim().toLowerCase();
      if (v && st.follows.indexOf(v) === -1 && st.follows.length < 12) {
        st.follows.push(v); writeP({ follows: st.follows });
      }
      document.getElementById('pref-kw').value = '';
      draw();
    });
    draw();
  }

  /* ── Service worker (PWA: instant open, offline fallback) ────────── */
  if ('serviceWorker' in navigator &&
      (location.protocol === 'https:' || location.hostname === 'localhost')) {
    navigator.serviceWorker.register('/sw.js').catch(function () {});
  }

  /* ── Newsletter placeholder form ─────────────────────────────────── */
  var nlp = document.querySelector('[data-nl-placeholder]');
  if (nlp) {
    nlp.addEventListener('submit', function (e) {
      e.preventDefault();
      var v = nlp.querySelector('input').value.trim();
      if (!v) return;
      try {
        var l = JSON.parse(localStorage.getItem('nnn:nl-intent') || '[]');
        if (l.indexOf(v) === -1) l.push(v);
        localStorage.setItem('nnn:nl-intent', JSON.stringify(l));
      } catch (err) {}
      nlp.outerHTML = '<div class="note"><p><strong>Noted.</strong> Sending '
        + 'starts once the list provider is connected - your address is kept '
        + 'in this browser until then.</p></div>';
    });
  }

  /* ── Read later: manage, filter, remove ──────────────────────────── */
  var later = document.querySelector('[data-later]');
  if (later) {
    var LKEY = 'nnn:later';
    function readL() {
      try { return JSON.parse(localStorage.getItem(LKEY) || '[]'); }
      catch (e) { return []; }
    }
    function writeL(l) {
      try { localStorage.setItem(LKEY, JSON.stringify(l)); } catch (e) {}
    }
    function dayLabel(ts) {
      if (!ts) return 'Earlier';
      var d = new Date(ts), now = new Date();
      var one = 86400000;
      var d0 = new Date(d.getFullYear(), d.getMonth(), d.getDate());
      var n0 = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      var diff = Math.round((n0 - d0) / one);
      if (diff === 0) return 'Today';
      if (diff === 1) return 'Yesterday';
      return d.toLocaleDateString(undefined,
        { weekday: 'long', day: 'numeric', month: 'long' });
    }
    var rlq = '', rlsrc = '', rlorder = 'new';

    function render() {
      var list = readL();
      var srcs = [];
      list.forEach(function (it) {
        if (it.source && srcs.indexOf(it.source) === -1) srcs.push(it.source);
      });
      srcs.sort();

      var shownList = list.filter(function (it) {
        if (rlsrc && it.source !== rlsrc) return false;
        if (rlq && (it.title || '').toLowerCase().indexOf(rlq) === -1) return false;
        return true;
      });
      shownList.sort(function (a, b) {
        return rlorder === 'old' ? (a.savedAt || 0) - (b.savedAt || 0)
                                 : (b.savedAt || 0) - (a.savedAt || 0);
      });

      var html = '';
      if (!list.length) {
        html = '<p class="empty">Nothing saved yet. Use the bookmark on any ' +
               'headline to keep it here.</p>';
      } else {
        html = '<div class="filters" style="margin-top:14px">' +
          '<div class="fsearch"><input id="rl-q" type="search" ' +
          'placeholder="Search saved stories…" value="' + escHtml(rlq) + '"></div>' +
          '<select id="rl-src" class="fsel"><option value="">All sources</option>' +
          srcs.map(function (x) {
            return '<option' + (x === rlsrc ? ' selected' : '') + '>' +
                   escHtml(x) + '</option>';
          }).join('') + '</select>' +
          '<select id="rl-order" class="fsel">' +
          '<option value="new"' + (rlorder === 'new' ? ' selected' : '') +
          '>Newest saved</option>' +
          '<option value="old"' + (rlorder === 'old' ? ' selected' : '') +
          '>Oldest saved</option></select>' +
          '<p class="fcount"><span>' +
          (shownList.length === list.length
            ? list.length + ' saved'
            : shownList.length + ' of ' + list.length + ' saved') +
          '</span><button class="linkbtn" id="rl-clear" type="button">' +
          'Remove all</button></p></div>';

        var day = null;
        shownList.forEach(function (it) {
          var lbl = dayLabel(it.savedAt);
          if (lbl !== day) {
            html += '<h2 class="rl-day">' + escHtml(lbl) + '</h2>';
            day = lbl;
          }
          html += '<div class="rl-item">' +
            '<a href="' + escHtml(it.link) + '" rel="nofollow noopener" ' +
            'target="_blank">' + escHtml(it.title || it.link) + '</a>' +
            '<span class="rl-src">' + escHtml(it.source || '') + '</span>' +
            '<button class="rl-x" type="button" data-rm="' +
            escHtml(it.link) + '" aria-label="Remove">&times;</button></div>';
        });
        if (!shownList.length) {
          html += '<p class="empty">No saved stories match.</p>';
        }
      }
      later.innerHTML = html;

      var q2 = document.getElementById('rl-q');
      if (q2) {
        q2.addEventListener('input', function () {
          rlq = q2.value.toLowerCase();
          var pos = q2.selectionStart;
          render();
          var nq = document.getElementById('rl-q');
          nq.focus(); nq.setSelectionRange(pos, pos);
        });
      }
      var s2 = document.getElementById('rl-src');
      if (s2) s2.addEventListener('change', function () {
        rlsrc = s2.value; render();
      });
      var o2 = document.getElementById('rl-order');
      if (o2) o2.addEventListener('change', function () {
        rlorder = o2.value; render();
      });
      var c2 = document.getElementById('rl-clear');
      if (c2) c2.addEventListener('click', function () {
        if (confirm('Remove all saved stories?')) { writeL([]); render(); }
      });
      [].slice.call(later.querySelectorAll('[data-rm]')).forEach(function (b) {
        b.addEventListener('click', function () {
          writeL(readL().filter(function (it) {
            return it.link !== b.getAttribute('data-rm');
          }));
          render();
        });
      });
    }
    render();
  }
})();
"""
