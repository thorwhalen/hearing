# hearing — deployment & the "server hosts it, my Mac runs it" architecture

This documents how `hearing` is deployed to **thorwhalen.com** via the
**enlace / tw_platform** setup, and the deliberate split that keeps all heavy
compute on your own machine.

## The architecture (answer to "can the server host it but run on my resources?")

**Yes.** `hearing` is two parts:

- **Frontend** (`frontend/`, a Vite/React SPA) — static files. *This* is what the
  server hosts, under `https://thorwhalen.com/hearing/`.
- **Backend** (`hearing serve`, FastAPI) — does all the heavy lifting (STT models,
  agents). *This* runs on **your Mac**.

The page (served from the server) calls the backend at whatever **API base URL**
you set in **Settings**. Set it to `http://localhost:8000` and run
`hearing serve` locally: every `/api` call goes to **your laptop**. STT, the
models, your audio, and any API keys never touch the server.

```
  browser ── loads UI ──▶  thorwhalen.com/hearing   (static files only)
     │
     └── /api/* calls ──▶  http://localhost:8000     (YOUR `hearing serve`)
                                   │
                                   ▼  faster-whisper / Claude / your keys — all local
```

Why this works: browsers permit an HTTPS page to call `http://localhost`
(localhost is treated as a trustworthy origin), and the local backend already
sends permissive CORS. **The server runs no compute and needs no API keys.**

## Registering as an enlace app (local + server)

`hearing` registers as a **frontend-only app**, exactly like `thoremin` /
`reelee-web`.

1. **`app.toml`** at the repo root (`proj/t/hearing/app.toml`):
   ```toml
   display_name = "hearing"
   description  = "Meeting transcription & AI copilot (runs on your machine)."
   access       = "private"          # restrict to the owner — see Auth below
   frontend_dir = "frontend/dist"    # Vite build output

   [build]
   install  = ["npm", "--prefix", "frontend", "ci", "--no-audit", "--no-fund"]
   build    = ["npm", "--prefix", "frontend", "run", "build"]
   env_vars = ["VITE_PUBLIC_BASE"]   # deployer injects /hearing/ for asset paths
   ```
   (`frontend/vite.config.ts` already honors `VITE_PUBLIC_BASE`, defaulting to a
   relative base for local use.)

2. **`platform.toml`** in `tt/tw_platform` — add hearing to `app_dirs`
   (path is relative to platform.toml's dir; hearing is a sibling under `t/`):
   ```toml
   app_dirs = [
       "../reelee-web",
       "../../t/thoremin",
       "../../t/hearing",   # ← add this
   ]
   ```
   Then `enlace check` / `enlace list-apps` should show `hearing` mounting at
   `/hearing/`.

## Auth — restricting to thorwhalen@gmail.com only

The platform has auth enabled (`[auth]` in `platform.toml`; sessions + a file
store under `~/.enlace/platform_store`, per-app secrets in a gitignored `.env`).
`access = "private"` gates the app. The exact owner-only mechanism (a shared
password in `.env`, or an email/identity allowlist) is the **one thing to
confirm with the enlace auth config** before going live — set it so only your
session can open `/hearing/`. Until that's confirmed, keep it unpublished.

## Deploying

Once registered, deploy via the tw_platform path (see the `twp-deploy` skill):
```bash
gh workflow run deploy.yml      # GitHub Actions deploy (preferred)
# or the transitional local deploy.py path
```
The deployer runs the `[build]` step (injecting `VITE_PUBLIC_BASE=/hearing/`) and
publishes the static `frontend/dist`. **No backend process and no secrets are
deployed for hearing** — that's the whole point.

## Is the Linux server ready?

For the recommended setup, the server only serves static files, so **Linux vs
macOS is irrelevant** — there's no `hearing` Python process on the server. (If we
ever wanted server-side transcription, faster-whisper/ffmpeg run on Linux fine,
but that would put compute and keys on the server, which this design avoids.)

## Status / next steps

- ✅ Frontend is deploy-ready (relative/`VITE_PUBLIC_BASE` base; static build).
- ✅ Local-compute model works (configurable API base URL in Settings).
- ⏳ Add `app.toml` + register in `tw_platform/platform.toml` (edits the separate
  platform repo).
- ⏳ Confirm the owner-only `access`/auth value, then `gh workflow run deploy.yml`.
