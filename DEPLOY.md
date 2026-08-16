# How newsnownext.org is deployed

The stack, chosen so that no API tokens exist anywhere:

1. **GitHub** holds the code. A scheduled Action builds the site from live
   feeds hourly during market hours (every 3 hours on weekends; the cadence
   is sized to Cloudflare Pages' free 500-builds/month quota, and can go to
   every 30 minutes on the $5/month Workers Paid plan)
   and force-pushes the built output to the `production` branch as a
   single orphan commit. The only credential involved is the runner's own
   ephemeral token, so the repo needs no secrets.
2. **Cloudflare Pages** is connected to the repo through its Git
   integration, watches the `production` branch, and deploys whatever
   lands there. No build step on Cloudflare's side: build command is
   empty, output directory is `/`.
3. The **domain** (www.newsnownext.org) is a custom domain on that Pages
   project; DNS lives in the same Cloudflare account, so records and the
   certificate are managed automatically.

## The worker

The build ships a `_worker.js` (Pages advanced mode) with two jobs:

- `/api/quotes` - live CNBC quotes cached ~15 seconds at the edge; the
  ticker cards poll it every 15 seconds (CNBC blocks browser origins, so
  the edge has to make the call). Pages Functions free tier is 100,000
  requests/day; at one poll per 15s that is ~416 concurrent visitor-hours
  per day before quotes stop refreshing (static pages are unaffected).
- `/api/*` and `/portfolio` - proxied to the original Railway backend,
  which still runs the client's login + watchlist system. If Railway is
  cancelled or unreachable, the static portfolio page serves instead and
  the rest of the site is untouched.

## Operating it

- Content edits (a new synopsis, updated events.json): commit to `main`,
  push. The workflow builds and publishes within a couple of minutes.
- Force a refresh: repo -> Actions -> "Build and publish site" -> Run
  workflow.
- A failed build publishes nothing; the previous deployment stays live and
  GitHub emails the repo owner. The sanity gate refuses to publish a home
  page with fewer than 50 headlines.
- The daily routine that stays human: `generator/synopsis/YYYY-MM-DD.txt`
  (the Morning Brief; without it the day's recap is noindex), and topping
  up `generator/data/events.json` when the build warns it is running low.

## Switches still off

- `newsletter_signup_url` in `generator/config.json`: set when a
  Buttondown/Resend list exists; the signup form goes live by itself.
- `contact_form_url`: same for the contact form; until then it composes an
  email.
- Google Search Console: add the domain, submit
  `https://www.newsnownext.org/sitemap.xml`.

## Rollback

- Bad deploy: Cloudflare dashboard -> Workers & Pages -> newsnownext ->
  Deployments -> pick an earlier one -> Rollback.
- Domain back to the old host: restore the DNS records noted in the
  cutover commit message / dashboard audit log.
