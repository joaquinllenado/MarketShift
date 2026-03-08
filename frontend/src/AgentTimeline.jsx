import { useState, useEffect } from 'react'

const STEPS = [
  'Learning more about the company',
  'Checking their Product Site',
  'Checking their Product Hunt',
  'Checking their Blog Posts',
  'Finding out if they have any new features',
  'Almost done',
]

const STEP_DURATION = 1400 // ms per step

function Checkmark() {
  return (
    <svg viewBox="0 0 12 12" className="w-3.5 h-3.5" aria-hidden>
      <polyline
        points="1.5,6.5 4.5,9.5 10.5,2.5"
        fill="none"
        stroke="white"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export default function AgentTimeline({ onComplete }) {
  const [stepIdx, setStepIdx] = useState(0)
  const [complete, setComplete] = useState(false)

  useEffect(() => {
    if (complete) return

    // Hold on the last step, then mark complete and call back
    if (stepIdx >= STEPS.length - 1) {
      const t = setTimeout(() => {
        setComplete(true)
        setTimeout(() => onComplete?.(), 900)
      }, STEP_DURATION)
      return () => clearTimeout(t)
    }

    // Advance to next step
    const t = setTimeout(() => setStepIdx((s) => s + 1), STEP_DURATION)
    return () => clearTimeout(t)
  }, [stepIdx, complete, onComplete])

  return (
    <div className="relative min-h-screen flex items-center justify-center px-4 py-20 overflow-hidden">

      {/* Animated gradient background */}
      <div className="absolute inset-0 gradient-animate" />

      {/* Soft vignette */}
      <div className="absolute inset-0 bg-linear-to-b from-black/10 via-transparent to-black/10 pointer-events-none" />

      {/* Glass card */}
      <div className="relative bg-white/25 backdrop-blur-2xl border border-white/35 rounded-[2.5rem] p-8 sm:p-12 w-full max-w-md shadow-2xl shadow-black/10">

        {/* Header */}
        <div className="flex flex-col gap-1 mb-10">
          <span className="text-xs font-semibold tracking-widest uppercase" style={{color:'#1a2a4a'}}>
            MarketShift Agent
          </span>
          <h2 className="text-2xl font-bold transition-all duration-500" style={{color:'#0f1f3d'}}>
            {complete ? 'Research complete ✓' : 'Researching your competitors…'}
          </h2>
        </div>

        {/* Timeline */}
        <div className="flex flex-col">
          {STEPS.map((step, i) => {
            const isDone = complete || i < stepIdx
            const isActive = !complete && i === stepIdx
            const isLast = i === STEPS.length - 1

            return (
              <div key={i} className="flex gap-5">

                {/* Left col: dot + connector line */}
                <div className="flex flex-col items-center">

                  <div
                    className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-all duration-500"
                    style={
                      isDone
                        ? { background: '#FF9E13', boxShadow: '0 4px 12px rgba(255,158,19,0.4)' }
                        : isActive
                        ? { background: 'rgba(255,255,255,0.7)', border: '2px solid #FF9E13', boxShadow: '0 2px 8px rgba(255,158,19,0.3)' }
                        : { background: 'rgba(255,255,255,0.3)', border: '1px solid rgba(255,255,255,0.5)' }
                    }
                  >
                    {isDone && <Checkmark />}
                    {isActive && (
                      <span className="w-2.5 h-2.5 rounded-full animate-pulse" style={{background:'#FF9E13'}} />
                    )}
                  </div>

                  {!isLast && (
                    <div className="w-0.5 flex-1 my-1.5 bg-slate-200 min-h-7 relative overflow-hidden rounded-full">
                      <div
                        className="absolute inset-x-0 top-0 rounded-full transition-all duration-700 ease-in-out"
                        style={{ background: '#FF9E13', height: isDone ? '100%' : '0%' }}
                      />
                    </div>
                  )}
                </div>

                {/* Right col: step text */}
                <div className={`pt-1 flex flex-col gap-0.5 ${isLast ? 'pb-0' : 'pb-5'}`}>
                  <p
                    className="text-sm font-medium leading-snug transition-all duration-500"
                    style={{
                      color: isDone ? '#1a3a6a' : isActive ? '#0f1f3d' : '#4a6080'
                    }}
                  >
                    {step}
                  </p>
                  {isActive && (
                    <p className="text-xs animate-pulse" style={{color:'#2a4a7a'}}>Working on it…</p>
                  )}
                </div>

              </div>
            )
          })}
        </div>

      </div>
    </div>
  )
}
