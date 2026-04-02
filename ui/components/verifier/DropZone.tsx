'use client'

import { useRef, useState } from 'react'
import type { VerifiedKey } from '@/types'

interface Props {
  onLoad: (keys: string[]) => void
}

function parseKeysFile(json: unknown): string[] {
  if (!Array.isArray(json)) return []
  return json
    .map((k) => (typeof k === 'string' ? k : (k as VerifiedKey).key ?? ''))
    .filter(Boolean)
}

export function DropZone({ onLoad }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [label, setLabel] = useState('Drop JSON or click to browse')
  const [chip, setChip] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)

  async function loadFile(file: File) {
    try {
      const json = JSON.parse(await file.text())
      const keys = parseKeysFile(json)
      setLabel(file.name)
      setChip(`${keys.length} keys`)
      onLoad(keys)
    } catch {
      setLabel('Invalid JSON — try again')
      setChip(null)
    }
  }

  function clear(e: React.MouseEvent) {
    e.stopPropagation()
    if (inputRef.current) inputRef.current.value = ''
    setLabel('Drop JSON or click to browse')
    setChip(null)
    onLoad([])
  }

  return (
    <div
      className={`border-2 border-dashed rounded-xl p-4 text-center cursor-pointer transition-all relative
        ${dragging ? 'border-neutral-500 bg-neutral-900/50' : 'border-neutral-800 hover:border-neutral-600 hover:bg-neutral-900/50'}`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f) loadFile(f) }}
      onClick={() => inputRef.current?.click()}
    >
      <input ref={inputRef} type="file" accept=".json" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) loadFile(f) }} />
      <div className="text-2xl mb-1 opacity-70">📂</div>
      <p className="text-xs text-neutral-500 font-medium">{label}</p>
      {chip && (
        <div className="mt-2 flex items-center justify-center gap-2">
          <span className="bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider">
            {chip}
          </span>
          <button
            type="button"
            onClick={clear}
            className="text-neutral-500 hover:text-red-400 p-1 bg-neutral-900 rounded-md transition-colors z-10 relative"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
            </svg>
          </button>
        </div>
      )}
    </div>
  )
}
