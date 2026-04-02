'use client'

import { useRef, useState } from 'react'
import { DropZone } from './DropZone'
import { ModelPills, type PillState } from './ModelPills'
import { ProviderBadge } from './ProviderBadge'
import { ResultCard } from './ResultCard'
import { detectProvider, PROVIDERS } from '@/lib/providers'
import { CALLERS, withTimeout, timeoutForModel } from '@/lib/callers'
import { shouldSkip } from '@/lib/placeholder'
import { mergeKey } from '@/lib/storage'
import type { Provider, VerifiedKey } from '@/types'

const CONCURRENT_KEYS = 1

async function runPool(tasks: (() => Promise<void>)[]): Promise<void> {
  const queue = [...tasks]
  const workers = Array.from({ length: Math.min(CONCURRENT_KEYS, queue.length) }, async () => {
    while (queue.length > 0) {
      const task = queue.shift()!
      await task()
    }
  })
  await Promise.all(workers)
}

interface KeyRunState {
  key: string
  provider: Provider
  pillStates: Record<string, PillState>
  errorMessages: Record<string, string>
}

interface ResultEntry {
  apiKey: string
  model: string
  text: string
  tokens: string
}

export function VerifierTab({ onKeySaved }: { onKeySaved?: () => void }) {
  const [singleKey, setSingleKey] = useState('')
  const [batchKeys, setBatchKeys] = useState<string[]>([])
  const [prompt, setPrompt] = useState('')
  const [maxTokens, setMaxTokens] = useState(1024)
  const [running, setRunning] = useState(false)
  const [runStates, setRunStates] = useState<KeyRunState[]>([])
  const [results, setResults] = useState<ResultEntry[]>([])
  const [workingKeys, setWorkingKeys] = useState<VerifiedKey[]>([])
  const [savedCount, setSavedCount] = useState(0)
  const [runningCount, setRunningCount] = useState(0)
  const [completedCount, setCompletedCount] = useState(0)
  const abortRef = useRef<AbortController | null>(null)

  const detectedProvider = detectProvider(singleKey)
  const activeKeys = batchKeys.length > 0 ? batchKeys : [singleKey]

  function setPillState(apiKey: string, model: string, state: PillState, errorMessage?: string) {
    setRunStates((prev) => prev.map((rs) => {
      if (rs.key !== apiKey) return rs
      return {
        ...rs,
        pillStates: { ...rs.pillStates, [model]: state },
        errorMessages: errorMessage
          ? { ...rs.errorMessages, [model]: errorMessage }
          : rs.errorMessages,
      }
    }))
  }

  async function runSingleKey(apiKey: string, signal: AbortSignal): Promise<string[]> {
    const provider = detectProvider(apiKey)
    if (!provider) return []
    const models = PROVIDERS[provider].models
    const succeeded: string[] = []

    await Promise.allSettled(
      models.map(async (model) => {
        if (signal.aborted) return
        try {
          const { text, tokens } = await withTimeout(CALLERS[provider](apiKey, model, prompt, maxTokens), timeoutForModel(model))
          setPillState(apiKey, model, 'success')
          setResults((prev) => [...prev, { apiKey, model, text, tokens }])
          succeeded.push(model)
        } catch (err) {
          const errMsg = err instanceof Error ? err.message : String(err)
          setPillState(apiKey, model, shouldSkip(err) ? 'skipped' : 'error', errMsg)
        }
      })
    )
    return succeeded
  }

  async function run() {
    if (!prompt.trim()) return
    const keys = [...new Set(activeKeys.filter(Boolean))]
    if (keys.length === 0) return

    abortRef.current = new AbortController()
    const { signal } = abortRef.current

    setRunning(true)
    setRunningCount(keys.length)
    setCompletedCount(0)
    setResults([])
    setWorkingKeys([])
    setSavedCount(0)
    setRunStates([])

    await runPool(
      keys.map((apiKey) => async () => {
        if (signal.aborted) return
        const provider = detectProvider(apiKey)
        if (!provider) return

        // Add this key's row the moment it starts — 1 row at a time
        const pillStates: Record<string, PillState> = {}
        PROVIDERS[provider].models.forEach((m) => { pillStates[m] = 'pending' })
        setRunStates((prev) => [...prev, { key: apiKey, provider, pillStates, errorMessages: {} }])

        const succeeded = await runSingleKey(apiKey, signal)
        setCompletedCount((n) => n + 1)

        if (succeeded.length > 0) {
          const entry: VerifiedKey = { key: apiKey, provider, models: succeeded, verifiedAt: new Date().toISOString() }
          setWorkingKeys((prev) => prev.some((k) => k.key === apiKey) ? prev : [...prev, entry])
        } else {
          // Key had no working models — remove its row
          setRunStates((prev) => prev.filter((rs) => rs.key !== apiKey))
        }
      })
    )
    setRunning(false)
    abortRef.current = null
  }

  function stop() {
    abortRef.current?.abort()
  }

  function saveToVault() {
    workingKeys.forEach((k) => mergeKey(k))
    setSavedCount(workingKeys.length)
    onKeySaved?.()
  }

  function downloadJSON() {
    const blob = new Blob([JSON.stringify(workingKeys, null, 2)], { type: 'application/json' })
    const a = Object.assign(document.createElement('a'), {
      href: URL.createObjectURL(blob),
      download: 'working_keys.json',
    })
    a.click()
    URL.revokeObjectURL(a.href)
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Config sidebar */}
        <aside className="lg:col-span-4 space-y-4">
          <div className="bg-[#121212] border border-neutral-800 rounded-xl p-5 space-y-5">
            <h2 className="text-[10px] font-bold text-neutral-400 uppercase tracking-widest">Configuration</h2>

            {/* API Key */}
            <div className="space-y-1.5 relative">
              <label className="text-[10px] font-bold text-neutral-500 uppercase tracking-wide block">API Key</label>
              <input
                type="password"
                value={singleKey}
                onChange={(e) => setSingleKey(e.target.value)}
                placeholder="sk-ant-… / sk-proj-… / AIza… / pplx-…"
                autoComplete="off"
                className="w-full bg-neutral-900 border border-neutral-800 rounded-lg px-3 py-2.5 text-sm focus:border-amber-500 outline-none transition-colors font-mono pr-24"
              />
              {detectedProvider && (
                <div className="absolute right-2 top-[30px]">
                  <ProviderBadge provider={detectedProvider} />
                </div>
              )}
            </div>

            {/* Max Tokens */}
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-neutral-500 uppercase tracking-wide block">Max Tokens</label>
              <input
                type="number"
                value={maxTokens}
                min={1}
                max={8192}
                onChange={(e) => setMaxTokens(parseInt(e.target.value) || 1024)}
                className="w-full bg-neutral-900 border border-neutral-800 rounded-lg px-3 py-2.5 text-sm focus:border-amber-500 outline-none transition-colors font-mono"
              />
            </div>

            {/* Drop Zone */}
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-neutral-500 uppercase tracking-wide block">Batch Keys (keys.json)</label>
              <DropZone onLoad={(keys) => { setBatchKeys(keys); if (keys[0]) setSingleKey(keys[0]) }} />
            </div>
          </div>

          {/* Working Keys panel */}
          {workingKeys.length > 0 && (
            <div className="bg-[#121212] border border-neutral-800 rounded-xl p-5 space-y-3">
              <h2 className="text-[10px] font-bold text-neutral-400 uppercase tracking-widest">Working Keys</h2>
              <div className="flex flex-col gap-2">
                <button
                  onClick={downloadJSON}
                  className="w-full bg-emerald-900/30 text-emerald-400 border border-emerald-800 rounded-lg py-2 text-xs font-bold hover:bg-emerald-900/50 transition-colors"
                >
                  Download {workingKeys.length} key{workingKeys.length > 1 ? 's' : ''} (JSON)
                </button>
                <button
                  onClick={saveToVault}
                  disabled={savedCount > 0}
                  className="w-full bg-blue-900/30 text-blue-400 border border-blue-800 rounded-lg py-2 text-xs font-bold hover:bg-blue-900/50 transition-colors disabled:opacity-50"
                >
                  {savedCount > 0 ? `✓ ${savedCount} key${savedCount > 1 ? 's' : ''} saved to vault` : 'Save to vault'}
                </button>
              </div>
            </div>
          )}
        </aside>

        {/* Main workspace */}
        <main className="lg:col-span-8 space-y-6">
          <div className="bg-[#121212] border border-neutral-800 rounded-xl p-6">
            <label className="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-2 block">Prompt</label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && !running) run() }}
              placeholder="Enter your instructions here…"
              className="w-full min-h-[160px] bg-neutral-900 border border-neutral-800 rounded-xl p-4 text-sm focus:border-amber-500 outline-none transition-all resize-y leading-relaxed"
            />
            <div className="mt-4 flex gap-3">
              <button
                onClick={run}
                disabled={running}
                className="flex-1 bg-amber-500 hover:bg-amber-400 text-black font-bold py-3.5 rounded-xl transition-all shadow-lg shadow-amber-500/10 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {running
                  ? runningCount > 1
                    ? `${completedCount} / ${runningCount} keys · ${workingKeys.length} working`
                    : 'Running…'
                  : 'Run'}
              </button>
              {running && (
                <button
                  onClick={stop}
                  className="px-5 bg-red-900/40 hover:bg-red-900/70 text-red-400 border border-red-800/60 font-bold py-3.5 rounded-xl transition-all"
                >
                  Stop
                </button>
              )}
            </div>
          </div>

          {/* Model status — grows one row at a time, failed keys drop out */}
          {runStates.length > 0 && (
            <div className="bg-[#121212] border border-neutral-800 rounded-xl p-5 space-y-3">
              {runStates.map((rs, i) => (
                <div key={rs.key} className={`space-y-2 ${i > 0 ? 'pt-2 border-t border-neutral-800' : ''}`}>
                  {batchKeys.length > 1 && (
                    <span className="text-xs font-bold text-neutral-500 font-mono">{rs.key.slice(0, 32)}…</span>
                  )}
                  <ModelPills models={PROVIDERS[rs.provider].models} states={rs.pillStates} errorMessages={rs.errorMessages} />
                </div>
              ))}
            </div>
          )}
        </main>
      </div>

      {/* Results grid */}
      {results.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {results.map((r, i) => (
            <ResultCard key={i} apiKey={r.apiKey} model={r.model} text={r.text} tokens={r.tokens} />
          ))}
        </div>
      )}

      {/* No results message */}
      {!running && completedCount > 0 && results.length === 0 && (
        <div className="text-red-400 text-sm font-medium bg-red-950/30 border border-red-900/50 p-4 rounded-xl text-center">
          No models returned a valid response.
        </div>
      )}
    </div>
  )
}
