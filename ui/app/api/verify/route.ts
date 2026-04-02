export const runtime = 'nodejs'
export const maxDuration = 120

import Anthropic from '@anthropic-ai/sdk'
import OpenAI from 'openai'
import { GoogleGenAI } from '@google/genai'
import type { Provider } from '@/types'

interface VerifyRequest {
  provider: Provider
  apiKey: string
  model: string
  prompt: string
  maxTokens: number
}

export async function POST(req: Request): Promise<Response> {
  const { provider, apiKey, model, prompt, maxTokens } = (await req.json()) as VerifyRequest

  try {
    let result: { text: string; tokens: string }

    if (provider === 'anthropic') {
      const client = new Anthropic({ apiKey })
      const msg = await client.messages.create({
        model,
        max_tokens: maxTokens,
        messages: [{ role: 'user', content: prompt }],
      })
      result = {
        text: msg.content[0]?.type === 'text' ? msg.content[0].text : '',
        tokens: `${msg.usage.input_tokens} in · ${msg.usage.output_tokens} out`,
      }
    } else if (provider === 'openai') {
      const client = new OpenAI({ apiKey })
      const resp = await client.chat.completions.create({
        model,
        max_tokens: maxTokens,
        messages: [{ role: 'user', content: prompt }],
      })
      result = {
        text: resp.choices[0]?.message?.content ?? '',
        tokens: `${resp.usage?.prompt_tokens ?? '?'} in · ${resp.usage?.completion_tokens ?? '?'} out`,
      }
    } else if (provider === 'google') {
      const genai = new GoogleGenAI({ apiKey })
      const r = await genai.models.generateContent({
        model,
        contents: [{ role: 'user', parts: [{ text: prompt }] }],
      })
      result = { text: r.text ?? '', tokens: '' }
    } else if (provider === 'perplexity') {
      const client = new OpenAI({ apiKey, baseURL: 'https://api.perplexity.ai' })
      const resp = await client.chat.completions.create({
        model,
        max_tokens: maxTokens,
        messages: [{ role: 'user', content: prompt }],
      })
      result = {
        text: resp.choices[0]?.message?.content ?? '',
        tokens: `${resp.usage?.prompt_tokens ?? '?'} in · ${resp.usage?.completion_tokens ?? '?'} out`,
      }
    } else {
      return Response.json({ error: 'Unknown provider' }, { status: 400 })
    }

    return Response.json(result)
  } catch (err: unknown) {
    const e = err as Error & { status?: number; code?: string }
    const httpStatus = typeof e.status === 'number' && e.status >= 400 && e.status < 600
      ? e.status
      : 500
    return Response.json(
      { error: e.message ?? 'Unknown error', status: e.status, code: e.code },
      { status: httpStatus },
    )
  }
}
