FROM caddy:2.11.7-alpine

# Non-root runtime (uid 10001). /data and /config are created and owned here so named
# volumes mounted there inherit the ownership (keeps the internal CA across restarts).
RUN addgroup -S -g 10001 caddy2 && adduser -S -u 10001 -G caddy2 -H caddy2 \
    && mkdir -p /data/caddy /config/caddy \
    && chown -R 10001:10001 /data /config
COPY Caddyfile /etc/caddy/Caddyfile
USER 10001:10001
