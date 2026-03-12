import { useState, useEffect, useRef } from 'react'
// import streetVideo from './assets/Street_View_Video_Generation.mp4'
import galaxyVideo from './assets/GalaxyVideo.mp4'
import AgentTimeline from './AgentTimeline'
import MarketShiftDashboard from './MarketShiftDashboard'

// ─── State machine ────────────────────────────────────────────────────────────
// 'user-query'    → hero with input
// 'agent-working' → AgentTimeline runs; API call fires in parallel
// 'dashboard'     → both timeline AND API done; show results

// ─── API helper ───────────────────────────────────────────────────────────────

async function postPipeline(url) {
  const res = await fetch('/api/pipeline', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `API error ${res.status}`)
  }
  return res.json()
}

const EMPTY_RESULT = {
  query: '', product_announcements: [], funding: [], partnerships: [],
  market_signals: [], market_opportunities: [], competitive_risks: [],
  action_steps: [], persisted_at: '',
}

export default function LandingPage() {
  const [appState, setAppState] = useState('user-query')
  const [query, setQuery] = useState('')
  const [error, setError] = useState(null)

  // API state
  const [apiResult, setApiResult] = useState(null)   // PipelineResponse | null
  const [apiError, setApiError] = useState(null)   // string | null
  const [timelineDone, setTimelineDone] = useState(false)

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

  // ── Gate: transition to dashboard only when BOTH API + timeline are done ──
  useEffect(() => {
    if (timelineDone && apiResult !== null) {
      setAppState('dashboard')
    }
  }, [timelineDone, apiResult])

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handleAnalyse = () => {
    if (!query.trim()) {
      setError('Enter a company name, URL, or market to get started.')
      return
    }

    // Reset prior run
    setError(null)
    setApiResult(null)
    setApiError(null)
    setTimelineDone(false)
    setAppState('agent-working')

    // Fire API in parallel with the timeline animation
    postPipeline(query.trim())
      .then((data) => {
        setApiResult(data)
        console.log('API result received:', data)
      })
      .catch((err) => {
        setApiError(err.message)
        setApiResult(EMPTY_RESULT) // unblock the gate; dashboard shows error
      })
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleAnalyse()
  }

  return (
    <div>

      {/* ── SECTION 1: Hero ──────────────────────────────────────────── */}
      <div className="relative min-h-screen overflow-hidden">

        <video
          autoPlay loop muted playsInline
          className="absolute w-full h-full object-cover"
        >
          <source src={galaxyVideo} type="video/mp4" />
        </video>

        <div className="absolute inset-0" />

        <section className="relative min-h-screen flex flex-col items-center justify-center px-4 text-center -translate-y-[50px]">
          <div className="flex flex-col items-center gap-6 max-w-4xl w-full">

            <h1 className="font-serif text-6xl sm:text-7xl font-semibold text-white leading-tight tracking-tight whitespace-nowrap">
              Today's MarketShift
            </h1>

            <div className="flex flex-col gap-2">
              <p className="font-mono text-lg sm:text-xl text-white leading-relaxed drop-shadow-[0_2px_8px_rgba(0,0,0,0.6)]">
                Monitor what competitors launch, build, fund, and partner on.
              </p>
              <p className="font-mono text-base sm:text-lg text-white/80  leading-relaxed drop-shadow-[0_2px_8px_rgba(0,0,0,0.5)]">
                One dashboard that reveals market movements and strategic opportunities.
              </p>
            </div>

            <div className="w-full flex flex-col items-center gap-3 mt-2">
              <div className="w-9/12 bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl flex items-center pr-1.5 focus-within:border-white/50 focus-within:bg-white/15 transition-all duration-300">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={appState !== 'user-query'}
                  placeholder="e.g. Notion.so · US · Coda.io, Craft.do"
                  className="flex-1 bg-transparent px-4 py-2.5 text-white placeholder-white/40 focus:outline-none text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <button
                  onClick={handleAnalyse}
                  disabled={appState !== 'user-query'}
                  className="shrink-0 bg-white/90 hover:bg-white active:bg-white/80 disabled:bg-white/40 text-slate-900 text-sm font-semibold px-4 py-1.5 rounded-xl transition-all duration-200 cursor-pointer disabled:cursor-not-allowed"
                >
                  Analyse
                </button>
              </div>

              {error && <p className="text-red-300 text-sm">{error}</p>}
            </div>

          </div>
        </section>
      </div>

      {/* ── SECTION 2: Agent Timeline ─────────────────────────────────── */}
      {appState !== 'user-query' && (
        <div ref={timelineRef}>
          <AgentTimeline onComplete={() => setTimelineDone(true)} apiDone={apiResult !== null} />
        </div>
      )}

      {/* ── SECTION 3: Dashboard ──────────────────────────────────────── */}
      {appState === 'dashboard' && (
        <div ref={dashboardRef}>
          <MarketShiftDashboard apiResult={apiResult} apiError={apiError} />
        </div>
      )}

    </div>
  )
}
