# Infra hardening (branch `infra-hardening`)

## How to run
```bash
# dev (unchanged): plain compose, auto-loads docker-compose.override.yml (Redis on 127.0.0.1:6379)
docker compose up -d

# production: explicit -f flags, so the dev override is NOT applied
cp .env.example .env     # fill every CHANGE_ME with real values, chmod 600 .env
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```
Only `caddy` publishes a port: `${BIND_IP:-127.0.0.1}:443`. Set `SITE_ADDRESS` to the name/IP users type (Caddy's `tls internal` cert is issued for it; clients must trust Caddy's root CA from the `caddy_data` volume).
First start on a new server: `docker volume create rahkaran_mssql_data` (the volume is `external: true`, unchanged).

## What changed
- `docker-compose.yml` (base/dev): no secret defaults (`${VAR:?}`), pinned images (pgvector 0.8.7-pg16-bookworm, redis 7.4.11-alpine, mssql 2022-CU27-ubuntu-22.04 = the image the data volume already ran), `MSSQL_PID` defaults to Express, dev ports bound to 127.0.0.1.
- `docker-compose.prod.yml` (new): no published ports except caddy; networks `data`/`app` (`internal: true`), `egress` (backend/worker only), `edge` (caddy only); Docker secrets (sourced from `.env`) for postgres (`POSTGRES_PASSWORD_FILE`), redis (`--requirepass`), mssql (wrapper); app containers: non-root, read_only + tmpfs, cap_drop ALL, no-new-privileges, mem/pids limits, log rotation; frontend + caddy services; `REDIS_URL` with password; infra-only secrets blanked inside app containers.
- `infra/caddy/` (new): Dockerfile (non-root) + Caddyfile (proxy `/`→frontend, `/api`→backend with `flush_interval -1`, 60 MB body cap, `/docs /redoc /openapi.json` → 404, HSTS, nosniff, no-referrer, CSP report-only).
- `Dockerfile` (backend): pinned python 3.12.12, uid 10001, owned upload dir, tiktoken encoding baked in. `Frontend/Dockerfile`: pinned node 20.20.2, uid 10001, `HOSTNAME=0.0.0.0`.
- `.dockerignore` (both), `.gitignore` (`.env*` except `.env.example`, `secrets/`, `*.bak *.trn *.age *.pem *.key`), `.env.example` (placeholders only).

## NEEDS CODE CHANGE (not done - for your review)
1. **Secrets as files for the app** (JWT, LLM/embedding keys, `RAHKARAN_DB_PASSWORD` still come from `.env` via `env_file`). `app/core/config.py`:
   ```python
   model_config = SettingsConfigDict(env_file=".env", secrets_dir="/run/secrets", extra="ignore")
   ```
   then add `secrets:` entries for `jwt_secret_key`, `llm_api_key`, `embedding_api_key`, `rahkaran_db_password` in the prod overlay.
2. **Disable API docs in the app itself** (defense in depth; today only Caddy blocks them) - `app/main.py:18`:
   ```python
   _prod = settings.environment == "production"
   app = FastAPI(title=settings.app_name, debug=settings.debug,
                 docs_url=None if _prod else "/docs", redoc_url=None if _prod else "/redoc", openapi_url=None if _prod else "/openapi.json")
   ```
3. Rate limiting for login/register/chat (stock Caddy has no rate-limit module): add in the app (e.g. slowapi + Redis) or use a Caddy build with the rate-limit plugin.
4. `Frontend/src/shared/lib/apiClient.ts`: the build uses `NEXT_PUBLIC_API_URL=/api/v1` (relative). It works in the browser; the SSR fallback `http://localhost:8000/api/v1` would be wrong if any server component calls the API.

## NEEDS MANUAL ACTION
- **Rotate every real secret.** The SA default password was committed in `docker-compose.yml` (commit `4a320ca`, still in history); real LLM/embedding keys, Postgres, SA and reader passwords sit in plaintext in local `.env`/`.env.production`. Run gitleaks/trufflehog on history; rewriting history is your call.
- Fill `.env` from `.env.example` on the server (`chmod 600`). Use hex passwords (`openssl rand -hex 24`): they are embedded in `DATABASE_URL`/`REDIS_URL`. Set `CORS_ORIGINS` to the https origin only (remove the old `http://31.216.62.251` entries).
- Express edition: confirm the restored DB uses no Enterprise-only features (`SELECT * FROM sys.dm_db_persisted_sku_features`) and stays under 10 GB; SA password applies only on first init of a fresh volume.
- Reaching the app from outside: `BIND_IP=127.0.0.1` means SSH tunnel / reverse VPN only. For a VPN (WireGuard) set `BIND_IP` to the VPN interface IP. Docker-published ports bypass ufw, so never use `0.0.0.0`.
- Restore/refresh the accounting DB in prod without a host port: `docker compose exec mssql ...` or a temporary `127.0.0.1:14330` override used only during the maintenance window. The prod container is `backend-mssql-1`, not `rahkaran-mssql`.
- Repo hygiene (report only): tracked `assets/*.pdf` (contract documents) and `Backend/docs/rahkaran/*` (real company/person names and figures) - keep the repo private or untrack them.

## RISKS / BREAKAGES noticed
- `.github/workflows/deploy.yml` deploys on every push to `main` via `git reset --hard` + systemd (`front`), not via Docker. It is untouched; merging this branch to `main` does not switch deployment to compose.
- `env_file: .env` hands the whole `.env` to app containers; infra-only secrets are blanked in prod, but the app still holds LLM keys, JWT secret and the reader password (needs change 1).
- Redis has no `read_only` (compose cannot inject env-sourced secrets into a read-only rootfs). postgres/redis/mssql/caddy keep a few capabilities: postgres CHOWN/DAC_OVERRIDE/FOWNER/SETGID/SETUID; mssql and caddy NET_BIND_SERVICE (their binaries carry it as a file capability, exec fails without it).
- `egress` lets backend/worker reach any internet host; add an allow-list (firewall/proxy) for the LLM host as a follow-up. Image digest pinning is also a follow-up.
- Backend runs as uid 10001 now: an existing dev `uploads_data` volume created by the old root image must be `chown 10001:10001` (none existed here). Dev redis/backend/mssql ports are now localhost-only (LAN access to them stops).
- Dev default for `MSSQL_PID` is now Express; set `MSSQL_PID=Developer` in your local `.env` to keep the old dev behavior.

## Updating the accounting database (drop folder)
Put the company's export (the `FULL_...bak` / `DIFF_...bak` files, in any sub-folder, e.g. keep their `FULL/ DIFF/ LOG/` layout) into **`Backend/data/rahkaran-backups/`** (override the location with `RAHKARAN_BACKUP_DIR` in `.env`). The folder is mounted read-only at `/backups` in the `mssql` container. Files must be readable by everyone (`chmod -R a+rX`). Then:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d        # or: ... run --rm rahkaran-refresh
```
The one-shot `rahkaran-refresh` service (`sql/rahkaran/refresh.py`) runs on every `up`:
1. picks the newest FULL and the newest DIFF whose base LSN matches it (older / unrelated files and `.trn` logs are ignored);
2. exits with "already up to date" if exactly those files (name + size) were already loaded (marker table `master.dbo.rahkaran_restore_state`);
3. restores into a side database `MehvarGostar_new`, re-applies the `ai` layer + the reader login (`apply.py`), smoke-tests it;
4. swaps it in (old one renamed aside, dropped only after the new one is live; rolled back on failure) and sets it READ_ONLY.
The live database is untouched until step 4; the app sees a few seconds of downtime during the swap. Options: `run --rm rahkaran-refresh --dry-run` (show what it would load), `--force` (reload even if unchanged). Tested here on SQL Server Express with the real FULL 2026-10-02 + DIFF 2026-10-05 pair (about 10 s on SSD).
Notes: needs free disk for a second copy during the restore; in dev the first run after enabling it reloads once (no marker yet); the DIFF/FULL must come from the same SQL Server backup chain.
This replaces the manual "make a backup on the laptop and carry it over" step: only the company's export is ever copied, straight into the folder on the server.
