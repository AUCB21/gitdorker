'use client'

import dynamic from 'next/dynamic'
import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { VerifierTab } from '@/components/verifier/VerifierTab'
import { KeysTab } from '@/components/keys/KeysTab'

// xterm.js requires browser APIs — no SSR
const TerminalTab = dynamic(() => import('@/components/terminal/TerminalTab').then((m) => m.TerminalTab), { ssr: false })

export default function Home() {
  const [tab, setTab] = useState('verifier')
  const [keysRefresh, setKeysRefresh] = useState(0)
  const [savedBanner, setSavedBanner] = useState(0)

  function handleKeySaved() {
    setKeysRefresh((n) => n + 1)
    setSavedBanner((n) => n + 1)
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#ededed] p-4 md:p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <header className="border-b border-neutral-800 pb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">
              gitdorker
              <span className="text-amber-500 text-sm ml-2 bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20 font-medium">
                UI
              </span>
            </h1>
            <p className="text-neutral-500 text-sm mt-1">Key verifier · gitdorker terminal · key vault</p>
          </div>
        </header>

        <Tabs value={tab} onValueChange={setTab} className="space-y-6">
          <TabsList className="bg-neutral-900 border border-neutral-800">
            <TabsTrigger value="verifier" className="data-[state=active]:bg-neutral-800">
              Verifier
            </TabsTrigger>
            <TabsTrigger value="terminal" className="data-[state=active]:bg-neutral-800">
              Terminal
            </TabsTrigger>
            <TabsTrigger value="keys" className="data-[state=active]:bg-neutral-800">
              Keys
              {keysRefresh > 0 && (
                <span className="ml-1.5 text-[9px] bg-amber-500 text-black rounded-full px-1.5 py-0.5 font-bold">
                  vault
                </span>
              )}
            </TabsTrigger>
          </TabsList>

          {/* Verifier → Keys saved banner */}
          {savedBanner > 0 && tab === 'verifier' && (
            <div className="flex items-center gap-3 bg-emerald-950/40 border border-emerald-900/50 rounded-lg px-4 py-2.5 text-sm text-emerald-400">
              <span>✓ Keys saved to vault.</span>
              <button
                onClick={() => setTab('keys')}
                className="underline underline-offset-2 font-bold hover:text-emerald-300 transition-colors"
              >
                View Keys tab →
              </button>
            </div>
          )}

          <TabsContent value="verifier" className="mt-0">
            <VerifierTab onKeySaved={handleKeySaved} />
          </TabsContent>

          <TabsContent value="terminal" className="mt-0">
            <TerminalTab />
          </TabsContent>

          <TabsContent value="keys" className="mt-0">
            <KeysTab refreshSignal={keysRefresh} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
