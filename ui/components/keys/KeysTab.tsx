'use client'

import { useSyncExternalStore } from 'react'
import { useState } from 'react'
import { KeyRow } from './KeyRow'
import { KeysToolbar } from './KeysToolbar'
import { getKeys, saveKeys, deleteKey } from '@/lib/storage'
import type { Provider, VerifiedKey } from '@/types'

// Minimal external store backed by localStorage
function subscribe(cb: () => void) {
  window.addEventListener('storage', cb)
  return () => window.removeEventListener('storage', cb)
}

function useVaultKeys(): [VerifiedKey[], () => void] {
  const keys = useSyncExternalStore(subscribe, getKeys, () => [])
  function refresh() {
    // Dispatch a synthetic storage event to re-run subscribers
    window.dispatchEvent(new Event('storage'))
  }
  return [keys, refresh]
}

// refreshSignal prop kept for API compatibility; vault auto-refreshes via useSyncExternalStore
export function KeysTab({ refreshSignal: _ = 0 }: { refreshSignal?: number }) {
  const [keys, refresh] = useVaultKeys()
  const [search, setSearch] = useState('')
  const [providerFilter, setProviderFilter] = useState<Provider | null>(null)

  function handleDelete(key: string) {
    deleteKey(key)
    refresh()
  }

  function handleImport(incoming: VerifiedKey[]) {
    const current = getKeys()
    incoming.forEach((k) => {
      const idx = current.findIndex((c) => c.key === k.key)
      if (idx >= 0) {
        k.models.forEach((m) => { if (!current[idx].models.includes(m)) current[idx].models.push(m) })
      } else {
        current.push(k)
      }
    })
    saveKeys(current)
    refresh()
  }

  const filtered = keys.filter((k) => {
    if (providerFilter && k.provider !== providerFilter) return false
    if (search && !k.key.includes(search)) return false
    return true
  })

  function handleExport() {
    const blob = new Blob([JSON.stringify(filtered, null, 2)], { type: 'application/json' })
    const a = Object.assign(document.createElement('a'), {
      href: URL.createObjectURL(blob),
      download: 'keys_export.json',
    })
    a.click()
    URL.revokeObjectURL(a.href)
  }

  if (keys.length === 0) {
    return (
      <div className="text-center py-20 text-neutral-600">
        <div className="text-4xl mb-3">🔑</div>
        <p className="text-sm font-medium">No keys in vault yet.</p>
        <p className="text-xs mt-1">Run the Verifier and click &quot;Save to vault&quot;, or import a JSON file.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <KeysToolbar
        search={search}
        providerFilter={providerFilter}
        onSearch={setSearch}
        onProviderFilter={setProviderFilter}
        onImport={handleImport}
        onExport={handleExport}
        count={filtered.length}
      />

      <div className="bg-[#121212] border border-neutral-800 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-neutral-800 text-[10px] text-neutral-500 uppercase tracking-widest">
              <th className="px-4 py-3 text-left font-bold">Provider</th>
              <th className="px-4 py-3 text-left font-bold">Key</th>
              <th className="px-4 py-3 text-left font-bold">Models</th>
              <th className="px-4 py-3 text-left font-bold">Verified</th>
              <th className="px-4 py-3 text-right font-bold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-neutral-600 text-xs">
                  No keys match the current filter.
                </td>
              </tr>
            ) : (
              filtered.map((k) => (
                <KeyRow key={k.key} entry={k} onDelete={handleDelete} />
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
