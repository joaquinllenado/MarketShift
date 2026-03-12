import { useState, useEffect, useRef, useCallback } from 'react'
import { Activity, TrendingUp, ShieldAlert, Bell, Zap, Megaphone, DollarSign, Handshake, Loader2, Pause, Volume2 } from 'lucide-react'

// ─── Severity by position ─────────────────────────────────────────────────────
const severityByIdx = (i) => (i < 2 ? 'high' : i < 4 ? 'medium' : 'low')

const SEVERITY = {
  high:   { dot: 'bg-red-400',   ring: 'ring-red-100'   },
  medium: { dot: 'bg-amber-400', ring: 'ring-amber-100' },
  low:    { dot: 'bg-slate-300', ring: 'ring-slate-100' },
}

// ─── GlassCard ────────────────────────────────────────────────────────────────
function GlassCard({ children, className = '' }) {
  return (
    <div className={`bg-white/60 backdrop-blur-xl border border-white/40 shadow-sm rounded-[2.5rem] p-6 ${className}`}>
      {children}
    </div>
  )
}

// ─── CompanyAvatar ────────────────────────────────────────────────────────────
function CompanyAvatar({ logo, abbreviation }) {
  const [err, setErr] = useState(false)
  if (!logo || err) {
    return (
      <div
        className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
        style={{ background: 'rgba(255,158,19,0.12)', border: '1px solid rgba(255,158,19,0.25)', color: '#b36a00' }}
      >
        {abbreviation}
      </div>
    )
  }
  return (
    <img
      src={logo}
      alt={abbreviation}
      className="w-8 h-8 rounded-full object-cover border border-slate-100 shrink-0"
      onError={() => setErr(true)}
    />
  )
}

// ─── ActivityRow ──────────────────────────────────────────────────────────────
function ActivityRow({ item, badge }) {
  return (
    <a
      href={item.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-start gap-3 p-2.5 rounded-2xl hover:bg-white/50 transition-colors group"
    >
      <CompanyAvatar logo={item.logo} abbreviation={item.abbreviation} />
      <div className="flex-1 min-w-0">
        <p className="text-xs font-semibold text-slate-700">{item.company}</p>
        <p className="text-sm text-slate-600 leading-snug">{item.title}</p>
      </div>
      {badge && (
        <span
          className="font-mono text-xs font-bold px-2 py-0.5 rounded-full shrink-0"
          style={{ color: '#b36a00', background: 'rgba(255,158,19,0.1)', border: '1px solid rgba(255,158,19,0.25)' }}
        >
          {badge}
        </span>
      )}
      <span className="text-xs text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity shrink-0 mt-0.5">↗</span>
    </a>
  )
}

// ─── ActivitySection ──────────────────────────────────────────────────────────
function ActivitySection({ items, badge }) {
  if (!items?.length) return null
  return (
    <ul className="flex flex-col">
      {items.map((item, i) => (
        <li key={i}>
          <ActivityRow item={item} badge={badge ? (item.amount || null) : null} />
        </li>
      ))}
    </ul>
  )
}

// ─── Checkmark ────────────────────────────────────────────────────────────────
function Checkmark() {
  return (
    <svg viewBox="0 0 10 10" className="w-2.5 h-2.5" aria-hidden>
      <polyline points="1.5,5.5 4,8 8.5,2" fill="none" stroke="white"
        strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

// ─── Empty state ──────────────────────────────────────────────────────────────
function Empty({ label }) {
  return <p className="text-xs text-slate-400 italic px-1">{label}</p>
}

// ─── Main dashboard ───────────────────────────────────────────────────────────
export default function MarketShiftDashboard({ apiResult = null, apiError = null }) {

  // Voice summary state
  const [voiceState, setVoiceState] = useState('idle') // idle | loading | playing | paused | error
  const [voiceError, setVoiceError] = useState(null)
  const audioRef = useRef(null)
  const blobUrlRef = useRef(null)

  const handleVoiceSummary = useCallback(async () => {
    if (voiceState === 'playing') {
      audioRef.current?.pause()
      setVoiceState('paused')
      return
    }
    if (voiceState === 'paused') {
      audioRef.current?.play()
      setVoiceState('playing')
      return
    }

    setVoiceState('loading')
    setVoiceError(null)

    try {
      const res = await fetch('/api/pipeline/voice-summary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(apiResult),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `API error ${res.status}`)
      }

      const blob = await res.blob()
      if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current)
      const url = URL.createObjectURL(blob)
      blobUrlRef.current = url

      const audio = new Audio(url)
      audioRef.current = audio
      audio.addEventListener('ended', () => setVoiceState('idle'))
      await audio.play()
      setVoiceState('playing')
    } catch (err) {
      setVoiceError(err.message)
      setVoiceState('error')
    }
  }, [voiceState])

  useEffect(() => {
    return () => {
      audioRef.current?.pause()
      if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current)
    }
  }, [])

  // Action steps with local done-state
  const [actions, setActions] = useState([])

  useEffect(() => {
    if (apiResult?.action_steps?.length) {
      setActions(apiResult.action_steps.map((a) => ({ ...a, done: false })))
    }
  }, [apiResult])

  const toggle = (step) =>
    setActions((prev) => prev.map((a) => (a.step === step ? { ...a, done: !a.done } : a)))

  // Derived data
  const signals       = apiResult?.market_signals        ?? []
  const opportunities = apiResult?.market_opportunities  ?? []
  const risks         = apiResult?.competitive_risks      ?? []
  const announcements = apiResult?.product_announcements ?? []
  const funding       = apiResult?.funding                ?? []
  const partnerships  = apiResult?.partnerships           ?? []
  const query         = apiResult?.query                  ?? ''
  const updatedAt     = apiResult?.persisted_at
    ? new Date(apiResult.persisted_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : null

  const doneCount = actions.filter((a) => a.done).length

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-amber-50 p-4 sm:p-6 lg:p-8 relative overflow-hidden">

      {/* Decorative blobs */}
      <div className="pointer-events-none absolute -top-40 -left-40 w-[28rem] h-[28rem] rounded-full blur-3xl" style={{background:'rgba(255,158,19,0.12)'}} />
      <div className="pointer-events-none absolute -bottom-40 -right-40 w-[28rem] h-[28rem] rounded-full bg-indigo-200/25 blur-3xl" />
      <div className="pointer-events-none absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 rounded-full bg-sky-100/20 blur-3xl" />

      <div className="relative max-w-7xl mx-auto grid grid-cols-12 gap-4">

        {/* ── ROW 1: HEADER ──────────────────────────────────────────────── */}
        <GlassCard className="col-span-12 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2.5">
              <Activity className="w-5 h-5" style={{color:'#FF9E13'}} />
              <h1 className="font-serif text-xl font-bold text-slate-800 tracking-tight">Market Shift</h1>
              <span className="font-mono text-xs text-slate-400 font-medium">Competitor Intelligence</span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span
                className="inline-flex items-center gap-1.5 self-start text-xs font-medium rounded-full px-3 py-1"
                style={{ color: '#b36a00', background: 'rgba(255,158,19,0.1)', border: '1px solid rgba(255,158,19,0.3)' }}
              >
                <span className="w-1.5 h-1.5 rounded-full" style={{background:'#FF9E13'}} />
                <span className="font-mono">
                  {query ? `Analysed: ${query.slice(0, 60)}${query.length > 60 ? '…' : ''}` : 'Competitor Intelligence'}
                </span>
              </span>
              {updatedAt && (
                <span className="font-mono text-xs text-slate-400">Updated {updatedAt}</span>
              )}
              {apiError && (
                <span className="text-xs text-red-500 bg-red-50 border border-red-100 rounded-full px-3 py-1">
                  ⚠ {apiError}
                </span>
              )}
            </div>
          </div>
          <div className="flex flex-col items-end gap-1">
            <button
              onClick={handleVoiceSummary}
              disabled={voiceState === 'loading'}
              className="self-start sm:self-auto inline-flex items-center gap-2 text-white text-sm font-semibold px-5 py-2.5 rounded-2xl transition-colors cursor-pointer disabled:opacity-60 disabled:cursor-wait"
              style={{ background: '#FF9E13', boxShadow: '0 2px 8px rgba(255,158,19,0.3)' }}
              onMouseEnter={e => { if (voiceState !== 'loading') e.currentTarget.style.background='#ffb340' }}
              onMouseLeave={e => e.currentTarget.style.background='#FF9E13'}
            >
              {voiceState === 'loading' && <Loader2 className="w-4 h-4 animate-spin" />}
              {voiceState === 'playing' && <Pause className="w-4 h-4" />}
              {voiceState === 'paused' && <Volume2 className="w-4 h-4" />}
              {(voiceState === 'idle' || voiceState === 'error') && <Zap className="w-4 h-4" />}
              {voiceState === 'loading' ? 'Generating…' :
               voiceState === 'playing' ? 'Pause' :
               voiceState === 'paused' ? 'Resume' :
               'Listen to Report'}
            </button>
            {voiceState === 'error' && voiceError && (
              <span className="text-xs text-red-500 bg-red-50 border border-red-100 rounded-full px-3 py-0.5">
                {voiceError}
              </span>
            )}
          </div>
        </GlassCard>

        {/* ── ROW 2: PRODUCT ANNOUNCEMENTS + FUNDING ─────────────────────── */}

        {/* Product Announcements */}
        <GlassCard className="col-span-12 md:col-span-6 flex flex-col gap-4 overflow-y-auto">
          <div className="flex items-center gap-2">
            <Megaphone className="w-4 h-4 text-indigo-500" />
            <h2 className="font-serif text-sm font-semibold text-slate-800">Product Announcements</h2>
            <span className="font-mono text-xs text-slate-400 ml-auto">{announcements.length} items</span>
          </div>
          {announcements.length === 0
            ? <Empty label="No announcements returned." />
            : <ActivitySection items={announcements} badge={false} />
          }
        </GlassCard>

        {/* Funding */}
        <GlassCard className="col-span-12 md:col-span-6 flex flex-col gap-4 overflow-y-auto">
          <div className="flex items-center gap-2">
            <DollarSign className="w-4 h-4" style={{color:'#FF9E13'}} />
            <h2 className="font-serif text-sm font-semibold text-slate-800">Funding</h2>
            <span className="font-mono text-xs text-slate-400 ml-auto">{funding.length} rounds</span>
          </div>
          {funding.length === 0
            ? <Empty label="No funding activity returned." />
            : <ActivitySection items={funding} badge={true} />
          }
        </GlassCard>

        {/* ── ROW 3: PARTNERSHIPS + MARKET SIGNALS ───────────────────────── */}

        {/* Partnerships */}
        <GlassCard className="col-span-12 md:col-span-6 flex flex-col gap-4 overflow-y-auto">
          <div className="flex items-center gap-2">
            <Handshake className="w-4 h-4 text-violet-500" />
            <h2 className="font-serif text-sm font-semibold text-slate-800">Partnerships</h2>
            <span className="font-mono text-xs text-slate-400 ml-auto">{partnerships.length} items</span>
          </div>
          {partnerships.length === 0
            ? <Empty label="No partnerships returned." />
            : <ActivitySection items={partnerships} badge={false} />
          }
        </GlassCard>

        {/* Market Signals */}
        <GlassCard className="col-span-12 md:col-span-6 flex flex-col gap-4 overflow-y-auto">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4 text-indigo-500" />
              <h2 className="font-serif text-sm font-semibold text-slate-800">Market Signals</h2>
            </div>
            <span className="font-mono text-xs text-slate-400">{signals.length} signals</span>
          </div>

          {signals.length === 0
            ? <Empty label="No market signals returned." />
            : (
              <ul className="flex flex-col gap-4">
                {signals.map((s, i) => {
                  const sev = SEVERITY[severityByIdx(i)]
                  return (
                    <li key={i} className="flex items-start gap-3">
                      <span className={`mt-1 w-2 h-2 rounded-full shrink-0 ${sev.dot} ring-4 ${sev.ring}`} />
                      <div className="flex items-start gap-2.5 min-w-0">
                        <CompanyAvatar logo={s.logo} abbreviation={s.abbreviation} />
                        <div className="flex flex-col gap-0.5 min-w-0">
                          <p className="text-xs font-semibold text-slate-700">{s.company}</p>
                          <p className="text-sm text-slate-600 leading-snug">{s.title}</p>
                          {s.description && (
                            <p className="text-xs text-slate-400 leading-snug">{s.description}</p>
                          )}
                        </div>
                      </div>
                    </li>
                  )
                })}
              </ul>
            )
          }
        </GlassCard>

        {/* ── ROW 4: OPPORTUNITIES + RISKS (full width) ──────────────────── */}
        <GlassCard className="col-span-12 flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4" style={{color:'#FF9E13'}} />
            <h2 className="font-serif text-sm font-semibold text-slate-800">Market Intelligence</h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">

            {/* Opportunities */}
            <div className="flex flex-col gap-2">
              <p className="font-mono text-xs font-semibold uppercase tracking-wide" style={{color:'#FF9E13'}}>
                Opportunities
              </p>
              {opportunities.length === 0
                ? <Empty label="No opportunities identified." />
                : (
                  <ul className="flex flex-col gap-2.5">
                    {opportunities.map((opp, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-slate-700 leading-snug">
                        <span className="mt-0.5 font-bold shrink-0" style={{color:'#FF9E13'}}>✓</span>
                        {opp}
                      </li>
                    ))}
                  </ul>
                )
              }
            </div>

            {/* Risks */}
            <div className="flex flex-col gap-2">
              <p className="font-mono text-xs font-semibold text-amber-600 uppercase tracking-wide">
                Competitive Risks
              </p>
              {risks.length === 0
                ? <Empty label="No risks identified." />
                : (
                  <ul className="flex flex-col gap-2.5">
                    {risks.map((risk, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-slate-700 leading-snug">
                        <span className="mt-0.5 text-amber-500 font-bold shrink-0">⚠</span>
                        {risk}
                      </li>
                    ))}
                  </ul>
                )
              }
            </div>

          </div>
        </GlassCard>

        {/* ── ROW 5: ACTION STEPS (full width) ───────────────────────────── */}
        <GlassCard className="col-span-12 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4" style={{color:'#FF9E13'}} />
              <h2 className="font-serif text-sm font-semibold text-slate-800">Action Steps</h2>
            </div>
            {actions.length > 0 && (
              <span className="font-mono text-xs text-slate-400">
                {doneCount}/{actions.length} done
              </span>
            )}
          </div>

          {actions.length === 0
            ? <Empty label="No action steps returned." />
            : (
              <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                {actions.map((action) => (
                  <li
                    key={action.step}
                    onClick={() => toggle(action.step)}
                    className={`flex items-start gap-3 p-3 rounded-2xl cursor-pointer transition-colors select-none ${
                      action.done ? 'bg-slate-50/60' : 'bg-white/40 hover:bg-white/70'
                    }`}
                  >
                    {/* Checkbox */}
                    <div
                      className="mt-0.5 w-4 h-4 rounded-full border-2 shrink-0 flex items-center justify-center transition-colors"
                      style={action.done
                        ? { background: '#FF9E13', borderColor: '#FF9E13' }
                        : { background: 'rgba(255,255,255,0.6)', borderColor: '#d1d5db' }
                      }
                    >
                      {action.done && <Checkmark />}
                    </div>

                    {/* Step number + title */}
                    <div className="flex items-start gap-2 min-w-0 flex-1">
                      <span
                        className="font-mono text-xs font-bold tabular-nums shrink-0 mt-0.5"
                        style={{ color: action.done ? '#d1d5db' : '#FF9E13' }}
                      >
                        {action.step}.
                      </span>
                      <span className={`text-sm leading-snug ${action.done ? 'line-through text-slate-400' : 'text-slate-700'}`}>
                        {action.title}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )
          }
        </GlassCard>

      </div>
    </div>
  )
}
