'use client'

interface Props {
  apiKey: string
  model: string
  text: string
  tokens: string
}

export function ResultCard({ apiKey, model, text, tokens }: Props) {
  return (
    <div className="rounded-xl border border-neutral-800 overflow-hidden animate-[fadein_0.3s_ease]">
      <div className="bg-neutral-900 px-4 py-3 border-b border-neutral-800 flex justify-between items-center text-xs font-bold text-neutral-400">
        <span className="flex items-center gap-2">
          <span className="text-neutral-200">{model}</span>
          <span className="font-mono text-neutral-600 font-normal">{apiKey.slice(0, 24)}…</span>
        </span>
        <span className="text-neutral-500 font-normal">{tokens}</span>
      </div>
      <div className="p-4 text-sm leading-relaxed text-neutral-300 whitespace-pre-wrap max-h-[420px] overflow-y-auto bg-[#121212]">
        {text}
      </div>
    </div>
  )
}
