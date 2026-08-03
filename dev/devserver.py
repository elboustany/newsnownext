#!/usr/bin/env python3
"""
Run the extension in an ordinary browser tab.

    python3 dev/devserver.py            # then open http://localhost:8787

Two things stop newtab.html from working as a plain web page, and this server
fixes both without a single change to the files that ship:

  1. `chrome.storage.local` does not exist off-extension. A shim backs it with
     localStorage, injected into the page on the way out.
  2. Feed hosts send no CORS headers, so a plain page cannot fetch them. The
     shim rewrites feed fetches to /__feed?url=…, which this server proxies.

Nothing in extension/ knows this exists. What you see is the shipping code.

Also serves the generated site at /site/ when generator/site exists, so one
server shows a client both halves of the package.
"""

import http.server
import socketserver
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "extension"
SITE = ROOT / "generator" / "site"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
UA = "Mozilla/5.0 (compatible; NewsNowNextDev/1.0)"

# Only these hosts may be proxied — a dev box should not be an open relay.
ALLOWED = {
    "news.google.com", "search.cnbc.com", "feeds.content.dowjones.io",
    "finance.yahoo.com", "feeds.feedburner.com", "www.investing.com",
    "www.ft.com",
}

SHIM = b"""
/* Dev harness only. Never shipped, never loaded inside the extension. */
(function () {
  const mem = {};
  if (!globalThis.chrome?.storage?.local) {
    globalThis.chrome = globalThis.chrome || {};
    globalThis.chrome.storage = {
      local: {
        async get(key) {
          const k = typeof key === "string" ? key : Object.keys(key || {})[0];
          try {
            const v = localStorage.getItem("shim:" + k);
            return v ? { [k]: JSON.parse(v) } : {};
          } catch { return k in mem ? { [k]: mem[k] } : {}; }
        },
        async set(obj) {
          for (const [k, v] of Object.entries(obj)) {
            mem[k] = v;
            try { localStorage.setItem("shim:" + k, JSON.stringify(v)); } catch {}
          }
        }
      }
    };
    document.documentElement.dataset.devHarness = "storage";
  }

  const real = globalThis.fetch.bind(globalThis);
  globalThis.fetch = (input, init) => {
    const url = typeof input === "string" ? input : input.url;
    if (/^https?:\\/\\//.test(url) && !url.startsWith(location.origin)) {
      return real("/__feed?url=" + encodeURIComponent(url), init);
    }
    return real(input, init);
  };
})();
"""

BANNER = b"""
<div style="position:fixed;left:0;right:0;bottom:0;z-index:99;
  font:10px/1 ui-monospace,Menlo,monospace;letter-spacing:.12em;
  text-transform:uppercase;text-align:center;padding:7px;
  background:#B23A2E;color:#fff">
  Dev preview &mdash; feeds proxied locally. The real extension fetches direct.
</div>
"""


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *a):
        if "__feed" in (a[0] if a else ""):
            sys.stderr.write("  proxy %s\n" % a[0][:110])

    def do_GET(self):
        parts = urllib.parse.urlparse(self.path)

        if parts.path == "/__shim.js":
            return self._send(SHIM, "application/javascript")

        if parts.path == "/__feed":
            return self._proxy(urllib.parse.parse_qs(parts.query).get("url", [""])[0])

        if parts.path in ("/", "/index.html", "/newtab.html"):
            html = (EXT / "newtab.html").read_bytes()
            html = html.replace(
                b'<script type="module"',
                b'<script src="/__shim.js"></script>\n<script type="module"', 1)
            html = html.replace(b"</body>", BANNER + b"</body>", 1)
            return self._send(html, "text/html; charset=utf-8")

        if parts.path.startswith("/site/"):
            return self._static(SITE, parts.path[len("/site/"):] or "index.html")

        # Generated pages link to /assets/… because that is correct on the real
        # domain. The extension has no assets/ directory, so map it to the site.
        if parts.path.startswith("/assets/"):
            return self._static(SITE, parts.path.lstrip("/"))

        return self._static(EXT, parts.path.lstrip("/"))

    # ── helpers ──────────────────────────────────────────────────────────

    def _send(self, body, ctype, code=200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _static(self, base, rel):
        path = (base / rel).resolve()
        if not str(path).startswith(str(base.resolve())) or not path.is_file():
            if (path / "index.html").is_file():
                path = path / "index.html"
            else:
                return self._send(b"Not found", "text/plain", 404)
        types = {".html": "text/html; charset=utf-8", ".css": "text/css",
                 ".js": "application/javascript", ".json": "application/json",
                 ".png": "image/png", ".xml": "application/xml",
                 ".txt": "text/plain; charset=utf-8"}
        self._send(path.read_bytes(), types.get(path.suffix, "application/octet-stream"))

    def _proxy(self, url):
        host = urllib.parse.urlparse(url).hostname or ""
        if host not in ALLOWED:
            return self._send(b"Host not allowed", "text/plain", 403)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25) as r:
                body = r.read()
        except Exception as e:                       # noqa: BLE001 - surface to the page
            return self._send(str(e).encode(), "text/plain", 502)
        self._send(body, "application/xml; charset=utf-8")


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    print(f"Extension preview  http://localhost:{PORT}")
    print(f"Generated site     http://localhost:{PORT}/site/topics/oil.html"
          if SITE.exists() else "Generated site     (run generator/build.py first)")
    print("Ctrl-C to stop.\n")
    with Server(("127.0.0.1", PORT), Handler) as httpd:
        httpd.serve_forever()
