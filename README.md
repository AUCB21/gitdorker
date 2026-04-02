# gitdorker

GitHub secret scanner — searches public repositories for exposed LLM API keys and generates disclosure reports.

---

## What it does

gitdorker runs targeted GitHub search queries ("dorks") against the GitHub Search API, extracts credential patterns from matching files, verifies them live against their respective APIs, and writes structured Markdown disclosure reports for every confirmed valid key found.

**Supported providers (17):**
Anthropic · OpenAI · Google Gemini · Perplexity · Groq · Replicate · HuggingFace · xAI · DeepSeek · OpenRouter · Fireworks · Cohere · Mistral · Together AI · NVIDIA NIM · Cerebras · Azure OpenAI

---

## Install

Requires Python 3.13+.

```bash
git clone https://github.com/<you>/gitdorker
cd gitdorker
pip install -e .
```

Set your GitHub token (needs `public_repo` read scope) in any of these ways:

```bash
# Option A — .env file (recommended)
echo "GITHUB_TOKEN=ghp_..." > .env

# Option B — environment variable
export GITHUB_TOKEN=ghp_...

# Option C — enter it interactively when prompted
```

---

## Usage

### Interactive wizard (recommended)

```bash
gitdorker
```

Launches a guided 6-step setup:

```
Step 1 — GitHub Token       detect env token or enter manually
Step 2 — Search Source      dorks file or single query
Step 3 — Dorks File         path to JSON (defaults to dorks.json)
Step 4 — Output dir         where to write reports (default: reports/)
Step 5 — Limits             max results per dork (default: all, cap 1000)
Step 6 — Loop Mode          continuous scanning with configurable delay
```

### Headless / scripted

```bash
# Run all 43 built-in dorks
gitdorker --dorks-file dorks.json --token ghp_...

# Single query
gitdorker --query "sk-ant-api03-" --token ghp_...

# Continuous loop, 10 min between cycles
gitdorker --dorks-file dorks.json --loop --loop-delay 600

# Limit results, verbose logging
gitdorker --dorks-file dorks.json --max-results 100 --verbose
```

### All options

```
-f, --dorks-file PATH     JSON file with dork definitions
-q, --query TEXT          Single search query
-t, --type                Search type: code | repositories | commits  [default: code]
    --token TEXT          GitHub PAT (or set GITHUB_TOKEN)
-o, --output-dir PATH     Report output directory  [default: reports/]
-n, --max-results INT     Max results per dork  [default: all]
-l, --loop                Run continuously until Ctrl+C
    --loop-delay INT      Seconds between loop cycles  [default: 300]
-v, --verbose             DEBUG-level logging to log file
```

---

## Output

**Reports** — written to `reports/` as Markdown files, one per unique repo:

```
reports/
  owner__repo__query.md
```

Each report includes: repository URL, file path, matched content, extracted credential (redacted in display, present for disclosure), and remediation steps.

**Logs** — written to `logs/gitdorker_YYYYMMDD_HHMMSS.log` on every run.

---

## Dorks file format

```json
{
  "dorks": [
    {
      "query": "sk-ant-api03-",
      "type": "code",
      "description": "Anthropic Claude API key (v3 format)",
      "remediation": "Revoke at console.anthropic.com → API Keys."
    }
  ]
}
```

`type` is one of `code`, `repositories`, or `commits`. See `dorks.example.json` for a full template.

---

## Web UI

A standalone HTML key verifier is included at `web/index.html` — open it directly in a browser (no server needed). Paste or batch-load keys, run a prompt against all supported models, and save working keys to a local vault.

---

## Legal

This tool is intended for **authorized security research and responsible disclosure** only. Only scan repositories you are permitted to test. Report any valid credentials you find to the affected party before public disclosure. Misuse may violate GitHub's Terms of Service and applicable law.
