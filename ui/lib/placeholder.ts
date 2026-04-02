export function shouldSkip(err: unknown): boolean {
  const e = err as Record<string, unknown>
  const status = (e.status ?? e.code ?? 0) as number
  if (status === 404 || status === 429) return true
  const msg = String(e.message ?? '')
  return /"code":\s*(404|429)/.test(msg) || /NOT_FOUND|RESOURCE_EXHAUSTED/.test(msg)
}
