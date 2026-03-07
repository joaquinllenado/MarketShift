import { useState, useEffect, useRef } from 'react'
import streetVideo from './assets/Street_View_Video_Generation.mp4'
import AgentTimeline from './AgentTimeline'
import MarketShiftDashboard from './MarketShiftDashboard'

// ─── State machine ────────────────────────────────────────────────────────────
// 'user-query'   → hero section with input
// 'agent-working' → AgentTimeline section (auto-scrolled to)
// 'dashboard'    → MarketShiftDashboard section (auto-scrolled to)

export default function LandingPage() {
  const [appState, setAppState] = useState('user-query')
  const [query, setQuery] = useState('')
  const [error, setError] = useState(null)

  const timelineRef = useRef(null)
  const dashboardRef = useRef(null)

  // ── Scroll when state changes ─────────────────────────────────────────────
  useEffect(() => {
    if (appState === 'agent-working') {
      setTimeout(
        () => timelineRef.current?.scrollIntoView({ behavior: 'smooth' }),
        50
      )
    }
    if (appState === 'dashboard') {
      setTimeout(
        () => dashboardRef.current?.scrollIntoView({ behavior: 'smooth' }),
        50
      )
    }
  }, [appState])

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handleAnalyse = () => {
    if (!query.trim()) {
      setError('Enter a company name, URL, or market to get started.')
      return
    }
    setError(null)
    setAppState('agent-working')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleAnalyse()
  }

  return (
    <div className="bg-black">

      {/* ── SECTION 1: Hero ──────────────────────────────────────────── */}
      <div className="relative min-h-screen overflow-hidden">

        <video
          autoPlay loop muted playsInline
          className="absolute inset-0 w-full h-full object-cover"
        >
          <source src={streetVideo} type="video/mp4" />
        </video>

        <div className="absolute inset-0 bg-black/55 backdrop-blur-[2px]" />

        <section className="relative min-h-screen flex flex-col items-center justify-center px-4 text-center">
          <div className="flex flex-col items-center gap-6 max-w-2xl w-full">

            <h1 className="text-6xl sm:text-7xl font-bold text-white leading-tight tracking-tight">
              Today's MarketShift
            </h1>

            <div className="flex flex-col gap-2">
              <p className="text-lg sm:text-xl text-white/80 font-light leading-relaxed">
                Monitor what competitors launch, build, fund, and partner on.
              </p>
              <p className="text-base sm:text-lg text-white/60 font-light leading-relaxed">
                One dashboard that reveals market movements and strategic opportunities.
              </p>
            </div>

            <div className="w-full flex flex-col items-center gap-3 mt-2">
              <div className="w-full bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl overflow-hidden focus-within:border-white/50 focus-within:bg-white/15 transition-all duration-300">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={appState !== 'user-query'}
                  placeholder="e.g. Notion.so · US · Coda.io, Craft.do"
                  className="w-full bg-transparent px-5 py-4 text-white placeholder-white/40 focus:outline-none text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                />
              </div>

              {error && <p className="text-red-300 text-sm">{error}</p>}

              <button
                onClick={handleAnalyse}
                disabled={appState !== 'user-query'}
                className="inline-flex items-center gap-2 bg-white/90 hover:bg-white active:bg-white/80 disabled:bg-white/40 text-slate-900 text-sm font-semibold px-8 py-3.5 rounded-2xl transition-all duration-200 cursor-pointer disabled:cursor-not-allowed shadow-lg"
              >
                Analyse your competitors right now
              </button>
            </div>

          </div>
        </section>
      </div>

      {/* ── SECTION 2: Agent Timeline ─────────────────────────────────── */}
      {appState !== 'user-query' && (
        <div ref={timelineRef}>
          <AgentTimeline onComplete={() => setAppState('dashboard')} />
        </div>
      )}

      {/* ── SECTION 3: Dashboard ──────────────────────────────────────── */}
      {appState === 'dashboard' && (
        <div ref={dashboardRef}>
          <MarketShiftDashboard />
        </div>
      )}

    </div>
  )
}
