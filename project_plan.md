# Project Plan: gitdorker Web UI → Next.js 14

## Discovery Summary
- **Type**: Web App (Full Stack, internal tool)
- **Goal**: Migrate vanilla HTML key verifier + add in-browser gitdorker terminal + key vault into one Next.js app
- **Scope**: MVP — Verifier tab, Terminal tab, Keys tab. No auth, no DB.
- **Constraints**: Next.js 14 App Router, TypeScript, Tailwind, shadcn/ui. localStorage only. Python CLI spawned server-side via child_process.

---

## Recommended Stack

| Layer | Technology | Why |
|---|---|---|
| Framework | Next.js 14 App Router | SSR for API routes; client components for interactive UI |
| Language | TypeScript | Type-safe key/model schemas across all 3 tabs |
| Styling | Tailwind CSS + shadcn/ui | Dark theme tokens match existing palette; tabs/badges built-in |
| Terminal | xterm.js + xterm-addon-fit | Industry standard browser terminal; SSE-compatible |
| State | React useState + localStorage | No DB needed; keys persist across sessions |
| Process | Node child_process (API route) | Spawn Python CLI, stream SSE to browser |
| Deployment | Vercel (or self-host) | Zero-config Next.js; SSE supported on Pro plan |

---

## Core Data Models

```ts
// Shared across all tabs — types.ts
type Provider = 'anthropic' | 'openai' | 'google' | 'perplexity'

interface VerifiedKey {
  key: string         // full key value
  provider: Provider
  models: string[]    // models that responded successfully
  verifiedAt: string  // ISO timestamp
}

// Download/upload format (replaces current string[] format)
type KeysFile = VerifiedKey[]
```

---

## Architecture

```
app/
  page.tsx                  ← Tab shell (Verifier | Terminal | Keys)
  api/
    run/route.ts            ← SSE: spawns gitdorker Python process
    keys/route.ts           ← GET/POST localStorage-compatible endpoint (optional)

components/
  verifier/
    VerifierTab.tsx         ← Ported HTML/JS logic
    DropZone.tsx            ← Drag-drop file input
    ProviderBadge.tsx       ← Colored pill
    ResultCard.tsx          ← Per-model result
    ModelPills.tsx          ← Pending/success/error pills
  terminal/
    TerminalTab.tsx         ← xterm.js shell
    TerminalControls.tsx    ← Dorks picker, flags, run/stop button
  keys/
    KeysTab.tsx             ← Key vault table
    KeyRow.tsx              ← Key + provider badge + model chips
    KeysToolbar.tsx         ← Import / export / filter

lib/
  providers.ts              ← PROVIDERS config (models, detect, caller fns)
  callers.ts                ← callAnthropic / callOpenAI / callGoogle / callPerplexity
  storage.ts                ← localStorage get/set typed wrappers
  placeholder.ts            ← shouldSkip() error classifier

types.ts                    ← VerifiedKey, Provider, etc.
```

---

## Data Flow

```
[1] Verifier: key input → detectProvider → runKey (parallel Promise.allSettled)
    → appendResult → workingKeys[].models.push(model) → export VerifiedKey[]

[2] Terminal: user clicks Run → POST /api/run → child_process.spawn(gitdorker)
    → stdout/stderr piped as SSE chunks → xterm.js writes to screen
    → Ctrl+C → AbortController → SIGINT sent to child

[3] Keys tab: reads localStorage["gd_keys"] (VerifiedKey[])
    ← populated by Verifier "Save to vault" or file upload
    → filter/export subset as JSON
```

---

## Phase -1 — Repo hygiene (do before any commit)

- [ ] **`.gitignore`**: add `env/`, `*.log`, `logs/`, `reports/`, `.env`, `node_modules/`, `.next/`, `__pycache__/`, `.pytest_cache/`, `*.pyc` — the live `GITHUB_TOKEN` in `.env` is currently untracked and will leak on first push
- [ ] **Python lockfile**: run `pip freeze > requirements.txt` (or `uv pip freeze`) inside the `env/` venv so deployments are reproducible; `pyproject.toml` alone is insufficient without a lock
- [ ] Confirm `.env` is listed in `.gitignore` and not staged

---

## Phase 0 — HTML-first patches (web/index.html, no Next.js yet)

- [ ] **Download format**: change `workingKeys` from `{key, model}[]` to `{key, provider, models[]}[]` — merge models per key on success
- [ ] **Export**: `JSON.stringify(workingKeys)` now exports `VerifiedKey[]` schema; add `verifiedAt: new Date().toISOString()` to each entry
- [ ] **DropZone**: replace `<input type="file">` with styled drag-drop zone (CSS + dragover/drop handlers), filename chip, clear button
- [ ] Verify both changes work end-to-end in browser before proceeding

---

## Phase 1 — Next.js scaffold

- [ ] `npx create-next-app@latest gitdorker-ui --typescript --tailwind --app --no-src-dir --import-alias "@/*"`
- [ ] `npx shadcn@latest init` — select dark theme, CSS variables
- [ ] Install deps: `npm i xterm xterm-addon-fit xterm-addon-web-links`
- [ ] Install shadcn components: `npx shadcn@latest add tabs badge button card input`
- [ ] Create `types.ts` with `VerifiedKey`, `Provider` types
- [ ] Create `.env.example` documenting `PYTHON_BIN`, `GITDORKER_REPORTS_DIR`
- [ ] Create `find-python.ts` helper in `lib/` — resolves Python binary: checks `PYTHON_BIN` env var → `env/` venv relative path → `which python3` fallback; used by `/api/run/route.ts`
- [ ] Confirm `next build` passes with empty shell

---

## Phase 2 — lib layer

- [ ] `lib/providers.ts` — PROVIDERS config object (detect fn, models[], label, color)
- [ ] `lib/callers.ts` — `callAnthropic`, `callOpenAI`, `callGoogle`, `callPerplexity` (ported from index.html, typed)
- [ ] `lib/storage.ts` — `getKeys(): VerifiedKey[]`, `saveKeys(keys)`, `mergeKey(k: VerifiedKey)` using localStorage
- [ ] `lib/placeholder.ts` — `shouldSkip(err)` error classifier
- [ ] `lib/find-python.ts` — resolve Python binary: `PYTHON_BIN` env → `./env/Scripts/python` (Windows) / `./env/bin/python` (Unix) → `which python3`
- [ ] `lib/dorks.ts` — `loadDorks(): Dork[]` reads `dorks.json` via `fs.readFileSync` (Node-only, imported only in API routes); export `Dork` type matching `config.py` schema
- [ ] Run `tsc --noEmit` — 0 errors before Phase 3

---

## Phase 3 — Verifier tab

- [ ] `components/verifier/DropZone.tsx` — drag-drop zone, filename chip, clear button, `onLoad(keys: string[])` callback
- [ ] `components/verifier/ProviderBadge.tsx` — colored pill per provider
- [ ] `components/verifier/ModelPills.tsx` — pending/success/skipped/error states with pulse animation
- [ ] `components/verifier/ResultCard.tsx` — model name + key prefix + token count + response body
- [ ] `components/verifier/VerifierTab.tsx` — orchestrates state: `workingKeys: VerifiedKey[]`, runs batch loop, calls `mergeKey` on success
- [ ] Wire "Save to vault" button → `storage.mergeKey()`
- [ ] Wire download button → exports `VerifiedKey[]` JSON
- [ ] Visual parity test vs current index.html

---

## Phase 4 — Terminal tab

- [ ] `app/api/run/route.ts` — POST handler: reads body `{args: string[]}`, spawns Python via `lib/find-python.ts`, pipes stdout+stderr as `text/event-stream` SSE, handles `AbortSignal` → `child.kill('SIGINT')`; add `export const runtime = 'nodejs'` (not Edge runtime — child_process requires Node)
- [ ] `app/api/dorks/route.ts` — GET handler: returns `loadDorks()` as JSON; used by TerminalControls to populate dork picker without bundling JSON client-side
- [ ] `components/terminal/TerminalControls.tsx` — dorks file picker (fetches `/api/dorks`), max-results input, loop toggle, Run/Stop button
- [ ] `components/terminal/TerminalTab.tsx` — mounts xterm.js (`dynamic(..., {ssr: false})`), opens `EventSource` to `/api/run`, writes chunks to terminal, fit addon on resize
- [ ] Test: run `gitdorker -q "AIzaSy" -n 5` from browser, see output stream in xterm
- [ ] Test Ctrl+C: terminal sends abort, Python process exits cleanly

---

## Phase 5 — Keys tab

- [ ] `components/keys/KeyRow.tsx` — key prefix (truncated), `ProviderBadge`, model chips, copy button, delete button
- [ ] `components/keys/KeysToolbar.tsx` — search/filter input, provider filter chips, "Import JSON" button, "Export selected" button
- [ ] `components/keys/KeysTab.tsx` — reads from `storage.getKeys()`, renders rows, handles import (merges, deduplicates by key value)
- [ ] Import: accepts both old `string[]` format and new `VerifiedKey[]` format (auto-detects)
- [ ] Export: filtered subset as `VerifiedKey[]` JSON download

---

## Phase 6 — Tab shell + integration

- [ ] `app/page.tsx` — shadcn `<Tabs>` shell with `[Verifier, Terminal, Keys]`
- [ ] Verifier → Keys flow: after run, banner "N keys saved to vault" with link to Keys tab
- [ ] Keys tab badge: show count of stored keys in tab label
- [ ] Terminal → Keys flow: post-run, parse reports dir for new findings (optional stretch)
- [ ] `next build` — 0 errors, 0 type errors
- [ ] `next lint` — 0 warnings

---

## Phase 8 — CI/CD & Deployment config

- [ ] `.github/workflows/ci.yml` — on push/PR: `pytest` (Python), `tsc --noEmit`, `next lint`, `next build`
- [ ] `vercel.json` — set `functions["app/api/run/route.ts"].maxDuration = 300` (or max allowed on plan) to prevent SSE timeout killing long gitdorker runs
- [ ] Document in `README.md`: Vercel free tier has 60s function timeout; SSE terminal tab requires Vercel Pro or self-hosting
- [ ] `README.md` — installation (Python venv setup + `npm install`), `.env` configuration, `next dev` usage, JSON schema for `VerifiedKey`, deployment options

---

## Phase 7 — Polish

- [ ] Empty states for all 3 tabs (no keys loaded, no terminal run yet, vault empty)
- [ ] Error boundaries around VerifierTab and TerminalTab
- [ ] Keyboard shortcut: Ctrl+Enter runs verifier (matches current behavior)
- [ ] DropZone accepts both `keys.json` (string[]) and `VerifiedKey[]` format
- [ ] Mobile-responsive layout (tabs stack vertically on small screens)
- [ ] `README.md` update: document new JSON schema, setup steps, Python path config

---

## Pre-Completion Verification

- [ ] `tsc --noEmit` — 0 errors
- [ ] `next lint` — 0 warnings
- [ ] `next build` — successful production build
- [ ] `pytest` — all Python tests pass
- [ ] `.env.example` documents `PYTHON_BIN`, `GITDORKER_REPORTS_DIR`
- [ ] `.gitignore` covers `env/`, `.env`, `logs/`, `reports/`, `.next/`, `node_modules/`
- [ ] No secrets hardcoded anywhere; `.env` not committed
- [ ] `requirements.txt` (or lockfile) present and up-to-date
- [ ] Verifier produces `VerifiedKey[]` download with `verifiedAt` field
- [ ] Terminal streams gitdorker output in real-time; SSE runtime is `nodejs` (not Edge)
- [ ] Keys tab persists across page reload
- [ ] Old `web/index.html` Phase 0 patches ship independently (no Next.js dependency)
- [ ] `vercel.json` sets `maxDuration` for `/api/run` route
- [ ] `README.md` covers setup, `.env` config, Python venv, deployment caveats

---

## Potential Challenges

| Challenge | Mitigation |
|---|---|
| SSE + Vercel timeout (60s default) | Self-host or use Vercel Pro; set `maxDuration` in `vercel.json` |
| xterm.js SSR | `dynamic(() => import('./TerminalTab'), { ssr: false })` |
| child_process not available on Edge runtime | Force `export const runtime = 'nodejs'` on `/api/run/route.ts` |
| Perplexity CORS from browser | Already works via esm.sh SDK with `dangerouslyAllowBrowser`; no change needed |
| Old `string[]` key files | Phase 5 import auto-detects format and upcasts to `VerifiedKey[]` |
| Python binary resolution across OS/venv | `lib/find-python.ts` checks `PYTHON_BIN` → venv path → `which python3` |
| `dorks.json` access from browser | Served via `/api/dorks` GET route using `fs.readFileSync`; never bundled client-side |
| `.env` with live token accidentally committed | Phase -1: `.gitignore` + verify not staged before any push |
| Deployment reproducibility (Python deps) | `requirements.txt` generated from venv; committed alongside `pyproject.toml` |
