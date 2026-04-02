import { execSync } from 'child_process'
import path from 'path'
import fs from 'fs'

export function findPython(): string {
  // 1. Explicit env var
  if (process.env.PYTHON_BIN) return process.env.PYTHON_BIN

  // 2. Local venv relative to this file's location (ui/lib → ui → repo root → env/)
  const repoRoot = path.resolve(__dirname, '..', '..', '..')
  const venvWin = path.join(repoRoot, 'env', 'Scripts', 'python.exe')
  const venvUnix = path.join(repoRoot, 'env', 'bin', 'python')

  if (fs.existsSync(venvWin)) return venvWin
  if (fs.existsSync(venvUnix)) return venvUnix

  // 3. System python3
  try {
    const which = execSync('which python3', { encoding: 'utf8' }).trim()
    if (which) return which
  } catch {}

  // 4. Fallback: let the OS resolve it
  return 'python3'
}
