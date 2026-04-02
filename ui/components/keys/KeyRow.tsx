'use client'

import { ProviderBadge } from '@/components/verifier/ProviderBadge'
import type { VerifiedKey } from '@/types'

interface Props {
  entry: VerifiedKey
  onDelete: (key: string) => void
}

export function KeyRow({ entry, onDelete }: Props) {
  function copy() {
    navigator.clipboard.writeText(entry.key)
  }

  return (
    <tr className="border-b border-neutral-800 hover:bg-neutral-900/40 transition-colors">
      <td className="px-4 py-3">
        <ProviderBadge provider={entry.provider} />
      </td>
      <td className="px-4 py-3 font-mono text-xs text-neutral-300">
        {entry.key.slice(0, 20)}…{entry.key.slice(-4)}
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-wrap gap-1">
          {entry.models.map((m) => (
            <span key={m} className="text-[10px] bg-neutral-800 text-neutral-400 px-1.5 py-0.5 rounded font-mono">
              {m}
            </span>
          ))}
        </div>
      </td>
      <td className="px-4 py-3 text-[10px] text-neutral-600 font-mono">
        {entry.verifiedAt ? new Date(entry.verifiedAt).toLocaleDateString() : '—'}
      </td>
      <td className="px-4 py-3">
        <div className="flex gap-2 justify-end">
          <button
            onClick={copy}
            className="text-[10px] px-2 py-1 bg-neutral-800 hover:bg-neutral-700 text-neutral-400 rounded transition-colors font-bold"
          >
            Copy
          </button>
          <button
            onClick={() => onDelete(entry.key)}
            className="text-[10px] px-2 py-1 bg-red-950/40 hover:bg-red-950/80 text-red-400 border border-red-900/50 rounded transition-colors font-bold"
          >
            Delete
          </button>
        </div>
      </td>
    </tr>
  )
}
