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
      function send(data: string) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`))
      }

      child.stdout.on('data', (chunk: Buffer) => send(chunk.toString()))
      child.stderr.on('data', (chunk: Buffer) => send(chunk.toString()))

      child.on('close', (code) => {
        send(`\r\n[Process exited with code ${code}]\r\n`)
        controller.close()
      })

      child.on('error', (err) => {
        send(`\r\n[Error: ${err.message}]\r\n`)
        controller.close()
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
