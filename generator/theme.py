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
  --mag:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.4' stroke-linecap='round'%3E%3Ccircle cx='11' cy='11' r='7'/%3E%3Cpath d='M20 20l-3.5-3.5'/%3E%3C/svg%3E");
  --caret:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 12 8'%3E%3Cpath d='M1 1.5 6 6.5l5-5' fill='none' stroke='%2365758b' stroke-width='1.8' stroke-linecap='round'/%3E%3C/svg%3E");
}

/* No dark scheme on purpose. The live site is light-only, and a page that
   flips to dark on a dark-mode machine is exactly the "different colours"
   this build is meant to avoid. To offer one later, add a
   `@media (prefers-color-scheme:dark)` block overriding the tokens above -
   nothing else in the stylesheet hard-codes a colour. */

*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  margin:0;background:var(--background);color:var(--foreground);
  font-family:var(--sans);font-size:16px;line-height:1.5;
  -webkit-font-smoothing:antialiased;
}
a{color:inherit}


/* ── Promo banner ──────────────────────────────────────────────────── */

.promo{
  background:linear-gradient(90deg,#059669,#2563eb);
  color:#fff;font-size:13px;
}
.promo-in{
  max-width:1320px;margin:0 auto;padding:9px 20px;
  display:flex;align-items:center;gap:12px;flex-wrap:wrap;
}
.promo .tag{
  background:rgba(255,255,255,.22);border-radius:4px;padding:2px 7px;
  font-size:10px;font-weight:700;letter-spacing:.06em;
}
.promo strong{font-weight:600}
.promo .muted{opacity:.85}
.promo a{color:#fff;margin-left:auto;font-weight:500;text-decoration:none;white-space:nowrap}
.promo a:hover{text-decoration:underline}
.promo .close{
  background:none;border:0;color:#fff;opacity:.8;cursor:pointer;
  font-size:16px;line-height:1;padding:0 2px;
}
.promo .close:hover{opacity:1}

/* ── Sticky chrome ─────────────────────────────────────────────────── */

/* Only the nav is sticky. The quote cards are tall; pinning them too would
   permanently eat a third of the viewport. */
.chrome{position:sticky;top:0;z-index:50}

.nav{background:var(--navbar);color:var(--navbar-fg)}
.nav-in{
  max-width:1320px;margin:0 auto;padding:16px 20px;
  display:flex;align-items:center;gap:24px;
}
.logo{
  font-weight:900;font-size:26px;line-height:.92;letter-spacing:-.02em;
  text-decoration:none;flex:none;
}
.logo span{display:block}
.logo .l1{color:var(--logo-news)}
.logo .l2{color:var(--logo-now)}
.logo .l3{color:var(--logo-next)}

/* No overflow scrolling here: a scroll container clips its absolutely-
   positioned children, which silently hid the dropdown panels. Four items
   wrap fine on small screens. */
.nav-links{
  display:flex;gap:4px;align-items:center;margin-left:auto;
  flex-wrap:wrap;justify-content:flex-end;
}
.nav-links a{
  color:#e5e7eb;text-decoration:none;font-size:15px;font-weight:500;
  padding:8px 11px;border-radius:6px;white-space:nowrap;
  display:inline-flex;align-items:center;gap:6px;
}
.nav-links a:hover{color:#fff;background:rgba(255,255,255,.10)}
.nav-links a[aria-current]{color:#fff;background:rgba(255,255,255,.16)}
.nav-links svg{width:15px;height:15px;flex:none}

/* ── Nav dropdowns + market clocks ─────────────────────────────────── */

.menu{position:relative}
.menu-btn{
  font:inherit;font-size:15px;font-weight:500;color:#e5e7eb;
  background:none;border:0;cursor:pointer;border-radius:6px;
  padding:8px 11px;display:inline-flex;align-items:center;gap:6px;white-space:nowrap;
}
.menu-btn:hover,.menu-btn[aria-expanded="true"]{color:#fff;background:rgba(255,255,255,.10)}
.menu-btn.cur{color:#fff;background:rgba(255,255,255,.16)}
.caret{font-size:10px;opacity:.7}
.menu-pop{
  position:absolute;top:calc(100% + 6px);left:0;z-index:70;min-width:190px;
  background:#fff;border:1px solid var(--border);border-radius:10px;
  box-shadow:0 12px 32px rgba(16,24,40,.18);padding:6px;
}
.menu:last-child .menu-pop,.nav-links .menu:last-of-type .menu-pop{left:auto;right:0}
.menu-pop a{
  display:flex;align-items:center;gap:8px;color:var(--foreground) !important;
  background:none !important;font-size:14px;font-weight:500;
  padding:8px 10px;border-radius:7px;text-decoration:none;
}
.menu-pop a:hover{background:var(--muted) !important}
.menu-pop a svg{width:15px;height:15px;flex:none;color:var(--muted-foreground)}
.menu-pop a:hover svg,.menu-pop a[aria-current] svg{color:var(--primary)}
.menu-pop a[aria-current]{color:var(--primary) !important;background:rgba(36,99,235,.07) !important}

.clockbox{margin-left:6px}
.clock-chip{font-size:13px;font-weight:600;letter-spacing:.01em}
.clock-chip [data-clock-mini]{font-variant-numeric:tabular-nums}
.clock-ico{font-size:13px}
.clock-pop{min-width:220px;padding:8px}
.clock-row{
  display:flex;align-items:center;gap:9px;padding:7px 8px;border-radius:7px;
  font-size:13.5px;color:var(--foreground);
}
.clock-row:hover{background:var(--muted)}
.clock-row .dot{width:8px;height:8px;border-radius:50%;background:#cbd5e1;flex:none}
.clock-row.open .dot{background:#10b981}
.clock-row .cname{font-weight:500}
.clock-row .ctime{
  margin-left:auto;font-variant-numeric:tabular-nums;color:var(--muted-foreground);
  font-weight:600;
}
.clock-row.open .ctime{color:var(--foreground)}

@media(max-width:900px){.clockbox{display:none}}

/* ── Economic calendar ─────────────────────────────────────────────── */

.ev-month{
  font-size:13px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
  color:var(--muted-foreground);margin:26px 0 10px;padding-bottom:7px;
  border-bottom:1px solid var(--border);
}
.evlist{max-width:820px}
.ev{
  display:flex;gap:16px;padding:16px;margin-bottom:10px;
  background:var(--card);border:1px solid var(--border);border-radius:10px;
}
.ev-date{
  flex:none;width:52px;text-align:center;padding-top:2px;
  display:flex;flex-direction:column;
}
.ev-day{font-size:24px;font-weight:800;letter-spacing:-.02em;line-height:1.1}
.ev-wd{font-size:11px;font-weight:600;text-transform:uppercase;color:var(--muted-foreground)}
.ev-body{min-width:0;flex:1}
.ev-line{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.ev-line h3{font-size:15.5px;font-weight:700;margin:0}
.ev-badge{
  font-size:10px;font-weight:800;letter-spacing:.05em;color:#fff;
  padding:2px 7px;border-radius:5px;
}
.ev-badge.high{background:#dc2626}
.ev-badge.medium{background:#f59e0b}
.ev-cat{
  font-size:11px;font-weight:600;color:var(--muted-foreground);
  border:1px solid var(--border);border-radius:5px;padding:1px 7px;
}
.ev-note{margin:5px 0 8px;font-size:13.5px;line-height:1.5;color:var(--muted-foreground)}
.ev-foot{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.ev-when{font-size:13px;font-weight:600;font-variant-numeric:tabular-nums}
.ev-count{
  font-size:12px;font-weight:600;color:#9a3412;background:#ffedd5;
  border-radius:6px;padding:2px 8px;
}
.ev-count:empty{display:none}

/* ── Ticker - the quote-card band under the nav ────────────────────── */

.ticker{background:#eceff3;border-bottom:1px solid var(--border);padding:16px 0 20px}
.ticker-in{max-width:1320px;margin:0 auto;padding:0 20px}
.tabs{display:flex;justify-content:center;gap:8px;margin-bottom:14px;flex-wrap:wrap}
.tab{
  font:inherit;font-size:14px;font-weight:500;padding:7px 16px;border-radius:999px;
  border:0;background:#fff;color:var(--foreground);cursor:pointer;white-space:nowrap;
  box-shadow:0 1px 2px rgba(16,24,40,.06);
}
.tab:hover{background:var(--muted)}
.tab[aria-selected="true"]{background:#1f2937;color:#fff}
.tab:focus-visible{outline:2px solid var(--primary);outline-offset:2px}

/* Every panel occupies the same grid cell; hidden ones keep their layout
   (visibility, not display), so the band is always exactly as tall as its
   tallest tab and switching can never resize the section. */
.panels{display:grid}
.panels > .quotes{grid-area:1/1}
.panels > .quotes[hidden]{
  display:grid !important;visibility:hidden;pointer-events:none;
}
.quotes{
  display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,210px));
  justify-content:center;gap:14px;grid-auto-rows:1fr;
}
.qcard{
  background:var(--card);border:1px solid var(--border);border-radius:10px;
  padding:12px 14px;box-shadow:0 1px 2px rgba(16,24,40,.05);
}
.qtop{
  display:flex;align-items:flex-start;justify-content:space-between;gap:8px;
  min-height:20px;
}
.qname{
  font-size:13px;font-weight:600;line-height:1.25;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
  overflow:hidden;min-height:2.5em;
}
.qlive{
  display:inline-flex;align-items:center;gap:5px;flex:none;
  font-size:11px;color:var(--muted-foreground);padding-top:1px;
}
.qlive i{width:7px;height:7px;border-radius:50%;background:#10b981}
.qlive.delayed i{background:#f59e0b}
.qbadge{
  display:inline-block;margin:7px 0 6px;font-size:11px;font-weight:700;color:#fff;
  padding:2px 8px;border-radius:6px;letter-spacing:.02em;
}
.qprice{font-size:20px;font-weight:800;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.qchg{font-size:13px;font-weight:600;font-variant-numeric:tabular-nums;margin-top:3px}
.qtime{
  font-size:12px;color:var(--muted-foreground);margin-top:5px;
  display:flex;align-items:center;gap:5px;
}
.qtime::before{content:"";width:5px;height:5px;border-radius:50%;background:#93c5fd}
.up{color:#059669}.down{color:#dc2626}.flat{color:var(--muted-foreground)}
.qmissing{font-size:13px;color:var(--muted-foreground);margin-top:8px}

/* Event cards are quote cards: same skeleton (qtop/qbadge/qprice/qchg/
   qtime), so switching tabs cannot change the band's height. The qname on
   every card reserves two lines for the same reason: event names wrap,
   and the reservation keeps instrument cards and event cards identical. */
.evc{text-decoration:none;color:inherit;display:block}
.evc:hover .qname{color:var(--primary)}
.evc .ev-badge{flex:none;font-size:9px;padding:2px 6px}

@media(max-width:640px){
  .quotes{grid-template-columns:repeat(2,1fr)}
  .logo{font-size:20px}
}

/* ── Today's Brief + For You ───────────────────────────────────────── */

.brief{
  background:linear-gradient(180deg,#eff6ff,#fdfefe);
  border:1px solid #bfdbfe;border-radius:12px;
  padding:16px 20px;margin:16px 0 4px;
}
.brief-head{display:flex;align-items:center;gap:10px}
.brief-mark{
  width:30px;height:30px;border-radius:8px;background:var(--primary);color:#fff;
  display:inline-flex;align-items:center;justify-content:center;font-size:15px;flex:none;
}
.brief-head h2{font-size:17px;font-weight:800;margin:0;letter-spacing:-.01em;color:#1e3a8a}
.brief-date{font-size:12px;color:var(--muted-foreground);font-weight:600;margin-left:2px}
.brief-head .tcollapse{margin-left:auto;color:#1e3a8a}
.brief-body{margin-top:10px;max-width:860px}
.brief p{margin:0 0 10px;font-size:14.5px;line-height:1.65}
.brief-more p:last-child{margin-bottom:0}
#brief-expand{margin:2px 0 10px}
.brief-links{display:flex;gap:18px;flex-wrap:wrap}
.brief-links a{color:var(--primary);text-decoration:none;font-size:13.5px;font-weight:600}
.brief-links a:hover{text-decoration:underline}

.foryou{
  background:var(--card);border:1px solid var(--border);border-radius:var(--radius);
  padding:14px 18px;margin:12px 0 4px;
}
.foryou h2{font-size:14px;font-weight:700;margin:0 0 2px;display:flex;gap:8px;align-items:center}
.foryou .fy-kw{font-size:11.5px;color:var(--muted-foreground);font-weight:500}
.foryou ul{list-style:none;margin:8px 0 0;padding:0}
.foryou li{padding:5px 0;display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
.foryou a{color:var(--primary);text-decoration:none;font-size:14px;font-weight:500}
.foryou a:hover{text-decoration:underline}
.fy-src{font-size:12px;color:var(--muted-foreground)}
.fy-hot{
  font-size:10.5px;font-weight:700;color:#9a3412;background:#ffedd5;
  border-radius:5px;padding:1px 7px;
}
.foryou .fy-edit{font-size:12.5px}

/* ── Newsletter ────────────────────────────────────────────────────── */

.nl-form{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0}
.nl-form input{
  flex:1 1 240px;font:inherit;font-size:15px;padding:11px 14px;
  border:1px solid var(--border);border-radius:var(--radius);background:var(--input);
}
.nl-form input:focus{outline:none;border-color:var(--primary);box-shadow:0 0 0 3px rgba(36,99,235,.13)}
.nl-btn{
  font:inherit;font-size:15px;font-weight:600;color:#fff;background:var(--primary);
  border:0;border-radius:var(--radius);padding:11px 20px;cursor:pointer;
}
.nl-btn:hover{background:var(--primary-hover)}

/* ── Trending ──────────────────────────────────────────────────────── */

.trend{
  background:linear-gradient(180deg,#fff7ed,#fffdf8);
  border:1px solid #fed7aa;border-radius:12px;
  padding:16px 18px;margin:14px 0 18px;
}
.trend-head{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.trend-head h2{
  font-size:21px;font-weight:800;letter-spacing:-.02em;color:#9a3412;
  margin:0;display:flex;align-items:center;gap:8px;
}
.flame{font-size:19px}
.trend-chips{margin-left:auto}
.trend .chip[aria-pressed="true"]{background:#f97316;border-color:#f97316}
.trend .chip:hover{border-color:#f97316;color:#ea580c}
.trend .chip[aria-pressed="true"]:hover{color:#fff}
.tcollapse{
  background:none;border:0;cursor:pointer;font-size:12px;
  color:#9a3412;padding:4px 6px;
}
.trend-body{margin-top:14px}
.tgrid{display:grid;gap:12px;grid-template-columns:1fr}
@media(min-width:640px){.tgrid{grid-template-columns:repeat(2,1fr)}}
@media(min-width:1000px){.tgrid{grid-template-columns:repeat(5,1fr)}}
.tcard{
  background:var(--card);border:1px solid #f5e2cd;border-radius:10px;
  padding:13px 14px;display:flex;flex-direction:column;gap:9px;
  box-shadow:0 1px 2px rgba(16,24,40,.04);
}
.ttop{display:flex;align-items:center;justify-content:space-between}
.tnum{
  width:33px;height:33px;border-radius:50%;background:#f97316;color:#fff;
  font-size:13px;font-weight:700;display:flex;align-items:center;justify-content:center;
}
.bm{
  background:none;border:0;cursor:pointer;color:#9ca3af;padding:3px;
  display:inline-flex;border-radius:6px;
}
.bm svg{width:17px;height:17px;fill:none}
.bm-sm{opacity:.35}
.bm-sm svg{width:14px;height:14px}
.bm-sm:hover,.bm-sm[aria-pressed="true"]{opacity:1}
.bm:hover{color:#f97316}
.bm[aria-pressed="true"]{color:#f97316}
.bm[aria-pressed="true"] svg{fill:#f97316}
.thl{
  font-size:14.5px;font-weight:600;line-height:1.4;color:var(--foreground);
  text-decoration:none;
}
.thl:hover{color:var(--primary)}
.tfoot{margin-top:auto;display:flex;flex-direction:column;gap:5px;align-items:flex-start}
.tsrc{
  background:#ffedd5;color:#9a3412;font-size:12px;font-weight:600;
  padding:3px 10px;border-radius:8px;
}
.tmeta{font-size:11.5px;color:var(--muted-foreground);margin:0}

/* ── Topic intros, Forex, Books ────────────────────────────────────── */

/* Topic intros exist for crawlers; readers should barely notice them. */
.intro{max-width:760px;margin:2px 0 6px}
.intro p{margin:0;font-size:13.5px;line-height:1.55;color:var(--muted-foreground)}

.fxcard{max-width:1000px}
.tablewrap{overflow-x:auto}
table.fx{border-collapse:collapse;width:100%;min-width:680px}
table.fx th,table.fx td{padding:12px 16px;text-align:right;font-size:14px;white-space:nowrap}
table.fx th{
  background:var(--muted);font-size:11px;font-weight:600;letter-spacing:.05em;
  text-transform:uppercase;color:var(--muted-foreground);border-bottom:1px solid var(--border);
}
table.fx th:first-child,table.fx td:first-child{text-align:left}
table.fx tbody tr{border-bottom:1px solid var(--border)}
table.fx tbody tr:last-child{border-bottom:0}
table.fx tbody tr:hover{background:#f8fafc}
table.fx td{font-variant-numeric:tabular-nums}
.fx-pair{font-weight:700;font-size:14.5px}
.fx-rate{color:var(--muted-foreground);font-size:12.5px;margin-top:1px}
.pct{
  display:inline-block;min-width:74px;text-align:right;
  padding:3px 8px;border-radius:6px;font-weight:600;font-size:13px;
}
.pct.up{background:rgba(5,150,105,.09)}
.pct.down{background:rgba(220,38,38,.08)}
.fx-note{
  margin:0;padding:12px 16px;border-top:1px solid var(--border);
  font-size:12.5px;color:var(--muted-foreground);
}

.books{display:grid;gap:12px;grid-template-columns:1fr;margin-top:6px}
.bshelf{
  grid-column:1/-1;display:flex;align-items:center;gap:9px;
  margin:18px 0 2px;padding-bottom:8px;border-bottom:1px solid var(--border);
  font-size:16px;font-weight:800;letter-spacing:-.01em;
}
.bshelf:first-child{margin-top:6px}
.bshelf-dot{width:11px;height:11px;border-radius:4px;background:var(--shelf);flex:none}
.bshelf-n{
  margin-left:auto;font-size:12px;font-weight:600;color:var(--muted-foreground);
}
@media(min-width:700px){.books{grid-template-columns:repeat(2,1fr)}}
@media(min-width:1100px){.books{grid-template-columns:repeat(3,1fr)}}
.book{
  border:1px solid var(--border);border-radius:var(--radius);background:var(--card);
  padding:14px 16px;display:flex;gap:14px;align-items:flex-start;
}
.bcover{
  flex:none;width:58px;height:86px;border-radius:5px;position:relative;
  display:flex;align-items:center;justify-content:center;
  color:#fff;font-weight:800;font-size:26px;font-family:Georgia,serif;
  box-shadow:0 2px 5px rgba(16,24,40,.18);
}
.bcover::before{
  content:"";position:absolute;left:7px;top:0;bottom:0;width:1px;
  background:rgba(255,255,255,.35);
}
.bcover.has-img{background:var(--muted);overflow:hidden}
.bcover.has-img::before{display:none}
.bcover.has-img img{width:100%;height:100%;object-fit:cover;display:block}
.binfo{display:flex;flex-direction:column;gap:5px;min-width:0}
.book-cat{
  font-size:10px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;
  color:var(--source);
}
.book h3{font-size:15px;font-weight:600;margin:0;line-height:1.3}
.book .byline{font-size:13px;color:var(--muted-foreground);margin:0}
.book a.buy{
  font-size:13px;font-weight:500;color:var(--primary);text-decoration:none;margin-top:2px;
}
.book a.buy:hover{text-decoration:underline}
.book mark{background:rgba(36,99,235,.16);color:inherit;border-radius:2px;padding:0 1px}

/* ── Shell ─────────────────────────────────────────────────────────── */

.wrap{max-width:1320px;margin:0 auto;padding:20px 20px 64px}
.page-head{margin:8px 0 4px}
h1{font-size:26px;font-weight:800;letter-spacing:-.02em;margin:0 0 4px}
.standfirst{color:var(--muted-foreground);margin:0;font-size:15px}

/* ── Filter bar ────────────────────────────────────────────────────── */

/* One line. Search, a region menu and an order menu - that is the whole
   primary surface. Anything more lived in a block that ate half the screen
   before the reader saw a single headline. */
.filters{
  display:flex;align-items:center;gap:8px;flex-wrap:wrap;
  margin:14px 0 16px;
}
.fsearch{position:relative;flex:1 1 260px;min-width:180px}
.fsearch input{
  width:100%;font:inherit;font-size:14px;color:var(--foreground);
  background:var(--card);border:1px solid var(--border);border-radius:999px;
  padding:9px 14px 9px 36px;
}
.fsearch::before{
  content:"";position:absolute;left:13px;top:50%;width:13px;height:13px;
  transform:translateY(-50%);pointer-events:none;opacity:.55;
  background:currentColor;
  -webkit-mask:var(--mag) center/contain no-repeat;
  mask:var(--mag) center/contain no-repeat;
}
.fsearch input::placeholder{color:var(--muted-foreground)}
.fsearch input:focus{
  outline:none;border-color:var(--primary);box-shadow:0 0 0 3px rgba(36,99,235,.13);
}
select.fsel{
  font:inherit;font-size:13px;font-weight:500;color:var(--foreground);
  background:var(--card);border:1px solid var(--border);border-radius:999px;
  padding:9px 30px 9px 13px;cursor:pointer;appearance:none;
  background-image:var(--caret);background-repeat:no-repeat;
  background-position:right 11px center;background-size:9px;
}
select.fsel:hover{border-color:var(--muted-foreground)}
select.fsel:focus{outline:none;border-color:var(--primary);box-shadow:0 0 0 3px rgba(36,99,235,.13)}

.fcount{
  font-size:13px;color:var(--muted-foreground);margin:0;
  display:flex;gap:10px;align-items:center;white-space:nowrap;
}
.linkbtn{
  font:inherit;font-size:13px;background:none;border:0;padding:0;
  color:var(--primary);cursor:pointer;
}
.linkbtn:hover{text-decoration:underline}

.chip{
  font:inherit;font-size:13px;font-weight:500;
  padding:6px 11px;border:1px solid var(--border);border-radius:999px;
  background:var(--card);color:var(--muted-foreground);cursor:pointer;
}
.chip:hover{border-color:var(--primary);color:var(--primary)}
.chip[aria-pressed="true"]{background:var(--primary);border-color:var(--primary);color:#fff}
.chip:focus-visible{outline:2px solid var(--primary);outline-offset:2px}
.chips{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.flabel{
  font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
  color:var(--muted-foreground);
}
.frow{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.frow + .frow{margin-top:8px}

@media(max-width:700px){
  .fcount{width:100%;order:9}
}

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
  display:flex;align-items:center;gap:7px;flex-wrap:wrap;
}
.srclogo{width:16px;height:16px;border-radius:4px;flex:none;object-fit:contain}
.flag{font-size:15px;margin-right:2px}
.src h3 .via{color:var(--muted-foreground);font-weight:400;font-size:11px}

ul.items{list-style:none;margin:0;padding:0}
ul.items li{padding:5px 24px 5px 0;position:relative}
ul.items .bm-sm{position:absolute;right:-2px;top:5px}
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
  display:grid;grid-template-columns:78px 1fr auto;gap:12px;align-items:start;
  padding:11px 0;border-bottom:1px solid var(--border);
}
ol.wire .wire-body{min-width:0}
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

/* ── Podcasts ──────────────────────────────────────────────────────── */

.pods{display:grid;gap:18px;margin-top:16px;grid-template-columns:1fr}
@media(min-width:900px){.pods{grid-template-columns:repeat(2,1fr)}}
.pod{
  border:1px solid var(--border);border-radius:12px;background:var(--card);
  overflow:hidden;display:flex;flex-direction:column;
}
.pod-thumb{position:relative;display:block;aspect-ratio:16/9;background:var(--muted)}
.pod-thumb img{width:100%;height:100%;object-fit:cover;display:block}
.pod-thumb::after{
  content:"";position:absolute;inset:0;
  background:linear-gradient(180deg,transparent 60%,rgba(16,24,40,.25));
}
.pod-play{
  position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
  width:52px;height:52px;border-radius:50%;z-index:1;
  background:rgba(220,38,38,.92);color:#fff;font-size:19px;
  display:flex;align-items:center;justify-content:center;padding-left:4px;
  box-shadow:0 6px 18px rgba(16,24,40,.35);transition:transform .15s;
}
.pod-thumb:hover .pod-play{transform:translate(-50%,-50%) scale(1.08)}
.pod-kind{
  position:absolute;top:10px;right:10px;z-index:1;
  font-size:10.5px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;
  background:rgba(16,24,40,.72);color:#fff;border-radius:6px;padding:3px 8px;
}
.pod-body{padding:16px 18px;display:flex;flex-direction:column;flex:1}
.pod h2{font-size:16.5px;font-weight:700;margin:0 0 7px;line-height:1.35}
.pod h2 a{color:var(--foreground);text-decoration:none}
.pod h2 a:hover{color:var(--primary)}
.pod-meta{
  font-size:12.5px;color:var(--muted-foreground);margin:0 0 10px;
  display:flex;flex-wrap:wrap;gap:6px;align-items:baseline;
}
.pod-meta strong{color:var(--foreground);font-weight:600;margin-right:3px}
.pod-meta .dot{opacity:.5}
.pod-sum{
  margin:0 0 12px;font-size:14px;line-height:1.6;
  display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;
}
.pod-sum.open{display:block;-webkit-line-clamp:unset}
.pod-foot{margin-top:auto;display:flex;gap:16px;align-items:baseline;flex-wrap:wrap}
.pod-link{font-size:13.5px;font-weight:600;color:var(--primary);text-decoration:none}
.pod-link:hover{text-decoration:underline}

/* ── Ask AI ────────────────────────────────────────────────────────── */

.totop{
  position:fixed;left:22px;bottom:22px;z-index:60;
  width:42px;height:42px;border-radius:50%;
  background:var(--card);border:1px solid var(--border);cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  color:var(--muted-foreground);box-shadow:0 4px 14px rgba(16,24,40,.14);
}
.totop:hover{color:var(--primary);border-color:var(--primary)}
.totop svg{width:18px;height:18px}

.ai-fab{
  position:fixed;right:22px;bottom:22px;z-index:60;
  display:inline-flex;align-items:center;gap:9px;
  font:inherit;font-size:14px;font-weight:600;color:#fff;
  background:#dc2626;border:0;border-radius:999px;padding:13px 20px;cursor:pointer;
  box-shadow:0 6px 16px rgba(220,38,38,.35);
}
.ai-fab:hover{background:#b91c1c}
.ai-fab svg{width:17px;height:17px}
.ai-panel{
  position:fixed;right:22px;bottom:78px;z-index:60;width:min(330px,calc(100vw - 44px));
  background:var(--card);border:1px solid var(--border);border-radius:14px;
  box-shadow:0 18px 40px rgba(16,24,40,.22);padding:14px 16px;
}
.ai-head{display:flex;align-items:center;justify-content:space-between;font-size:15px}
.ai-x{
  background:none;border:0;font-size:20px;line-height:1;cursor:pointer;
  color:var(--muted-foreground);padding:2px 4px;
}
.ai-x:hover{color:var(--foreground)}
.ai-sub{font-size:12px;color:var(--muted-foreground);margin:4px 0 10px}
#ai-q{
  width:100%;font:inherit;font-size:14px;color:var(--foreground);
  background:var(--input);border:1px solid var(--border);border-radius:8px;
  padding:9px 12px;
}
#ai-q:focus{outline:none;border-color:var(--primary);box-shadow:0 0 0 3px rgba(36,99,235,.13)}
.ai-sugg{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}

/* ── Contact ───────────────────────────────────────────────────────── */

.contact-grid{display:grid;gap:12px;grid-template-columns:1fr;margin:16px 0 6px}
@media(min-width:800px){.contact-grid{grid-template-columns:repeat(3,1fr)}}
.ccard{
  background:var(--card);border:1px solid var(--border);border-radius:10px;
  padding:16px 18px;
}
.ccard-ico{
  display:inline-flex;width:34px;height:34px;border-radius:9px;background:var(--muted);
  align-items:center;justify-content:center;font-size:16px;margin-bottom:8px;
}
.ccard h2{font-size:15px;font-weight:700;margin:0 0 4px}
.ccard p{margin:0 0 6px;font-size:13.5px;line-height:1.5;color:var(--muted-foreground)}
.ccard a{color:var(--primary);font-size:13.5px;font-weight:600;text-decoration:none}
.ccard a:hover{text-decoration:underline}
.contact-form-h{font-size:17px;font-weight:800;margin:26px 0 4px}
.cform{max-width:640px;display:flex;flex-direction:column;gap:12px;margin-top:10px}
.cform-row{display:grid;gap:12px;grid-template-columns:1fr}
@media(min-width:640px){.cform-row{grid-template-columns:1fr 1fr}}
.cform label{
  display:flex;flex-direction:column;gap:5px;font-size:12.5px;font-weight:600;
  color:var(--muted-foreground);
}
.cform input,.cform select,.cform textarea{
  font:inherit;font-size:14.5px;color:var(--foreground);background:var(--input);
  border:1px solid var(--border);border-radius:var(--radius);padding:9px 12px;
}
.cform input:focus,.cform select:focus,.cform textarea:focus{
  outline:none;border-color:var(--primary);box-shadow:0 0 0 3px rgba(36,99,235,.13);
}
.cform textarea{resize:vertical}
.cform .nl-btn{align-self:flex-start}

/* ── Read later ────────────────────────────────────────────────────── */

.rl-day{
  font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
  color:var(--muted-foreground);margin:22px 0 6px;padding-bottom:6px;
  border-bottom:1px solid var(--border);
}
.rl-item{
  display:flex;gap:12px;align-items:baseline;padding:9px 0;
  border-bottom:1px solid var(--border);
}
.rl-item a{color:var(--primary);text-decoration:none;font-size:14.5px;font-weight:500}
.rl-item a:hover{text-decoration:underline}
.rl-src{font-size:12px;color:var(--muted-foreground);flex:none}
.rl-x{
  margin-left:auto;flex:none;background:none;border:0;cursor:pointer;
  color:var(--muted-foreground);font-size:15px;padding:2px 6px;border-radius:6px;
}
.rl-x:hover{color:#dc2626;background:var(--muted)}

/* ── Foot ──────────────────────────────────────────────────────────── */

.foot{
  margin-top:36px;padding-top:16px;border-top:1px solid var(--border);
  font-size:13px;color:var(--muted-foreground);text-align:center;
}
.foot p{margin:0 0 6px}
.foot a{color:var(--primary);text-decoration:none}
.foot a:hover{text-decoration:underline}
.foot-tag{font-weight:500;color:var(--foreground)}

.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}
"""
