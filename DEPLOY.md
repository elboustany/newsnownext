# Going live on newsnownext.org

The stack: GitHub holds the code and runs the schedule, Cloudflare Pages
serves the site, the domain points at Pages. Once wired, the site rebuilds
itself from live feeds every 30 minutes during market hours with no server
to maintain.

Everything in this repo is ready. Four short steps remain, and three of
them involve credentials, so they are yours to run.

## 1. Push the repo to GitHub (5 minutes)

```bash
brew install gh
gh auth login
```

Pick GitHub.com, HTTPS, login with browser. Then, from this folder:

```bash
cd /Users/charlesboustany/Downloads/newsnownext
gh repo create newsnownext --public --source=. --push
```

Use `--private` if you prefer, but note the schedule: a public repo gets
unlimited free Actions minutes; a private repo gets 2,000 minutes per month,
and the 30-minute cadence uses roughly 4,000. On a private repo, either
accept the cost or halve the cadence in `.github/workflows/site.yml`.

If the friend wants it under his account instead: he creates an empty repo,
adds you as a collaborator, and you run
`git remote add origin <his-repo-url> && git push -u origin main --tags`.

## 2. Create the Cloudflare API token (3 minutes)

In the Cloudflare dashboard (with the friend's account access):

1. My Profile -> API Tokens -> Create Token -> Custom token
2. Permissions: **Account -> Cloudflare Pages -> Edit**. Nothing else.
3. Copy the token. Also note the **Account ID** (right sidebar of any
   dashboard page, or in the URL).

## 3. Add the two secrets to the GitHub repo (2 minutes)

GitHub repo -> Settings -> Secrets and variables -> Actions -> New secret:

- `CLOUDFLARE_API_TOKEN` = the token from step 2
- `CLOUDFLARE_ACCOUNT_ID` = the account ID

Or from the terminal: `gh secret set CLOUDFLARE_API_TOKEN` (it prompts,
paste, enter) and the same for `CLOUDFLARE_ACCOUNT_ID`.

## 4. First deploy, then the domain (5 minutes)

Trigger the first run: GitHub repo -> Actions -> "Build and deploy site" ->
Run workflow. It builds from live feeds and creates the Pages project
`newsnownext` on its first deploy. When the run is green, the site is at
`https://newsnownext.pages.dev`.

Then attach the domain: Cloudflare dashboard -> Workers & Pages ->
newsnownext -> Custom domains -> add `www.newsnownext.org` (and
`newsnownext.org` if wanted; Cloudflare sets the DNS records itself since
the zone is already there). The site canonicalises to `www`, matching the
live site.

Certificate issues in a minute or two. Done: the cron keeps it fresh.

## What runs automatically after that

- Every 30 minutes, Mon-Fri market hours (every 3h weekends): fetch all 22
  feeds and 20 country feeds, refresh quotes and FX, recompute trending
  with cross-run velocity, rebuild all 18 pages, deploy.
- The feed cache and trending history persist between runs via Actions
  cache, so "up from 2 desks" velocity works in production.
- If a run fails, the previous deployment stays live and GitHub emails the
  repo owner. Nothing half-built ever ships.
- Every push to main also deploys, so content edits (a new synopsis,
  updated events.json) go live in about two minutes.

## The daily routine that is NOT automatic

- `generator/synopsis/YYYY-MM-DD.txt`: the Morning Brief. Without it the
  day's recap is noindex and the brief block does not render. Write it,
  commit, push; the next run publishes it.
- `generator/data/events.json`: top up as dates approach; the build warns
  when fewer than five future events remain.
- `python3 dev/gen-digest.py` renders the newsletter email locally when a
  send provider is connected.

## Switches still off

- `newsletter_signup_url` in `generator/config.json`: set it when a
  Buttondown/Resend list exists; the signup form goes live by itself.
- `contact_form_url`: same idea for the contact form; until then it
  composes an email.
- Google Search Console: add the domain after DNS, submit
  `https://www.newsnownext.org/sitemap.xml`.
