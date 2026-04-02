export type Provider = 'anthropic' | 'openai' | 'google' | 'perplexity'

export interface VerifiedKey {
  key: string
  provider: Provider
  models: string[]
  verifiedAt: string
}

export type KeysFile = VerifiedKey[]

export interface Dork {
  query: string
  type: 'code' | 'repositories' | 'commits'
  description: string
  remediation: string
}
