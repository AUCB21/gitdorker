export const runtime = 'nodejs'

import { spawn } from 'child_process'
import { findPython } from '@/lib/find-python'

export async function POST(req: Request): Promise<Response> {
  const { args } = (await req.json()) as { args: string[] }

  const python = findPython()
  const child = spawn(python, ['-m', 'gitdorker.cli', ...args], {
    cwd: process.cwd().replace(/[\\/]ui$/, ''),
    env: { ...process.env },
  })

  const encoder = new TextEncoder()

  const stream = new ReadableStream({
    start(controller) {
      let closed = false
      function send(data: string) {
        if (closed) return
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`))
      }
      function close() {
        if (closed) return
        closed = true
        controller.close()
      }

      child.stdout.on('data', (chunk: Buffer) => send(chunk.toString()))
      child.stderr.on('data', (chunk: Buffer) => send(chunk.toString()))

      child.on('close', (code) => {
        send(`\r\n[Process exited with code ${code}]\r\n`)
        close()
      })

      child.on('error', (err) => {
        send(`\r\n[Error: ${err.message}]\r\n`)
        close()
      })
    },
    cancel() {
      child.kill('SIGINT')
    },
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    },
  })
}
