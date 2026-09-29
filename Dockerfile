# Static host for ridiculouslyhopeful.com — same GitHub -> Railway flow as prostojoes,
# but this site is plain HTML, so we just serve the finished files with Caddy.
FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY site/ /srv/
