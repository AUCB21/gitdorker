import type { Provider } from '@/types'

// Slow reasoning/research models need more time; fast models should not block the batch.
const MODEL_TIMEOUTS: Record<string, number> = {
  'o3':                    90_000,
  'o1':                    90_000,
  'sonar-deep-research':   90_000,
  'sonar-reasoning-pro':   45_000,
  'o3-mini':               45_000,
  'o1-mini':               45_000,
}
const DEFAULT_TIMEOUT_MS = 45_000

export function timeoutForModel(model: string): number {
  return MODEL_TIMEOUTS[model] ?? DEFAULT_TIMEOUT_MS
}

export function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  let id: ReturnType<typeof setTimeout>
  const timeout = new Promise<never>((_, reject) => {
    id = setTimeout(() => reject(new Error(`API timeout after ${ms / 1000}s`)), ms)
  })
  return Promise.race([promise, timeout]).finally(() => clearTimeout(id))
}

// Retry once on 429 after a delay — avoids giving up on temporarily rate-limited models
export async function withRetry<T>(fn: () => Promise<T>, delayMs = 5_000): Promise<T> {
  try {
    return await fn()
  } catch (err) {
    if ((err as { status?: number }).status === 429) {
      await new Promise(r => setTimeout(r, delayMs))
      return fn()
    }
    throw err
  }
}

export interface CallResult {
  text: string
  tokens: string
}

async function callViaServer(
  provider: Provider,
  apiKey: string,
  model: string,
  prompt: string,
  maxTokens: number,
): Promise<CallResult> {
  const resp = await fetch('/api/verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider, apiKey, model, prompt, maxTokens }),
  })

  const data = await resp.json() as {
    text?: string
    tokens?: string
    error?: string
    status?: number
    code?: string
  }

  if (!resp.ok) {
    throw Object.assign(
      new Error(data.error ?? `HTTP ${resp.status}`),
      { status: data.status ?? resp.status, code: data.code },
    )
  }

  return { text: data.text ?? '', tokens: data.tokens ?? '' }
}

export const CALLERS: Record<string, (apiKey: string, model: string, prompt: string, maxTokens: number) => Promise<CallResult>> = {
  anthropic:  (k, m, p, t) => callViaServer('anthropic',  k, m, p, t),
  openai:     (k, m, p, t) => callViaServer('openai',     k, m, p, t),
  google:     (k, m, p, t) => callViaServer('google',     k, m, p, t),
  perplexity: (k, m, p, t) => callViaServer('perplexity', k, m, p, t),
}
