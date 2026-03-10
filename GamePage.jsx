import { useState, useEffect, useRef, useCallback } from 'react'
import { ArrowLeft, Play, Pause, RotateCcw, Clock } from 'lucide-react'
import api from '../utils/api'

const GUESS_OPTIONS = [
  { id: 'CONTACT',   label: 'Contact',   emoji: '📡', description: "I'm here / Where are you?",       color: '#00D4FF', bg: 'hover:bg-signal-contact/10 hover:border-signal-contact' },
  { id: 'DIVE',      label: 'Dive',      emoji: '🌊', description: 'Going down — follow me',           color: '#0066CC', bg: 'hover:bg-signal-dive/10 hover:border-signal-dive' },
  { id: 'FORAGE',    label: 'Forage',    emoji: '🐟', description: 'Food detected / spread out',       color: '#00CC88', bg: 'hover:bg-signal-forage/10 hover:border-signal-forage' },
  { id: 'NAVIGATE',  label: 'Navigate',  emoji: '🧭', description: 'Directional / migration heading',  color: '#FF9900', bg: 'hover:bg-signal-navigate/10 hover:border-signal-navigate' },
  { id: 'BROADCAST', label: 'Broadcast', emoji: '📻', description: 'Stationary signal / advertisement','color': '#CC44FF', bg: 'hover:bg-signal-broadcast/10 hover:border-signal-broadcast' },
]

export default function GamePage({ call, sessionId, onResult, onBack }) {
  const [phase, setPhase] = useState('listen') // listen | guess | submitting
  const [selectedGuess, setSelectedGuess] = useState(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [playCount, setPlayCount] = useState(0)
  const [timeElapsed, setTimeElapsed] = useState(0)
  const [guessStartTime, setGuessStartTime] = useState(null)
  const [spectrogramData, setSpectrogramData] = useState([])
  const [playProgress, setPlayProgress] = useState(0)

  const canvasRef = useRef(null)
  const animFrameRef = useRef(null)
  const audioRef = useRef(null)
  const startTimeRef = useRef(null)
  const timerRef = useRef(null)

  // Generate synthetic spectrogram visualization based on call features
  useEffect(() => {
    generateSpectrogramData()
  }, [call])

  // Timer when in guess phase
  useEffect(() => {
    if (phase === 'guess') {
      setGuessStartTime(Date.now())
      timerRef.current = setInterval(() => {
        setTimeElapsed(prev => prev + 1)
      }, 1000)
    }
    return () => clearInterval(timerRef.current)
  }, [phase])

  // Draw spectrogram on canvas
  useEffect(() => {
    if (!canvasRef.current || spectrogramData.length === 0) return
    drawSpectrogram()
  }, [spectrogramData, playProgress])

  function generateSpectrogramData() {
    const features = call.cadence_features || {}
    const peakFreq = features.peak_freq_hz || 200
    const contour = features.freq_contour || 'flat'
    const duration = call.duration_s || 2
    const urgency = features.urgency_score || 0.3

    // Generate frequency × time spectrogram data
    const timeSteps = 200
    const freqBins = 80
    const data = []

    for (let t = 0; t < timeSteps; t++) {
      const tNorm = t / timeSteps
      const row = new Array(freqBins).fill(0)

      // Base frequency track
      let centerFreqNorm
      if (contour === 'rising') {
        centerFreqNorm = 0.1 + tNorm * 0.4
      } else if (contour === 'descending') {
        centerFreqNorm = 0.6 - tNorm * 0.4
      } else if (contour === 'complex') {
        centerFreqNorm = 0.3 + 0.2 * Math.sin(tNorm * Math.PI * 3)
      } else {
        centerFreqNorm = 0.25 + (peakFreq > 1000 ? 0.4 : 0)
      }

      // IPI-based pulse pattern
      const ipi = features.inter_pulse_interval_ms || 500
      const ipiNorm = Math.min(ipi / 5000, 1)
      const isPulseActive = urgency > 0.5
        ? (t % Math.max(2, Math.floor(ipiNorm * 20))) < 3
        : true

      if (isPulseActive || urgency < 0.4) {
        const spread = peakFreq > 1000 ? 8 : 4
        for (let f = 0; f < freqBins; f++) {
          const fNorm = f / freqBins
          const dist = Math.abs(fNorm - centerFreqNorm)
          const intensity = Math.exp(-dist * dist * spread * 20)

          // Amplitude envelope
          let envMult = 1
          const fadeIn = 0.05
          const fadeOut = 0.95
          if (tNorm < fadeIn) envMult = tNorm / fadeIn
          else if (tNorm > fadeOut) envMult = (1 - tNorm) / (1 - fadeOut)

          // Add noise floor
          const noise = Math.random() * 0.05
          row[f] = Math.min(1, intensity * envMult + noise)
        }
      }

      data.push(row)
    }

    setSpectrogramData(data)
  }

  function drawSpectrogram() {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const W = canvas.width
    const H = canvas.height

    ctx.clearRect(0, 0, W, H)

    // Background
    ctx.fillStyle = '#000D1A'
    ctx.fillRect(0, 0, W, H)

    const timeSteps = spectrogramData.length
    const freqBins = spectrogramData[0]?.length || 80
    const cellW = W / timeSteps
    const cellH = H / freqBins

    // Draw spectrogram
    for (let t = 0; t < timeSteps; t++) {
      for (let f = 0; f < freqBins; f++) {
        const intensity = spectrogramData[t][freqBins - 1 - f] // flip Y
        if (intensity < 0.02) continue

        // Color mapping: dark blue → cyan → white
        const r = Math.floor(intensity * 100)
        const g = Math.floor(intensity * 180)
        const b = Math.floor(100 + intensity * 155)
        const a = Math.min(1, intensity * 2)

        ctx.fillStyle = `rgba(${r},${g},${b},${a})`
        ctx.fillRect(t * cellW, f * cellH, cellW + 0.5, cellH + 0.5)
      }
    }

    // Playback cursor
    if (playProgress > 0) {
      const cursorX = playProgress * W
      const grad = ctx.createLinearGradient(cursorX - 2, 0, cursorX + 2, 0)
      grad.addColorStop(0, 'transparent')
      grad.addColorStop(0.5, 'rgba(0,212,255,0.9)')
      grad.addColorStop(1, 'transparent')
      ctx.fillStyle = grad
      ctx.fillRect(cursorX - 2, 0, 4, H)

      // Glow effect
      ctx.shadowBlur = 8
      ctx.shadowColor = 'rgba(0,212,255,0.5)'
      ctx.fillStyle = 'rgba(0,212,255,0.6)'
      ctx.fillRect(cursorX - 0.5, 0, 1, H)
      ctx.shadowBlur = 0
    }

    // Frequency labels
    ctx.fillStyle = 'rgba(0,212,255,0.3)'
    ctx.font = '9px monospace'
    const features = call.cadence_features || {}
    const maxFreq = Math.max(features.peak_freq_hz * 2 || 500, 500)
    for (let i = 1; i <= 4; i++) {
      const y = H * (1 - i/4)
      const freq = Math.floor((maxFreq * i/4) / 10) * 10
      ctx.fillText(`${freq}Hz`, 4, y - 2)
    }
  }

  const simulatePlayback = useCallback(() => {
    const duration = call.duration_s * 1000
    const start = Date.now()
    setIsPlaying(true)
    setPlayProgress(0)

    const animate = () => {
      const elapsed = Date.now() - start
      const progress = Math.min(elapsed / duration, 1)
      setPlayProgress(progress)

      if (progress < 1) {
        animFrameRef.current = requestAnimationFrame(animate)
      } else {
        setIsPlaying(false)
        setPlayCount(prev => {
          const next = prev + 1
          if (next >= 1) setPhase('guess')
          return next
        })
      }
    }

    animFrameRef.current = requestAnimationFrame(animate)
  }, [call.duration_s])

  const handlePlay = () => {
    if (isPlaying) return
    cancelAnimationFrame(animFrameRef.current)
    simulatePlayback()
  }

  const handleGuessSelect = (guessId) => {
    setSelectedGuess(guessId)
  }

  const handleSubmit = async () => {
    if (!selectedGuess) return
    setPhase('submitting')

    const timeTaken = guessStartTime ? (Date.now() - guessStartTime) / 1000 : null

    try {
      const result = await api.submitGuess({
        call_id: call.id,
        human_guess: selectedGuess,
        session_id: sessionId,
        time_taken_s: timeTaken
      })
      onResult(result)
    } catch (err) {
      // Offline fallback — build result locally
      const groundTruth = call.behavioral_class
      const humanCorrect = selectedGuess === groundTruth

      // Simple rule-based prediction for offline
      const features = call.cadence_features || {}
      let predicted = 'CONTACT'
      if (features.freq_contour === 'descending') predicted = 'DIVE'
      else if (features.freq_contour === 'rising' && features.peak_freq_hz < 500) predicted = 'CONTACT'
      else if (features.peak_freq_hz > 1500) predicted = 'FORAGE'
      else if (features.freq_contour === 'complex' && features.duration_s > 4) predicted = 'BROADCAST'
      else if (features.peak_freq_hz < 50) predicted = 'NAVIGATE'

      const classInfo = {
        CONTACT:   { label: 'Contact',   emoji: '📡', description: "I'm here / Where are you?",         color: '#00D4FF' },
        DIVE:      { label: 'Dive',       emoji: '🌊', description: 'Going down — follow me',            color: '#0066CC' },
        FORAGE:    { label: 'Forage',     emoji: '🐟', description: 'Food detected / spread out',        color: '#00CC88' },
        NAVIGATE:  { label: 'Navigate',   emoji: '🧭', description: 'Directional / migration heading',   color: '#FF9900' },
        BROADCAST: { label: 'Broadcast',  emoji: '📻', description: 'Stationary signal / advertisement', color: '#CC44FF' },
      }

      onResult({
        call_id: call.id,
        human_guess: selectedGuess,
        score: { human_correct: humanCorrect, result: humanCorrect ? 'correct' : 'wrong', total_score: humanCorrect ? 100 : 0, base_score: humanCorrect ? 100 : 0, beat_model_bonus: 0, model_was_correct: predicted === groundTruth },
        model_prediction: { predicted_class: predicted, predicted_label: classInfo[predicted].label, predicted_emoji: classInfo[predicted].emoji, predicted_description: classInfo[predicted].description, predicted_color: classInfo[predicted].color, confidence: 0.75, reasoning: ['Rule-based classification (offline mode)'], model_version: 'offline_fallback' },
        ground_truth: { class: groundTruth, label: classInfo[groundTruth].label, emoji: call.behavioral_emoji, outcome: call.behavioral_outcome, species: call.species, fun_fact: call.fun_fact || '', source: call.source },
        animation: { type: groundTruth.toLowerCase(), keyframes: [], duration_s: 60 },
        session: { total_score: humanCorrect ? 100 : 0, correct: humanCorrect ? 1 : 0, total: 1 }
      })
    }
  }

  return (
    <div className="min-h-screen relative">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-ocean-700/30">
        <button onClick={onBack} className="flex items-center gap-2 text-ocean-400 hover:text-ocean-200 transition-colors text-sm">
          <ArrowLeft size={16} />
          <span className="font-display">BACK</span>
        </button>
        <div className="flex items-center gap-3">
          <span className="text-xl">{call.behavioral_emoji || '🐋'}</span>
          <div>
            <div className="font-display text-sm text-ocean-100">{call.species}</div>
            <div className="text-xs text-ocean-400 capitalize">{call.call_type?.replace(/_/g, ' ')}</div>
          </div>
        </div>
        {phase === 'guess' && (
          <div className="flex items-center gap-2 text-ocean-400 text-sm">
            <Clock size={14} />
            <span className="font-display">{timeElapsed}s</span>
          </div>
        )}
        {phase !== 'guess' && <div className="w-20" />}
      </header>

      <div className="max-w-3xl mx-auto px-6 py-8">

        {/* Phase indicator */}
        <div className="flex items-center justify-center gap-6 mb-8">
          {['LISTEN', 'GUESS', 'REVEAL'].map((p, i) => {
            const phases = ['listen', 'guess', 'submitting']
            const active = phases.indexOf(phase) >= i
            return (
              <div key={p} className="flex items-center gap-2">
                {i > 0 && <div className={`w-8 h-px ${active ? 'bg-signal-contact' : 'bg-ocean-700'}`} />}
                <div className={`flex items-center gap-1.5 text-xs font-display ${active ? 'text-signal-contact' : 'text-ocean-600'}`}>
                  <div className={`w-2 h-2 rounded-full ${active ? 'bg-signal-contact' : 'bg-ocean-700'}`} />
                  {p}
                </div>
              </div>
            )
          })}
        </div>

        {/* Spectrogram */}
        <div className="glass p-4 mb-6">
          <div className="flex items-center justify-between mb-3">
            <div className="font-display text-xs text-ocean-400 tracking-widest">ACOUSTIC SPECTROGRAM</div>
            <div className="text-xs text-ocean-500">{call.duration_s}s · {call.cadence_features?.peak_freq_hz}Hz peak</div>
          </div>

          <canvas
            ref={canvasRef}
            width={600}
            height={180}
            className="w-full rounded-lg"
            style={{ imageRendering: 'pixelated' }}
          />

          {/* Feature tags */}
          <div className="flex flex-wrap gap-2 mt-3">
            {[
              { label: 'Contour', val: call.cadence_features?.freq_contour || 'unknown' },
              { label: 'Duration', val: `${call.duration_s}s` },
              { label: 'Peak', val: `${call.cadence_features?.peak_freq_hz}Hz` },
              { label: 'IPI', val: call.cadence_features?.inter_pulse_interval_ms ? `${Math.round(call.cadence_features.inter_pulse_interval_ms)}ms` : '—' },
            ].map(f => (
              <div key={f.label} className="glass px-2 py-1 text-xs">
                <span className="text-ocean-500">{f.label}: </span>
                <span className="text-ocean-300 font-display">{f.val}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Play controls */}
        <div className="flex items-center justify-center gap-4 mb-8">
          <button
            onClick={handlePlay}
            disabled={isPlaying}
            className={`flex items-center gap-3 px-8 py-3 rounded-xl font-display text-sm tracking-widest transition-all ${
              isPlaying
                ? 'bg-ocean-800 text-ocean-500 cursor-not-allowed'
                : 'bg-signal-contact/20 border border-signal-contact text-signal-contact hover:bg-signal-contact/30'
            }`}
          >
            {isPlaying ? (
              <><Pause size={16} /> PLAYING...</>
            ) : (
              <><Play size={16} /> {playCount === 0 ? 'PLAY CALL' : 'REPLAY'}</>
            )}
          </button>

          {playCount > 0 && (
            <div className="text-xs text-ocean-500 font-display">
              Played {playCount}×
            </div>
          )}
        </div>

        {/* Listen phase prompt */}
        {phase === 'listen' && (
          <div className="text-center glass p-6">
            <div className="text-4xl mb-3">👂</div>
            <div className="font-display text-ocean-200 mb-2">LISTEN CAREFULLY</div>
            <div className="text-sm text-ocean-400">
              Play the call above. Watch the spectrogram. What do you notice about the rhythm, pitch, and pattern?
            </div>
            <div className="mt-3 text-xs text-ocean-500">
              The call will auto-advance to guessing after you play it.
            </div>
          </div>
        )}

        {/* Guess phase */}
        {phase === 'guess' && (
          <div>
            <div className="text-center mb-6">
              <div className="font-display text-ocean-200 text-lg mb-1">WHAT IS THIS WHALE SIGNALING?</div>
              <div className="text-sm text-ocean-400">Based on the cadence, pitch, and rhythm of the call</div>
            </div>

            <div className="grid grid-cols-1 gap-3 mb-6">
              {GUESS_OPTIONS.map(opt => (
                <button
                  key={opt.id}
                  onClick={() => handleGuessSelect(opt.id)}
                  className={`flex items-center gap-4 p-4 rounded-xl border transition-all duration-200 text-left ${
                    selectedGuess === opt.id
                      ? `border-2 bg-white/5`
                      : `glass border-ocean-700/50 ${opt.bg}`
                  }`}
                  style={selectedGuess === opt.id ? { borderColor: opt.color, boxShadow: `0 0 20px ${opt.color}30` } : {}}
                >
                  <span className="text-2xl">{opt.emoji}</span>
                  <div className="flex-1">
                    <div className="font-display text-sm" style={{ color: selectedGuess === opt.id ? opt.color : undefined }}>
                      {opt.label.toUpperCase()}
                    </div>
                    <div className="text-xs text-ocean-400 mt-0.5">{opt.description}</div>
                  </div>
                  {selectedGuess === opt.id && (
                    <div className="w-2 h-2 rounded-full" style={{ background: opt.color }} />
                  )}
                </button>
              ))}
            </div>

            <button
              onClick={handleSubmit}
              disabled={!selectedGuess || phase === 'submitting'}
              className={`w-full py-4 font-display text-base tracking-widest rounded-xl transition-all ${
                selectedGuess
                  ? 'bg-gradient-to-r from-ocean-500 to-ocean-400 text-white hover:from-signal-contact/30 hover:to-ocean-400 cursor-pointer'
                  : 'bg-ocean-900 text-ocean-600 cursor-not-allowed'
              }`}
            >
              {phase === 'submitting' ? 'PROCESSING...' : 'LOCK IN MY ANSWER →'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
