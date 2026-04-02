'use client'

import { useEffect, useRef, useState } from 'react'
import { TerminalControls } from './TerminalControls'

export function TerminalTab() {
  const containerRef = useRef<HTMLDivElement>(null)
  const termRef = useRef<{ write: (s: string) => void; clear: () => void } | null>(null)
  const readerRef = useRef<ReadableStreamDefaultReader | null>(null)
  const [running, setRunning] = useState(false)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (!mounted || !containerRef.current) return

    async function init() {
      const { Terminal } = await import('xterm')
      const { FitAddon } = await import('xterm-addon-fit')
      const { WebLinksAddon } = await import('xterm-addon-web-links')

      const term = new Terminal({
        theme: {
          background: '#0a0a0a',
          foreground: '#ededed',
          cursor: '#fbbf24',
          selectionBackground: '#fbbf2440',
        },
        fontFamily: 'JetBrains Mono, Menlo, monospace',
        fontSize: 13,
        cursorBlink: true,
      })

      const fitAddon = new FitAddon()
      term.loadAddon(fitAddon)
      term.loadAddon(new WebLinksAddon())
      term.open(containerRef.current!)
      fitAddon.fit()
      termRef.current = term

      const observer = new ResizeObserver(() => fitAddon.fit())
      observer.observe(containerRef.current!)

      return () => observer.disconnect()
    }

    const cleanup = init()
    return () => { cleanup.then((fn) => fn?.()) }
  }, [mounted])

  async function run(args: string[]) {
    if (!termRef.current) return
    termRef.current.clear()
    setRunning(true)

    const resp = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ args }),
    })

    if (!resp.body) { setRunning(false); return }

    const reader = resp.body.getReader()
    readerRef.current = reader
    const decoder = new TextDecoder()

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const text = decoder.decode(value)
        // Parse SSE data lines
        for (const line of text.split('\n')) {
          if (line.startsWith('data: ')) {
            try {
              const chunk = JSON.parse(line.slice(6))
              termRef.current?.write(chunk.replace(/\n/g, '\r\n'))
            } catch {}
          }
        }
      }
    } catch {}

    setRunning(false)
    readerRef.current = null
  }

  function stop() {
    readerRef.current?.cancel()
    setRunning(false)
  }

  if (!mounted) return null

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <aside className="lg:col-span-4">
        <TerminalControls running={running} onRun={run} onStop={stop} />
      </aside>
      <main className="lg:col-span-8">
        <div className="bg-[#0a0a0a] border border-neutral-800 rounded-xl overflow-hidden" style={{ height: '600px' }}>
          <div className="bg-neutral-900 border-b border-neutral-800 px-4 py-2 flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500/60" />
            <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
            <div className="w-3 h-3 rounded-full bg-green-500/60" />
            <span className="text-[10px] text-neutral-500 font-mono ml-2">gitdorker terminal</span>
          </div>
          <div ref={containerRef} className="h-[calc(100%-36px)] p-2" />
        </div>
      </main>
    </div>
  )
}
