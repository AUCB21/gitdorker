import type { Provider } from '@/types'

interface ProviderConfig {
  label: string
  color: string
  detect: (key: string) => boolean
  models: string[]
}

export const PROVIDERS: Record<Provider, ProviderConfig> = {
  anthropic: {
    label: 'Anthropic',
    color: 'amber',
    detect: (k) => k.startsWith('sk-ant-'),
    models: [
      'claude-opus-4-6',
      'claude-sonnet-4-6',
      'claude-haiku-4-5-20251001',
      'claude-3-5-sonnet-20241022',
      'claude-3-5-haiku-20241022',
      'claude-3-opus-20240229',
      'claude-3-sonnet-20240229',
      'claude-3-haiku-20240307',
    ],
  },
  openai: {
    label: 'OpenAI',
    color: 'emerald',
    detect: (k) => k.startsWith('sk-proj-') || k.startsWith('sk-'),
    models: ['gpt-4o', 'gpt-4o-mini', 'o3', 'o3-mini', 'o1', 'o1-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
  },
  google: {
    label: 'Gemini',
    color: 'blue',
    detect: (k) => k.startsWith('AIza'),
    models: [
      'gemini-2.5-flash',
      'gemini-2.5-flash-lite',
      'gemini-2.5-pro',
      'gemini-3.1-pro-preview',
      'gemini-3-flash-preview',
      'gemini-3.1-flash-lite-preview',
      'gemini-2.0-flash',
      'gemini-2.0-flash-lite',
      'gemini-1.5-pro',
    ],
  },
  perplexity: {
    label: 'Perplexity',
    color: 'purple',
    detect: (k) => k.startsWith('pplx-'),
    models: ['sonar', 'sonar-pro', 'sonar-reasoning-pro', 'sonar-deep-research'],
  },
}

const DETECT_ORDER: Provider[] = ['anthropic', 'google', 'perplexity', 'openai']

export function detectProvider(key: string): Provider | null {
  for (const id of DETECT_ORDER) {
    if (key && PROVIDERS[id].detect(key)) return id
  }
  return null
}
