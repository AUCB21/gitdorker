'use client'

export type PillState = 'pending' | 'success' | 'skipped' | 'error'

const STYLES: Record<PillState, string> = {
  pending: 'bg-neutral-900 border-neutral-800 text-neutral-400',
  success: 'bg-emerald-950 border-emerald-900 text-emerald-400',
  skipped: 'bg-neutral-900 border-neutral-800 text-neutral-500',
  error:   'bg-red-950     border-red-900     text-red-400',
}

const DOT: Record<PillState, string> = {
  pending: 'bg-neutral-500 animate-pulse',
  success: 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]',
  skipped: 'bg-neutral-600',
  error:   'bg-red-400',
}

interface Props {
  models: string[]
  states: Record<string, PillState>
}

export function ModelPills({ models, states }: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      {models.map((m) => {
        const state = states[m] ?? 'pending'
        return (
          <span
            key={m}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[10px] font-bold transition-colors ${STYLES[state]}`}
          >
            <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${DOT[state]}`} />
            {m}
          </span>
        )
      })}
    </div>
  )
}
