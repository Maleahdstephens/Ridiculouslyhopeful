# ridiculouslyhopeful.com

Static copy of ridiculouslyhopeful.com (pulled off WordPress / WP Engine), hosted on
Railway via the same GitHub → Railway auto-deploy flow as the Pros to Joes site.

## How it works
- `site/` — the finished website (WordPress export (static HTML)/CSS/JS/images). Edit these files.
- `Caddyfile` — tiny web-server config (clean URLs, gzip).
- `Dockerfile` — tells Railway to serve `site/` with Caddy.

Push to GitHub → Railway rebuilds and deploys automatically. No build step, no
Node, no server code.

## Edit the site
Change files in `site/`, commit, and push. Railway redeploys in ~1 minute.

## Run it locally (optional)
```
cd site
python3 -m http.server 8899   # then open http://localhost:8899
```

## Contact / Schedule forms
The old WordPress forms don't work on a static site. The contact + schedule
forms are wired to a free form service (Formspree) that emails submissions to
Maleah's chosen address. See the migration steps PDF.
