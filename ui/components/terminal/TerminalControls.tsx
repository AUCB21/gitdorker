'use client'

import { useEffect, useState } from 'react'
import type { Dork } from '@/types'

interface Props {
  running: boolean
  onRun: (args: string[]) => void
  onStop: () => void
}

export function TerminalControls({ running, onRun, onStop }: Props) {
  const [dorks, setDorks] = useState<Dork[]>([])
  const [query, setQuery] = useState('')
  const [maxResults, setMaxResults] = useState(10)
  const [loop, setLoop] = useState(false)

  useEffect(() => {
    fetch('/api/dorks')
      .then((r) => r.json())
      .then((data: Dork[]) => setDorks(data))
      .catch(() => {})
  }, [])

  function buildArgs(): string[] {
    const args: string[] = []
    if (query) args.push('-q', query)
    if (maxResults) args.push('-n', String(maxResults))
    if (loop) args.push('--loop')
    return args
  }

  return (
    <div className="bg-[#121212] border border-neutral-800 rounded-xl p-5 space-y-4">
      <h2 className="text-[10px] font-bold text-neutral-400 uppercase tracking-widest">Terminal Controls</h2>

      {/* Dork picker */}
      <div className="space-y-1.5">
        <label className="text-[10px] font-bold text-neutral-500 uppercase tracking-wide block">Dork Query</label>
        <select
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full bg-neutral-900 border border-neutral-800 rounded-lg px-3 py-2.5 text-sm text-neutral-300 focus:border-amber-500 outline-none transition-colors"
        >
          <option value="">— custom / none —</option>
          {dorks.map((d, i) => (
            <option key={i} value={d.query}>{d.query}</option>
          ))}
        </select>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="or type a custom query…"
          className="w-full bg-neutral-900 border border-neutral-800 rounded-lg px-3 py-2 text-sm font-mono text-neutral-300 focus:border-amber-500 outline-none transition-colors"
        />
      </div>

      {/* Max results */}
      <div className="space-y-1.5">
        <label className="text-[10px] font-bold text-neutral-500 uppercase tracking-wide block">Max Results</label>
        <input
          type="number"
          value={maxResults}
          min={1}
          max={500}
          onChange={(e) => setMaxResults(parseInt(e.target.value) || 10)}
          className="w-full bg-neutral-900 border border-neutral-800 rounded-lg px-3 py-2.5 text-sm font-mono focus:border-amber-500 outline-none transition-colors"
        />
      </div>

      {/* Loop toggle */}
      <label className="flex items-center gap-2 cursor-pointer select-none">
        <input type="checkbox" checked={loop} onChange={(e) => setLoop(e.target.checked)} className="accent-amber-500" />
        <span className="text-xs text-neutral-400">Loop continuously</span>
      </label>

      {/* Run / Stop */}
      <div className="flex gap-3">
        <button
          onClick={() => onRun(buildArgs())}
          disabled={running}
          className="flex-1 bg-amber-500 hover:bg-amber-400 text-black font-bold py-3 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed text-sm"
        >
          Run
        </button>
        {running && (
          <button
            onClick={onStop}
            className="px-5 bg-red-900/40 hover:bg-red-900/70 text-red-400 border border-red-800/60 font-bold py-3 rounded-xl transition-all text-sm"
          >
            Stop
          </button>
        )}
      </div>
    </div>
  )
}
