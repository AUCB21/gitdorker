import fs from 'fs'
import path from 'path'
import type { Dork } from '@/types'

export function loadDorks(): Dork[] {
  const dorksPath = path.resolve(process.cwd(), '..', 'dorks.json')
  const raw = fs.readFileSync(dorksPath, 'utf8')
  return JSON.parse(raw) as Dork[]
}
