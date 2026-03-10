import { useState, useEffect } from 'react'
import { Waves, Zap, BarChart2, ChevronRight, Award } from 'lucide-react'
import api from '../utils/api'

// Demo calls for when backend isn't running
const DEMO_CALLS = [
  { id: 'narw_upcall_001', species: 'North Atlantic Right Whale', call_type: 'upcall', behavioral_class: 'CONTACT', behavioral_emoji: '📡', difficulty: 1, duration_s: 1.2, description: 'Rising frequency sweep, ~170Hz', fun_fact: 'The most studied whale contact call. Functions like a "here I am" beacon.', behavioral_outcome: 'Pod convergence — two individuals approached within 50m over 3 minutes', source: 'NOAA NEFSC DCLDE 2013', cadence_features: { peak_freq_hz: 170, freq_contour: 'rising', duration_s: 1.2, inter_pulse_interval_ms: 1200, urgency_score: 0.2, repetition_hz: 0.1 } },
  { id: 'sei_downsweep_001', species: 'Sei Whale', call_type: 'downsweep', behavioral_class: 'DIVE', behavioral_emoji: '🌊', difficulty: 1, duration_s: 0.9, description: 'Sharp descending sweep 240→80Hz', fun_fact: 'Sei whale downsweeps reliably precede dives within 15 seconds.', behavioral_outcome: 'Dive initiated within 15s — depth 0→40m over 30 seconds', source: 'NOAA NEFSC DCLDE 2013', cadence_features: { peak_freq_hz: 240, freq_contour: 'descending', duration_s: 0.9, inter_pulse_interval_ms: 900, urgency_score: 0.35, repetition_hz: 0.0 } },
  { id: 'humpback_song_001', species: 'Humpback Whale', call_type: 'song_phrase', behavioral_class: 'BROADCAST', behavioral_emoji: '📻', difficulty: 2, duration_s: 8.1, description: 'Complex phrase, 200-800Hz', fun_fact: 'Humpback songs change every year across entire ocean basins — cultural transmission.', behavioral_outcome: 'Whale remained stationary during 40-minute song bout', source: 'NOAA SanctSound 2020', cadence_features: { peak_freq_hz: 400, freq_contour: 'complex', duration_s: 8.1, inter_pulse_interval_ms: 300, urgency_score: 0.15, repetition_hz: 0.12 } },
  { id: 'orca_burst_pulse_001', species: 'Orca (Southern Resident)', call_type: 'burst_pulse', behavioral_class: 'FORAGE', behavioral_emoji: '🐟', difficulty: 2, duration_s: 2.7, description: 'Rapid clicks ~2000Hz, 5-20ms IPI', fun_fact: 'Different orca pods have distinct foraging "dialects" — acoustic culture.', behavioral_outcome: 'Pod spread into foraging arc — 150-300m spacing within 90 seconds', source: 'NOAA Pacific Islands DCLDE 2022', cadence_features: { peak_freq_hz: 2000, freq_contour: 'flat', duration_s: 2.7, inter_pulse_interval_ms: 12, urgency_score: 0.75, repetition_hz: 5.2 } },
  { id: 'fin_20hz_001', species: 'Fin Whale', call_type: '20hz_pulse', behavioral_class: 'NAVIGATE', behavioral_emoji: '🧭', difficulty: 3, duration_s: 3.4, description: '20Hz pulse — pitched up 10x', fun_fact: '20Hz fin whale calls travel hundreds of miles through the SOFAR channel.', behavioral_outcome: 'Sustained directional heading for 45 minutes post-call', source: 'NOAA NEFSC DCLDE 2013', cadence_features: { peak_freq_hz: 20, freq_contour: 'flat', duration_s: 3.4, inter_pulse_interval_ms: 26000, urgency_score: 0.1, repetition_hz: 0.038 } },
  { id: 'blue_ab_call_001', species: 'Blue Whale', call_type: 'ab_call', behavioral_class: 'CONTACT', behavioral_emoji: '📡', difficulty: 4, duration_s: 18.5, description: 'Two-part tonal 17Hz — pitched up', fun_fact: 'Blue whale calls are the loudest animal sounds — 188dB, detectable across ocean basins.', behavioral_outcome: 'Response call received ~50km away 8 minutes later', source: 'NOAA NEFSC DCLDE 2013', cadence_features: { peak_freq_hz: 17, freq_contour: 'flat', duration_s: 18.5, inter_pulse_interval_ms: 18500, urgency_score: 0.1, repetition_hz: 0.05 } },
]

const GUESS_OPTIONS = [
  { id: 'CONTACT',   label: 'Contact',   emoji: '📡', description: "I'm here / Where are you?",       color: '#00D4FF' },
  { id: 'DIVE',      label: 'Dive',      emoji: '🌊', description: 'Going down — follow me',           color: '#0066CC' },
  { id: 'FORAGE',    label: 'Forage',    emoji: '🐟', description: 'Food detected / spread out',       color: '#00CC88' },
  { id: 'NAVIGATE',  label: 'Navigate',  emoji: '🧭', description: 'Directional / migration heading',  color: '#FF9900' },
  { id: 'BROADCAST', label: 'Broadcast', emoji: '📻', description: 'Stationary signal / advertisement','color': '#CC44FF' },
]

const DIFFICULTY_STARS = ['', '★', '★★', '★★★', '★★★★']

export default function LandingPage({ onStart, sessionScore, roundsPlayed, onLeaderboard }) {
  const [calls, setCalls] = useState(DEMO_CALLS)
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(false)
  const [hoveredCall, setHoveredCall] = useState(null)

  useEffect(() => {
    api.getCalls()
      .then(data => { if (data.calls?.length) setCalls(data.calls) })
      .catch(() => {}) // use demo data
  }, [])

  const handleStart = () => {
    if (!selected) return
    onStart(selected)
  }

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Animated background particles */}
      <Particles />

      {/* Header */}
      <header className="relative z-10 flex items-center justify-between px-6 py-5 border-b border-ocean-700/30">
        <div className="flex items-center gap-3">
          <div className="relative w-10 h-10">
            <div className="sonar-ring w-10 h-10" />
            <div className="sonar-ring w-10 h-10" />
            <span className="relative z-10 text-2xl">🐋</span>
          </div>
          <div>
            <div className="font-display text-lg text-ocean-100 tracking-wider">CETASIGNAL</div>
            <div className="text-xs text-ocean-300/60 font-display">WHALE LANGUAGE DECODER</div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {roundsPlayed > 0 && (
            <div className="glass px-4 py-2 text-sm">
              <span className="text-ocean-300">Score: </span>
              <span className="font-display text-signal-contact">{sessionScore}</span>
              <span className="text-ocean-400 ml-2">({roundsPlayed} rounds)</span>
            </div>
          )}
          <button onClick={onLeaderboard} className="flex items-center gap-2 glass px-4 py-2 text-sm text-ocean-200 hover:text-signal-contact transition-colors">
            <Award size={14} />
            <span className="font-display">SCORES</span>
          </button>
        </div>
      </header>

      {/* Hero */}
      <div className="relative z-10 text-center pt-16 pb-10 px-6">
        <div className="inline-flex items-center gap-2 glass px-4 py-1.5 mb-6 text-xs font-display text-ocean-300/80 tracking-widest">
          <Zap size={10} className="text-signal-contact" />
          REAL NOAA ACOUSTIC DATA · OPEN SCIENCE
        </div>

        <h1 className="text-5xl md:text-7xl font-display font-bold tracking-tight mb-4">
          <span className="text-ocean-100">CAN YOU DECODE</span>
          <br />
          <span className="bg-gradient-to-r from-signal-contact via-ocean-200 to-signal-broadcast bg-clip-text text-transparent">
            WHALE LANGUAGE?
          </span>
        </h1>

        <p className="text-ocean-300 text-lg md:text-xl max-w-2xl mx-auto mb-3 font-light">
          Hear a real whale call. Guess what it means. Then see what the whale actually did.
        </p>
        <p className="text-ocean-400 text-sm max-w-xl mx-auto">
          You vs. AI vs. ground truth. Every guess builds the validation dataset.
        </p>
      </div>

      {/* Call selector */}
      <div className="relative z-10 max-w-5xl mx-auto px-6 pb-8">
        <div className="text-center mb-6">
          <div className="font-display text-xs text-ocean-400 tracking-widest">SELECT A CALL TO DECODE</div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-8">
          {calls.map(call => (
            <CallCard
              key={call.id}
              call={call}
              selected={selected?.id === call.id}
              onSelect={() => setSelected(call)}
              onHover={setHoveredCall}
            />
          ))}
        </div>

        {/* Selected call detail + start */}
        {selected && (
          <div className="glass p-5 mb-6 border-ocean-500/30">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="text-xs font-display text-ocean-400 mb-1 tracking-widest">SELECTED</div>
                <div className="text-lg font-display text-ocean-100">{selected.species}</div>
                <div className="text-ocean-300 text-sm mt-1">{selected.description}</div>
                <div className="mt-3 text-xs text-ocean-400 leading-relaxed">
                  <span className="text-ocean-300">Fun fact:</span> {selected.fun_fact}
                </div>
                <div className="mt-2 text-xs text-ocean-500">Source: {selected.source}</div>
              </div>
              <div className="text-right shrink-0">
                <div className="text-xs font-display text-ocean-400 mb-1">DIFFICULTY</div>
                <div className="text-signal-navigate font-display">{DIFFICULTY_STARS[selected.difficulty || 1]}</div>
                <div className="text-xs text-ocean-500 mt-1">{selected.duration_s}s call</div>
              </div>
            </div>
          </div>
        )}

        <button
          onClick={handleStart}
          disabled={!selected}
          className={`w-full py-4 font-display text-lg tracking-widest rounded-xl transition-all duration-300 flex items-center justify-center gap-3 ${
            selected
              ? 'bg-gradient-to-r from-ocean-500 to-ocean-400 text-white hover:from-ocean-400 hover:to-signal-contact hover:shadow-lg hover:shadow-signal-contact/20 cursor-pointer'
              : 'bg-ocean-900 text-ocean-600 cursor-not-allowed'
          }`}
        >
          {selected ? (
            <>START DECODING <ChevronRight size={20} /></>
          ) : (
            'SELECT A CALL ABOVE'
          )}
        </button>
      </div>

      {/* How it works */}
      <div className="relative z-10 max-w-4xl mx-auto px-6 pb-16">
        <div className="text-center mb-8">
          <div className="font-display text-xs text-ocean-400 tracking-widest">HOW IT WORKS</div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { step: '01', icon: '🔊', label: 'Hear', desc: 'A real recorded whale call plays with live spectrogram' },
            { step: '02', icon: '🤔', label: 'Guess', desc: 'Choose what you think the call signals' },
            { step: '03', icon: '🤖', label: 'AI Predicts', desc: 'Our cadence model makes its prediction (hidden until now)' },
            { step: '04', icon: '🐋', label: 'Ground Truth', desc: 'See what the whale actually did after the call' },
          ].map(s => (
            <div key={s.step} className="glass p-4 text-center">
              <div className="font-display text-xs text-ocean-500 mb-2">{s.step}</div>
              <div className="text-2xl mb-2">{s.icon}</div>
              <div className="font-display text-sm text-ocean-100 mb-1">{s.label}</div>
              <div className="text-xs text-ocean-400 leading-relaxed">{s.desc}</div>
            </div>
          ))}
        </div>

        <div className="mt-8 glass p-5 text-center">
          <BarChart2 size={16} className="inline-block text-signal-contact mb-2" />
          <div className="text-xs text-ocean-400 leading-relaxed max-w-lg mx-auto">
            Every guess is anonymously logged. We track human accuracy vs. model accuracy vs. behavioral ground truth.
            When the model consistently beats human guesses — we've proven cadence encodes coordination signal.
            <span className="text-ocean-300"> That's the hypothesis.</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function CallCard({ call, selected, onSelect, onHover }) {
  const classColors = {
    CONTACT: 'border-signal-contact/40 hover:border-signal-contact',
    DIVE: 'border-signal-dive/40 hover:border-signal-dive',
    FORAGE: 'border-signal-forage/40 hover:border-signal-forage',
    NAVIGATE: 'border-signal-navigate/40 hover:border-signal-navigate',
    BROADCAST: 'border-signal-broadcast/40 hover:border-signal-broadcast',
  }
  const selectedColors = {
    CONTACT: 'border-signal-contact bg-signal-contact/10',
    DIVE: 'border-signal-dive bg-signal-dive/10',
    FORAGE: 'border-signal-forage bg-signal-forage/10',
    NAVIGATE: 'border-signal-navigate bg-signal-navigate/10',
    BROADCAST: 'border-signal-broadcast bg-signal-broadcast/10',
  }

  const cls = call.behavioral_class
  const stars = '★'.repeat(call.difficulty || 1)

  return (
    <button
      onClick={onSelect}
      onMouseEnter={() => onHover(call)}
      onMouseLeave={() => onHover(null)}
      className={`text-left p-4 rounded-xl border transition-all duration-200 ${
        selected ? selectedColors[cls] : `glass ${classColors[cls]}`
      }`}
    >
      <div className="flex items-start justify-between mb-2">
        <span className="text-xl">{call.behavioral_emoji || '📡'}</span>
        <span className="text-xs text-ocean-500 font-display">{stars}</span>
      </div>
      <div className="text-xs font-display text-ocean-300 truncate">{call.species}</div>
      <div className="text-xs text-ocean-500 mt-0.5 capitalize">{call.call_type?.replace(/_/g, ' ')}</div>
      <div className="text-xs text-ocean-600 mt-1">{call.duration_s}s</div>
    </button>
  )
}

function Particles() {
  const particles = Array.from({ length: 20 }, (_, i) => ({
    id: i,
    left: `${Math.random() * 100}%`,
    top: `${Math.random() * 100}%`,
    duration: `${4 + Math.random() * 8}s`,
    delay: `${Math.random() * 6}s`,
    fx: `${(Math.random() - 0.5) * 30}px`,
    fy: `${(Math.random() - 0.5) * 30}px`,
    fx2: `${(Math.random() - 0.5) * 20}px`,
    fy2: `${(Math.random() - 0.5) * 20}px`,
    opacity: 0.2 + Math.random() * 0.4,
  }))

  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden">
      {particles.map(p => (
        <div
          key={p.id}
          className="particle"
          style={{
            left: p.left,
            top: p.top,
            '--duration': p.duration,
            '--delay': p.delay,
            '--fx': p.fx,
            '--fy': p.fy,
            '--fx2': p.fx2,
            '--fy2': p.fy2,
            opacity: p.opacity,
            width: Math.random() > 0.7 ? '3px' : '2px',
            height: Math.random() > 0.7 ? '3px' : '2px',
          }}
        />
      ))}
    </div>
  )
}
