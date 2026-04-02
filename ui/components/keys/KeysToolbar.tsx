'use client'

import type { Provider, VerifiedKey } from '@/types'

const PROVIDERS: Provider[] = ['anthropic', 'openai', 'google', 'perplexity']

interface Props {
  search: string
  providerFilter: Provider | null
  onSearch: (v: string) => void
  onProviderFilter: (p: Provider | null) => void
  onImport: (keys: VerifiedKey[]) => void
  onExport: () => void
  count: number
}

export function KeysToolbar({ search, providerFilter, onSearch, onProviderFilter, onImport, onExport, count }: Props) {
  function handleImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    file.text().then((raw) => {
      try {
        const json = JSON.parse(raw)
        if (!Array.isArray(json)) return
        // Auto-detect: string[] or VerifiedKey[]
        const keys: VerifiedKey[] = json.map((item) =>
          typeof item === 'string'
            ? { key: item, provider: 'openai' as Provider, models: [], verifiedAt: new Date().toISOString() }
            : item
        )
        onImport(keys)
      } catch {}
    })
    e.target.value = ''
  }

  return (
    <div className="flex flex-wrap gap-3 items-center">
      <input
        type="text"
        value={search}
        onChange={(e) => onSearch(e.target.value)}
        placeholder="Search keys…"
        className="bg-neutral-900 border border-neutral-800 rounded-lg px-3 py-2 text-sm font-mono text-neutral-300 focus:border-amber-500 outline-none transition-colors w-56"
      />

      <div className="flex gap-1">
        <button
          onClick={() => onProviderFilter(null)}
          className={`text-[10px] px-2 py-1 rounded font-bold uppercase tracking-wider border transition-colors
            ${providerFilter === null ? 'bg-neutral-700 border-neutral-600 text-white' : 'bg-neutral-900 border-neutral-800 text-neutral-500 hover:border-neutral-600'}`}
        >
          All
        </button>
        {PROVIDERS.map((p) => (
          <button
            key={p}
            onClick={() => onProviderFilter(p === providerFilter ? null : p)}
            className={`text-[10px] px-2 py-1 rounded font-bold uppercase tracking-wider border transition-colors
              ${providerFilter === p ? 'bg-neutral-700 border-neutral-600 text-white' : 'bg-neutral-900 border-neutral-800 text-neutral-500 hover:border-neutral-600'}`}
          >
            {p}
          </button>
        ))}
      </div>

      <div className="ml-auto flex gap-2">
        <label className="cursor-pointer text-[10px] px-3 py-1.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded font-bold transition-colors">
          Import JSON
          <input type="file" accept=".json" className="hidden" onChange={handleImport} />
        </label>
        <button
          onClick={onExport}
          disabled={count === 0}
          className="text-[10px] px-3 py-1.5 bg-emerald-900/30 hover:bg-emerald-900/50 text-emerald-400 border border-emerald-800 rounded font-bold transition-colors disabled:opacity-50"
        >
          Export {count > 0 ? `(${count})` : ''}
        </button>
      </div>
    </div>
  )
}
