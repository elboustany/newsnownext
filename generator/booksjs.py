"""
Client-side filtering for the books page, and the ticker tab switcher.

Both are progressive enhancement over server-rendered HTML: every book and
every quote is already in the page, so a crawler and a no-JavaScript reader
see the full content. These only hide, reorder and toggle.
"""

BOOKS_JS = r"""
(function () {
  /* ── Books ───────────────────────────────────────────────────────── */
  var root = document.querySelector('[data-book-filters]');
  if (!root) return;
  root.hidden = false;

  var q = root.querySelector('#b-q');
  var sort = root.querySelector('#b-sort');
  var count = root.querySelector('#b-count');
  var clear = root.querySelector('#b-clear');
  var chips = [].slice.call(root.querySelectorAll('[data-book-cat]'));
  var grid = document.getElementById('book-grid');
  var empty = document.getElementById('b-empty');
  var books = [].slice.call(grid.querySelectorAll('[data-book]'));
  var shelves = [].slice.call(grid.querySelectorAll('[data-shelf]'));
  var sequence = [].slice.call(grid.children);   // shelves + cards, curated order
  var cat = null;

  books.forEach(function (b) {
    b._title = b.querySelector('h3').textContent;
    b._hay = (b._title + ' ' + b.querySelector('.byline').textContent).toLowerCase();
    b._year = +b.getAttribute('data-year');
    b._h3 = b.querySelector('h3');
  });

  function esc(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
  function escHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
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

  function apply() {
    var terms = (q.value.toLowerCase().match(/"[^"]+"|\S+/g) || [])
      .map(function (t) { return t.replace(/^"|"$/g, '').trim(); })
      .filter(Boolean);
    var re = terms.length ? new RegExp('(' + terms.map(esc).join('|') + ')', 'ig') : null;
    var shown = 0;

    books.forEach(function (b) {
      var ok = (!cat || b.getAttribute('data-cat') === cat) &&
               terms.every(function (t) { return b._hay.indexOf(t) > -1; });
      b.hidden = !ok;
      if (ok) shown++;
      b._h3.innerHTML = markUp(b._title, ok ? re : null);
    });

    var shelved = sort.value === 'az';
    shelves.forEach(function (h) {
      if (!shelved) { h.hidden = true; return; }
      var any = false, n = h.nextElementSibling;
      while (n && !n.hasAttribute('data-shelf')) {
        if (n.hasAttribute('data-book') && !n.hidden) { any = true; break; }
        n = n.nextElementSibling;
      }
      h.hidden = !any;
    });

    count.textContent = shown === books.length
      ? books.length + ' books'
      : shown + ' of ' + books.length + ' books';
    empty.hidden = shown > 0;
    clear.hidden = !(q.value || cat || sort.value !== 'az');
  }

  function reorder() {
    var mode = sort.value;
    if (mode === 'az') {
      // The default view is curated shelves, not a flat A-Z wall: restore
      // the exact server-rendered sequence, headers included.
      sequence.forEach(function (el) { grid.appendChild(el); });
      return;
    }
    books.slice().sort(function (a, b) {
      if (mode === 'new') return b._year - a._year || a._title.localeCompare(b._title);
      return a._year - b._year || a._title.localeCompare(b._title);
    }).forEach(function (b) { grid.appendChild(b); });
  }

  q.addEventListener('input', apply);
  q.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { q.value = ''; apply(); }
  });
  sort.addEventListener('change', function () { reorder(); apply(); });
  chips.forEach(function (c) {
    c.addEventListener('click', function () {
      var v = c.getAttribute('data-book-cat');
      cat = cat === v ? null : v;
      chips.forEach(function (o) {
        o.setAttribute('aria-pressed',
          String(o.getAttribute('data-book-cat') === cat));
      });
      apply();
    });
  });
  clear.addEventListener('click', function () {
    q.value = ''; cat = null; sort.value = 'az';
    chips.forEach(function (o) { o.setAttribute('aria-pressed', 'false'); });
    reorder(); apply();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && e.target !== q &&
        !/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) {
      e.preventDefault(); q.focus(); q.select();
    }
  });

  apply();
})();
"""
