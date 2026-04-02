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

  // 3. System lookup — avoid Windows Store stubs (WindowsApps) which are fake launchers
  const isStub = (p: string) => p.toLowerCase().includes('windowsapps')

  if (process.platform === 'win32') {
    for (const cmd of ['where python', 'where py', 'where python3']) {
      try {
        const result = execSync(cmd, { encoding: 'utf8' }).trim().split('\n')[0].trim()
        if (result && !isStub(result)) return result
      } catch {}
    }
  } else {
    try {
      const result = execSync('which python3 || which python', { encoding: 'utf8' }).trim()
      if (result && !isStub(result)) return result
    } catch {}
  }

  // 4. Fallback: py launcher (Windows), then python3, then python
  return process.platform === 'win32' ? 'py' : 'python3'
}
