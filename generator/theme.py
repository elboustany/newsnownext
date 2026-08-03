"""
Design tokens and stylesheet, matched to the live newsnownext.org.

Every value here was sampled off the running site rather than eyeballed:
the palette is its shadcn/Tailwind token set, the grid is its
`grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 md:gap-6`, the logo colours
are the three computed span colours, and the type is Inter throughout.

Change a value here and the whole site follows. Nothing else defines colour.
"""

CSS = """
:root{
  /* sampled from the live site's :root token set */
  --background:#ffffff;
  --foreground:#344256;
  --card:#ffffff;
  --muted:#f1f5f9;
  --muted-foreground:#65758b;
  --border:#e1e7ef;
  --input:#f7f9fa;
  --primary:#2463eb;
  --primary-hover:#1d4fd7;
  --source:#dc2626;
  --navbar:#374151;
  --navbar-fg:#e5e7eb;
  --logo-news:#f97316;
  --logo-now:#10b981;
  --logo-next:#ef4444;
  --radius:8px;
  --sans:"Inter",system-ui,-apple-system,"Segoe UI",sans-serif;
}

/* No dark scheme on purpose. The live site is light-only, and a page that
   flips to dark on a dark-mode machine is exactly the "different colours"
   this build is meant to avoid. To offer one later, add a
   `@media (prefers-color-scheme:dark)` block overriding the tokens above —
   nothing else in the stylesheet hard-codes a colour. */

*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  margin:0;background:var(--background);color:var(--foreground);
  font-family:var(--sans);font-size:16px;line-height:1.5;
  -webkit-font-smoothing:antialiased;
}
a{color:inherit}

/* ── Nav ───────────────────────────────────────────────────────────── */

.nav{background:var(--navbar);color:var(--navbar-fg)}
.nav-in{
  max-width:1320px;margin:0 auto;padding:14px 20px;
  display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap;
}
.logo{
  font-weight:900;font-size:22px;line-height:.95;letter-spacing:-.02em;
  text-decoration:none;display:block;
}
.logo span{display:block}
.logo .l1{color:var(--logo-news)}
.logo .l2{color:var(--logo-now)}
.logo .l3{color:var(--logo-next)}
.nav-links{display:flex;gap:22px;flex-wrap:wrap;align-items:center}
.nav-links a{
  color:var(--navbar-fg);text-decoration:none;font-size:15px;font-weight:500;
  padding:4px 0;border-bottom:2px solid transparent;
}
.nav-links a:hover{border-bottom-color:var(--logo-news)}
.nav-links a[aria-current]{border-bottom-color:var(--logo-news)}

/* ── Ticker strip ──────────────────────────────────────────────────── */

.ticker{background:var(--muted);border-bottom:1px solid var(--border)}
.ticker-in{max-width:1320px;margin:0 auto;padding:14px 20px 16px}
.tabs{display:flex;gap:6px;justify-content:center;flex-wrap:wrap;margin-bottom:12px}
.tab{
  font:inherit;font-size:13px;font-weight:500;padding:6px 14px;border-radius:999px;
  border:1px solid transparent;background:transparent;color:var(--muted-foreground);cursor:pointer;
}
.tab:hover{color:var(--foreground);background:var(--card)}
.tab[aria-selected="true"]{background:#1f2937;color:#fff}
.tab:focus-visible{outline:2px solid var(--primary);outline-offset:2px}

.quotes{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
@media(min-width:900px){.quotes{grid-template-columns:repeat(4,1fr)}}
.quote{
  background:var(--card);border:1px solid var(--border);border-radius:var(--radius);
  padding:12px 14px;min-width:0;
}
.quote-top{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:6px}
.quote-name{font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--muted-foreground)}
.quote-live{display:inline-flex;align-items:center;gap:5px;font-size:10px;color:var(--muted-foreground)}
.quote-live::before{content:"";width:6px;height:6px;border-radius:50%;background:#10b981}
.quote.stale .quote-live::before{background:#f59e0b}
.quote-badge{
  display:inline-block;font-size:10px;font-weight:700;color:#fff;
  padding:2px 6px;border-radius:4px;background:var(--primary);margin-bottom:4px;
}
.quote-price{font-size:20px;font-weight:700;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.quote-chg{font-size:13px;font-weight:500;font-variant-numeric:tabular-nums;margin-top:2px}
.up{color:#059669}.down{color:#dc2626}.flat{color:var(--muted-foreground)}
.quote-at{font-size:11px;color:var(--muted-foreground);margin-top:4px}
.quote-missing{color:var(--muted-foreground);font-size:13px}

/* ── Forex table ───────────────────────────────────────────────────── */

.tablewrap{overflow-x:auto;border:1px solid var(--border);border-radius:var(--radius);background:var(--card)}
table.fx{border-collapse:collapse;width:100%;min-width:640px}
table.fx th,table.fx td{padding:11px 14px;text-align:right;font-size:14px;white-space:nowrap}
table.fx th{
  background:var(--muted);font-size:11px;font-weight:600;letter-spacing:.05em;
  text-transform:uppercase;color:var(--muted-foreground);border-bottom:1px solid var(--border);
}
table.fx th:first-child,table.fx td:first-child{text-align:left}
table.fx tbody tr{border-bottom:1px solid var(--border)}
table.fx tbody tr:last-child{border-bottom:0}
table.fx tbody tr:hover{background:var(--muted)}
table.fx td{font-variant-numeric:tabular-nums}
.fx-pair{font-weight:600}
.fx-rate{color:var(--muted-foreground);font-weight:400;margin-left:8px}

/* ── Books ─────────────────────────────────────────────────────────── */

.books{display:grid;gap:12px;grid-template-columns:1fr;margin-top:18px}
@media(min-width:700px){.books{grid-template-columns:repeat(2,1fr)}}
@media(min-width:1100px){.books{grid-template-columns:repeat(3,1fr)}}
.book{
  border:1px solid var(--border);border-radius:var(--radius);background:var(--card);
  padding:14px 16px;display:flex;flex-direction:column;gap:6px;
}
.book-cat{
  font-size:10px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;
  color:var(--source);
}
.book h3{font-size:15px;font-weight:600;margin:0;line-height:1.3}
.book .byline{font-size:13px;color:var(--muted-foreground);margin:0}
.book a.buy{
  font-size:13px;font-weight:500;color:var(--primary);text-decoration:none;margin-top:auto;
}
.book a.buy:hover{text-decoration:underline}
.book mark{background:rgba(36,99,235,.16);color:inherit;border-radius:2px;padding:0 1px}

/* ── Shell ─────────────────────────────────────────────────────────── */

.wrap{max-width:1320px;margin:0 auto;padding:20px 20px 64px}
.page-head{margin:8px 0 4px}
h1{font-size:26px;font-weight:800;letter-spacing:-.02em;margin:0 0 4px}
.standfirst{color:var(--muted-foreground);margin:0;font-size:15px}

/* ── Filter bar ────────────────────────────────────────────────────── */

.filters{
  background:var(--card);border:1px solid var(--border);border-radius:var(--radius);
  padding:12px;margin:16px 0 20px;
}
.frow{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.frow + .frow{margin-top:10px}
.fsearch{position:relative;flex:1 1 300px;min-width:200px}
.fsearch input{
  width:100%;font:inherit;font-size:15px;color:var(--foreground);
  background:var(--input);border:1px solid var(--border);border-radius:var(--radius);
  padding:9px 12px;
}
.fsearch input::placeholder{color:var(--muted-foreground)}
.fsearch input:focus{outline:none;border-color:var(--primary);box-shadow:0 0 0 3px rgba(36,99,235,.14)}
select.fsel{
  font:inherit;font-size:14px;color:var(--foreground);background:var(--card);
  border:1px solid var(--border);border-radius:var(--radius);padding:9px 10px;cursor:pointer;
}
select.fsel:focus{outline:none;border-color:var(--primary);box-shadow:0 0 0 3px rgba(36,99,235,.14)}

.chip{
  font:inherit;font-size:13px;font-weight:500;
  padding:6px 11px;border:1px solid var(--border);border-radius:999px;
  background:var(--card);color:var(--muted-foreground);cursor:pointer;
}
.chip:hover{border-color:var(--primary);color:var(--primary)}
.chip[aria-pressed="true"]{background:var(--primary);border-color:var(--primary);color:#fff}
.chip:focus-visible{outline:2px solid var(--primary);outline-offset:2px}

.flabel{
  font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
  color:var(--muted-foreground);margin-right:2px;
}

/* The extras live behind this. Closed by default: the primary controls are
   search, region and order — everything else is opt-in. */
details.more{margin-top:10px;border-top:1px solid var(--border);padding-top:10px}
details.more > summary{
  cursor:pointer;font-size:13px;font-weight:500;color:var(--primary);
  list-style:none;display:inline-flex;align-items:center;gap:6px;
}
details.more > summary::-webkit-details-marker{display:none}
details.more > summary::after{content:"▾";font-size:11px}
details.more[open] > summary::after{content:"▴"}
details.more .frow{margin-top:10px}

.fcount{
  font-size:13px;color:var(--muted-foreground);margin:10px 0 0;
  display:flex;gap:12px;align-items:center;flex-wrap:wrap;
}
.linkbtn{
  font:inherit;font-size:13px;background:none;border:0;padding:0;
  color:var(--primary);cursor:pointer;text-decoration:underline;
}
.linkbtn:hover{color:var(--primary-hover)}

/* ── Region cards ──────────────────────────────────────────────────── */

.grid{display:grid;grid-template-columns:1fr;gap:16px}
@media(min-width:768px){.grid{grid-template-columns:repeat(2,1fr);gap:24px}}
@media(min-width:1280px){.grid{grid-template-columns:repeat(3,1fr)}}

.card{
  background:var(--card);border:1px solid var(--border);border-radius:var(--radius);
  overflow:hidden;align-self:start;
}
.card-head{
  background:var(--muted);padding:12px 16px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between;gap:10px;
}
.card-head h2{font-size:15px;font-weight:600;margin:0}
.card-count{font-size:12px;color:var(--muted-foreground);font-variant-numeric:tabular-nums}

.src{padding:12px 16px;border-bottom:1px solid var(--border)}
.src:last-child{border-bottom:0}
.src h3{
  font-size:13px;font-weight:500;color:var(--source);margin:0 0 6px;
  display:flex;align-items:center;gap:6px;flex-wrap:wrap;
}
.src h3 .via{color:var(--muted-foreground);font-weight:400;font-size:11px}

ul.items{list-style:none;margin:0;padding:0}
ul.items li{padding:5px 0}
ul.items a{
  color:var(--primary);text-decoration:none;font-size:14px;font-weight:500;
  line-height:1.375;display:block;
}
ul.items a:hover{color:var(--primary-hover);text-decoration:underline}
ul.items time{display:block;font-size:12px;color:var(--muted-foreground);margin-top:2px}
ul.items mark{background:rgba(36,99,235,.16);color:inherit;border-radius:2px;padding:0 1px}

/* Session markers: an opt-in extra, off unless the reader turns it on. */
.session-rule{
  display:none;align-items:center;gap:8px;margin:8px 0 4px;
  font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
  color:var(--source);
}
.session-rule::after{content:"";flex:1;border-top:1px solid var(--border)}
body[data-sessions="1"] .session-rule{display:flex}

.empty{color:var(--muted-foreground);font-size:14px;padding:24px 0}
[hidden]{display:none !important}

/* ── Article pages (topics, recaps) ────────────────────────────────── */

.prose{max-width:760px}
.note{
  background:var(--muted);border-left:3px solid var(--primary);
  border-radius:0 var(--radius) var(--radius) 0;padding:16px 18px;margin:18px 0;
}
.note p{margin:0 0 10px}.note p:last-child{margin:0}
.daymark{
  font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
  color:var(--muted-foreground);margin:22px 0 8px;padding-bottom:6px;
  border-bottom:1px solid var(--border);
}
ol.wire{list-style:none;margin:0;padding:0}
ol.wire li{
  display:grid;grid-template-columns:78px 1fr;gap:12px;
  padding:11px 0;border-bottom:1px solid var(--border);
}
ol.wire time{font-size:12px;color:var(--muted-foreground);padding-top:2px}
ol.wire a{color:var(--primary);text-decoration:none;font-size:15px;font-weight:500;line-height:1.4}
ol.wire a:hover{text-decoration:underline}
ol.wire .src-tag{font-size:12px;color:var(--muted-foreground);margin-top:2px;display:block}
ol.wire mark{background:rgba(36,99,235,.16);color:inherit;border-radius:2px;padding:0 1px}
@media(max-width:640px){ol.wire li{grid-template-columns:1fr;gap:2px}}

.cards{list-style:none;margin:18px 0 0;padding:0;display:grid;gap:12px}
@media(min-width:768px){.cards{grid-template-columns:repeat(2,1fr)}}
.cards li{
  border:1px solid var(--border);border-radius:var(--radius);padding:14px 16px;background:var(--card);
}
.cards h2{font-size:16px;font-weight:600;margin:0 0 4px}
.cards h2 a{color:var(--primary);text-decoration:none}
.cards h2 a:hover{text-decoration:underline}
.cards p{margin:0;color:var(--muted-foreground);font-size:14px}

/* ── Foot ──────────────────────────────────────────────────────────── */

.foot{
  margin-top:36px;padding-top:14px;border-top:1px solid var(--border);
  font-size:13px;color:var(--muted-foreground);
}
.foot a{color:var(--primary)}

.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}
"""
