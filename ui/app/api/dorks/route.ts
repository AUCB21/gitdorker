export const runtime = 'nodejs'

import { loadDorks } from '@/lib/dorks'
import { NextResponse } from 'next/server'

export function GET() {
  try {
    const dorks = loadDorks()
    return NextResponse.json(dorks)
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
