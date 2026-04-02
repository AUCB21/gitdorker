'use client'

import type { Provider } from '@/types'
import { PROVIDERS } from '@/lib/providers'

const STYLES: Record<Provider, string> = {
  anthropic:  'bg-amber-950   text-amber-400   border-amber-900',
  openai:     'bg-emerald-950 text-emerald-400 border-emerald-900',
  google:     'bg-blue-950    text-blue-400    border-blue-900',
  perplexity: 'bg-purple-950  text-purple-400  border-purple-900',
}

export function ProviderBadge({ provider }: { provider: Provider }) {
  return (
    <span className={`inline-block text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded border ${STYLES[provider]}`}>
      {PROVIDERS[provider].label}
    </span>
  )
}
