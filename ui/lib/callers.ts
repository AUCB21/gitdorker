/* eslint-disable @typescript-eslint/no-explicit-any */
// SDKs are loaded dynamically from esm.sh — no static types available; any is intentional here.

export const API_TIMEOUT_MS = 60_000

export function withTimeout<T>(promise: Promise<T>, ms = API_TIMEOUT_MS): Promise<T> {
  let id: ReturnType<typeof setTimeout>
  const timeout = new Promise<never>((_, reject) => {
    id = setTimeout(() => reject(new Error(`API timeout after ${ms / 1000}s`)), ms)
  })
  return Promise.race([promise, timeout]).finally(() => clearTimeout(id))
}

export interface CallResult {
  text: string
  tokens: string
}

export async function callAnthropic(apiKey: string, model: string, prompt: string, maxTokens: number): Promise<CallResult> {
  const { default: Anthropic } = await import('https://esm.sh/@anthropic-ai/sdk@0.40.0' as string) as any
  const client = new Anthropic({ apiKey, dangerouslyAllowBrowser: true })
  const msg = await client.messages.create({
    model,
    max_tokens: maxTokens,
    messages: [{ role: 'user', content: prompt }],
  })
  return {
    text: msg.content[0]?.text ?? '',
    tokens: `${msg.usage?.input_tokens ?? '?'} in · ${msg.usage?.output_tokens ?? '?'} out`,
  }
}

export async function callOpenAI(apiKey: string, model: string, prompt: string, maxTokens: number): Promise<CallResult> {
  const { default: OpenAI } = await import('https://esm.sh/openai@4' as string) as any
  const client = new OpenAI({ apiKey, dangerouslyAllowBrowser: true })
  const resp = await client.chat.completions.create({
    model,
    max_tokens: maxTokens,
    messages: [{ role: 'user', content: prompt }],
  })
  return {
    text: resp.choices[0]?.message?.content ?? '',
    tokens: `${resp.usage?.prompt_tokens ?? '?'} in · ${resp.usage?.completion_tokens ?? '?'} out`,
  }
}

export async function callGoogle(apiKey: string, model: string, prompt: string): Promise<CallResult> {
  const { GoogleGenAI } = await import('https://esm.sh/@google/genai@1' as string) as any
  const genai = new GoogleGenAI({ apiKey })
  const result = await genai.models.generateContent({
    model,
    contents: [{ role: 'user', parts: [{ text: prompt }] }],
  })
  return { text: result.text ?? '', tokens: '' }
}

export async function callPerplexity(apiKey: string, model: string, prompt: string, maxTokens: number): Promise<CallResult> {
  const { default: OpenAI } = await import('https://esm.sh/openai@4' as string) as any
  const client = new OpenAI({
    apiKey,
    baseURL: 'https://api.perplexity.ai',
    dangerouslyAllowBrowser: true,
  })
  const resp = await client.chat.completions.create({
    model,
    max_tokens: maxTokens,
    messages: [{ role: 'user', content: prompt }],
  })
  return {
    text: resp.choices[0]?.message?.content ?? '',
    tokens: `${resp.usage?.prompt_tokens ?? '?'} in · ${resp.usage?.completion_tokens ?? '?'} out`,
  }
}

export const CALLERS: Record<string, (apiKey: string, model: string, prompt: string, maxTokens: number) => Promise<CallResult>> = {
  anthropic: callAnthropic,
  openai: callOpenAI,
  google: callGoogle,
  perplexity: callPerplexity,
}
