import type { VerifiedKey } from '@/types'

const KEY = 'gd_keys'

export function getKeys(): VerifiedKey[] {
  if (typeof window === 'undefined') return []
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? '[]') as VerifiedKey[]
  } catch {
    return []
  }
}

export function saveKeys(keys: VerifiedKey[]): void {
  localStorage.setItem(KEY, JSON.stringify(keys))
}

export function mergeKey(incoming: VerifiedKey): void {
  const keys = getKeys()
  const idx = keys.findIndex((k) => k.key === incoming.key)
  if (idx >= 0) {
    incoming.models.forEach((m) => {
      if (!keys[idx].models.includes(m)) keys[idx].models.push(m)
    })
    keys[idx].verifiedAt = incoming.verifiedAt
  } else {
    keys.push(incoming)
  }
  saveKeys(keys)
}

export function deleteKey(key: string): void {
  saveKeys(getKeys().filter((k) => k.key !== key))
}
