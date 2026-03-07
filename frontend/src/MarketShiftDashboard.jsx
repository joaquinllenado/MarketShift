import { useState } from 'react'
import { Activity, TrendingUp, ShieldAlert, Users, Bell, Zap } from 'lucide-react'

// ─── Static mock data ────────────────────────────────────────────────────────

const SIGNALS = [
  {
    id: 1,
    severity: 'high',
    text: 'Competitor A updated pricing — new Growth tier at $149/mo.',
    time: '2m ago',
  },
  {
    id: 2,
    severity: 'medium',
    text: 'Competitor B launched a redesigned landing page with new social proof.',
    time: '18m ago',
  },
  {
    id: 3,
    severity: 'medium',
    text: 'Competitor C posted 3 new AI Lead roles — signals product expansion.',
    time: '1h ago',
  },
  {
    id: 4,
    severity: 'high',
    text: 'Competitor A published a comparison article targeting your brand keywords.',
    time: '3h ago',
  },
  {
    id: 5,
    severity: 'low',
    text: 'Competitor D removed their free tier — possible monetization pivot.',
    time: '5h ago',
  },
]

const SENTIMENT = [
  42, 45, 43, 48, 52, 50, 55, 53, 58, 60,
  57, 62, 65, 63, 68, 70, 67, 72, 75, 73,
  78, 76, 80, 82, 79, 84, 86, 83, 88, 90,
]

const COMPETITORS = [
  { name: 'RivalStack',   featureParity: 78, pricingAdvantage: 55, seoHealth: 82 },
  { name: 'LaunchBase',   featureParity: 62, pricingAdvantage: 71, seoHealth: 58 },
  { name: 'CoreMetrics',  featureParity: 45, pricingAdvantage: 88, seoHealth: 70 },
]

const ACTIONS = [
  { id: 1, text: "Review new pricing tier vs. Competitor A's Growth plan", priority: 'high',   done: false },
  { id: 2, text: 'Brief sales team on Feature X gap vs. RivalStack',        priority: 'high',   done: false },
  { id: 3, text: 'Update SEO keywords to counter new comparison article',   priority: 'medium', done: false },
  { id: 4, text: 'Audit landing page social proof and trust signals',       priority: 'medium', done: true  },
  { id: 5, text: 'Track CoreMetrics free-tier removal impact on signups',   priority: 'low',    done: false },
]

// ─── Severity config ─────────────────────────────────────────────────────────

const SEVERITY = {
  high:   { dot: 'bg-red-400',    ring: 'ring-red-100'    },
  medium: { dot: 'bg-amber-400',  ring: 'ring-amber-100'  },
  low:    { dot: 'bg-slate-300',  ring: 'ring-slate-100'  },
}

const PRIORITY_BADGE = {
  high:   'bg-red-50   text-red-600   border border-red-100',
  medium: 'bg-amber-50 text-amber-600 border border-amber-100',
  low:    'bg-slate-50 text-slate-500 border border-slate-200',
}

// ─── Glass card wrapper ───────────────────────────────────────────────────────

function GlassCard({ children, className = '' }) {
  return (
    <div
      className={`bg-white/60 backdrop-blur-xl border border-white/40 shadow-sm rounded-[2.5rem] p-6 ${className}`}
    >
      {children}
    </div>
  )
}

// ─── SVG sentiment chart (no external deps) ───────────────────────────────────

function SentimentChart({ data }) {
  const W = 440, H = 150
  const pad = { top: 14, right: 16, bottom: 30, left: 38 }
  const cw = W - pad.left - pad.right
  const ch = H - pad.top - pad.bottom
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min

  const pts = data.map((v, i) => ({
    x: pad.left + (i / (data.length - 1)) * cw,
    y: pad.top + ch - ((v - min) / range) * ch,
  }))

  const linePath = pts
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)},${p.y.toFixed(1)}`)
    .join(' ')

  const areaPath =
    `${linePath} L ${pts.at(-1).x.toFixed(1)},${(pad.top + ch).toFixed(1)}` +
    ` L ${pts[0].x.toFixed(1)},${(pad.top + ch).toFixed(1)} Z`

  const yTicks = [min, Math.round(min + range / 2), max]
  const xLabels = [
    { label: 'Day 1',  idx: 0  },
    { label: 'Day 15', idx: 14 },
    { label: 'Day 30', idx: 29 },
  ]

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-full" aria-label="Sentiment trend over 30 days">
      <defs>
        <linearGradient id="sgGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#0d9488" stopOpacity="0.22" />
          <stop offset="100%" stopColor="#0d9488" stopOpacity="0"    />
        </linearGradient>
      </defs>

      {/* Dashed grid lines */}
      {yTicks.map((tick, i) => {
        const y = (pad.top + ch - ((tick - min) / range) * ch).toFixed(1)
        return (
          <line
            key={i}
            x1={pad.left} y1={y}
            x2={(pad.left + cw).toFixed(1)} y2={y}
            stroke="#e2e8f0" strokeWidth="1" strokeDasharray="4,5"
          />
        )
      })}

      {/* Area fill */}
      <path d={areaPath} fill="url(#sgGrad)" />

      {/* Line */}
      <path
        d={linePath}
        fill="none"
        stroke="#0d9488"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* End-point pulse rings */}
      <circle cx={pts.at(-1).x.toFixed(1)} cy={pts.at(-1).y.toFixed(1)} r="10" fill="#0d9488" fillOpacity="0.10" />
      <circle cx={pts.at(-1).x.toFixed(1)} cy={pts.at(-1).y.toFixed(1)} r="4"  fill="#0d9488" />

      {/* Y-axis labels */}
      {yTicks.map((tick, i) => {
        const y = (pad.top + ch - ((tick - min) / range) * ch + 4).toFixed(1)
        return (
          <text key={i} x={pad.left - 6} y={y} textAnchor="end" fontSize="9" fill="#94a3b8">
            {tick}%
          </text>
        )
      })}

      {/* X-axis labels */}
      {xLabels.map(({ label, idx }) => (
        <text
          key={label}
          x={pts[idx].x.toFixed(1)}
          y={H - 8}
          textAnchor="middle"
          fontSize="9"
          fill="#94a3b8"
        >
          {label}
        </text>
      ))}
    </svg>
  )
}

// ─── Metric progress bar ──────────────────────────────────────────────────────

function MetricBar({ label, value, color }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-slate-500 w-36 shrink-0">{label}</span>
      <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${value}%` }} />
      </div>
      <span className="text-xs font-semibold text-slate-700 w-8 text-right tabular-nums">{value}%</span>
    </div>
  )
}

// ─── Checkmark SVG (inline, no dep) ──────────────────────────────────────────

function Checkmark() {
  return (
    <svg viewBox="0 0 10 10" className="w-2.5 h-2.5" aria-hidden>
      <polyline
        points="1.5,5.5 4,8 8.5,2"
        fill="none"
        stroke="white"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

// ─── Main dashboard ───────────────────────────────────────────────────────────

export default function MarketShiftDashboard() {
  const [actions, setActions] = useState(ACTIONS)

  const toggleAction = (id) =>
    setActions((prev) =>
      prev.map((a) => (a.id === id ? { ...a, done: !a.done } : a))
    )

  const currentSentiment = SENTIMENT.at(-1)
  const sentimentDelta = SENTIMENT.at(-1) - SENTIMENT[0]
  const doneCount = actions.filter((a) => a.done).length

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-teal-50 p-4 sm:p-6 lg:p-8 relative overflow-hidden">

      {/* Decorative depth blobs */}
      <div className="pointer-events-none absolute -top-40 -left-40 w-[28rem] h-[28rem] rounded-full bg-teal-200/25 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-40 -right-40 w-[28rem] h-[28rem] rounded-full bg-indigo-200/25 blur-3xl" />
      <div className="pointer-events-none absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 rounded-full bg-sky-100/20 blur-3xl" />

      <div className="relative max-w-7xl mx-auto grid grid-cols-12 gap-4">

        {/* ── HEADER ─────────────────────────────────────────────────────── */}
        <GlassCard className="col-span-12 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2.5">
              <Activity className="w-5 h-5 text-teal-600" />
              <h1 className="text-xl font-bold text-slate-800 tracking-tight">Market Shift</h1>
              <span className="text-xs text-slate-400 font-medium">Competitor Intelligence</span>
            </div>
            <span className="inline-flex items-center gap-1.5 self-start text-xs font-medium text-teal-700 bg-teal-50 border border-teal-200 rounded-full px-3 py-1">
              <span className="w-1.5 h-1.5 rounded-full bg-teal-500 animate-pulse" />
              Current Focus: Analyzing Q1 Pricing Shifts
            </span>
          </div>

          <button className="self-start sm:self-auto inline-flex items-center gap-2 bg-teal-600 hover:bg-teal-500 active:bg-teal-700 text-white text-sm font-semibold px-5 py-2.5 rounded-2xl transition-colors shadow-sm shadow-teal-100 cursor-pointer">
            <Zap className="w-4 h-4" />
            Generate Intelligence Report
          </button>
        </GlassCard>

        {/* ── SIGNAL FEED ────────────────────────────────────────────────── */}
        <GlassCard className="col-span-12 md:col-span-5 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4 text-indigo-500" />
              <h2 className="text-sm font-semibold text-slate-800">Live Signal Feed</h2>
            </div>
            <span className="text-xs text-slate-400">{SIGNALS.length} alerts</span>
          </div>

          <ul className="flex flex-col gap-3.5">
            {SIGNALS.map((signal) => {
              const s = SEVERITY[signal.severity]
              return (
                <li key={signal.id} className="flex items-start gap-3">
                  <span
                    className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${s.dot} ring-4 ${s.ring}`}
                  />
                  <div className="flex flex-col gap-0.5 min-w-0">
                    <p className="text-sm text-slate-700 leading-snug">{signal.text}</p>
                    <span className="text-xs text-slate-400">{signal.time}</span>
                  </div>
                </li>
              )
            })}
          </ul>
        </GlassCard>

        {/* ── SENTIMENT CHART ────────────────────────────────────────────── */}
        <GlassCard className="col-span-12 md:col-span-7 flex flex-col gap-4">
          <div className="flex items-start justify-between flex-wrap gap-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-teal-600" />
              <h2 className="text-sm font-semibold text-slate-800">Share of Voice — Sentiment Trend</h2>
            </div>
            <div className="flex items-baseline gap-1.5">
              <span className="text-3xl font-bold text-teal-600 tabular-nums">{currentSentiment}%</span>
              <span
                className={`text-xs font-medium ${sentimentDelta >= 0 ? 'text-teal-500' : 'text-red-400'}`}
              >
                {sentimentDelta >= 0 ? '+' : ''}{sentimentDelta}% vs. Day 1
              </span>
            </div>
          </div>

          <div className="h-36 w-full">
            <SentimentChart data={SENTIMENT} />
          </div>

          <p className="text-xs text-slate-400 text-right">Last 30 days · Updated 5m ago</p>
        </GlassCard>

        {/* ── COMPETITOR COMPARISON ──────────────────────────────────────── */}
        <GlassCard className="col-span-12 md:col-span-7 flex flex-col gap-5">
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-indigo-500" />
            <h2 className="text-sm font-semibold text-slate-800">Competitor Comparison</h2>
          </div>

          <div className="flex flex-col divide-y divide-slate-100">
            {COMPETITORS.map((c) => (
              <div key={c.name} className="py-4 first:pt-0 last:pb-0 flex flex-col gap-2.5">
                <span className="text-xs font-semibold text-slate-700">{c.name}</span>
                <MetricBar label="Feature Parity"     value={c.featureParity}     color="bg-teal-500"   />
                <MetricBar label="Pricing Advantage"  value={c.pricingAdvantage}  color="bg-indigo-500" />
                <MetricBar label="SEO Health"         value={c.seoHealth}         color="bg-violet-500" />
              </div>
            ))}
          </div>
        </GlassCard>

        {/* ── STRATEGIC RESPONSES ────────────────────────────────────────── */}
        <GlassCard className="col-span-12 md:col-span-5 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-teal-600" />
              <h2 className="text-sm font-semibold text-slate-800">Strategic Responses</h2>
            </div>
            <span className="text-xs text-slate-400">
              {doneCount}/{actions.length} done
            </span>
          </div>

          <ul className="flex flex-col gap-2">
            {actions.map((action) => (
              <li
                key={action.id}
                onClick={() => toggleAction(action.id)}
                className={`flex items-start gap-3 p-3 rounded-2xl cursor-pointer transition-colors select-none ${
                  action.done
                    ? 'bg-slate-50/60'
                    : 'bg-white/40 hover:bg-white/70'
                }`}
              >
                {/* Custom checkbox */}
                <div
                  className={`mt-0.5 w-4 h-4 rounded-full border-2 shrink-0 flex items-center justify-center transition-colors ${
                    action.done
                      ? 'bg-teal-500 border-teal-500'
                      : 'border-slate-300 bg-white/60'
                  }`}
                >
                  {action.done && <Checkmark />}
                </div>

                <div className="flex flex-col gap-1 min-w-0 flex-1">
                  <span
                    className={`text-sm leading-snug ${
                      action.done ? 'line-through text-slate-400' : 'text-slate-700'
                    }`}
                  >
                    {action.text}
                  </span>
                  <span
                    className={`self-start text-xs font-medium px-2 py-0.5 rounded-full ${PRIORITY_BADGE[action.priority]}`}
                  >
                    {action.priority}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </GlassCard>

      </div>
    </div>
  )
}
