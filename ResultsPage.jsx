import { useState, useEffect, useRef } from 'react'
import { RotateCcw, Award, ChevronRight } from 'lucide-react'

const CLASS_COLORS = {
  CONTACT:   '#00D4FF',
  DIVE:      '#0066CC',
  FORAGE:    '#00CC88',
  NAVIGATE:  '#FF9900',
  BROADCAST: '#CC44FF',
}

export default function ResultsPage({ result, call, onPlayAgain, onLeaderboard }) {
  const [revealPhase, setRevealPhase] = useState(0)
  // 0=human result, 1=model reveal, 2=ground truth, 3=animation, 4=full
  const canvasRef = useRef(null)
  const animRef = useRef(null)
  const [animTime, setAnimTime] = useState(0)

  const { score, model_prediction, ground_truth, animation } = result
  const humanGuessInfo = getClassInfo(result.human_guess)
  const gtColor = CLASS_COLORS[ground_truth.class] || '#00D4FF'

  // Auto-advance through reveal phases
  useEffect(() => {
    const timings = [1200, 2400, 3600, 4800]
    timings.forEach((t, i) => {
      setTimeout(() => setRevealPhase(i + 1), t)
    })
  }, [])

  // Animate whale behavior
  useEffect(() => {
    if (revealPhase < 3) return
    const start = Date.now()
    const tick = () => {
      setAnimTime((Date.now() - start) / 1000)
      animRef.current = requestAnimationFrame(tick)
    }
    animRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(animRef.current)
  }, [revealPhase])

  // Draw animation
  useEffect(() => {
    if (revealPhase < 3 || !canvasRef.current) return
    drawBehaviorAnimation()
  }, [animTime, revealPhase])

  function drawBehaviorAnimation() {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const W = canvas.width
    const H = canvas.height
    const t = Math.min(animTime, 8)
    const prog = t / 8

    ctx.clearRect(0, 0, W, H)

    // Ocean background
    const gradient = ctx.createLinearGradient(0, 0, 0, H)
    gradient.addColorStop(0, '#001122')
    gradient.addColorStop(0.15, '#001a33')
    gradient.addColorStop(1, '#000511')
    ctx.fillStyle = gradient
    ctx.fillRect(0, 0, W, H)

    // Surface line
    const surfaceY = H * 0.15
    ctx.strokeStyle = 'rgba(0,212,255,0.2)'
    ctx.lineWidth = 1
    ctx.setLineDash([4, 8])
    ctx.beginPath()
    ctx.moveTo(0, surfaceY)
    ctx.lineTo(W, surfaceY)
    ctx.stroke()
    ctx.setLineDash([])

    // Surface label
    ctx.fillStyle = 'rgba(0,212,255,0.3)'
    ctx.font = '9px monospace'
    ctx.fillText('SURFACE', 8, surfaceY - 4)

    // Depth markers
    for (let d = 1; d <= 3; d++) {
      const y = surfaceY + (H - surfaceY) * (d/4)
      ctx.strokeStyle = 'rgba(0,102,204,0.1)'
      ctx.lineWidth = 0.5
      ctx.beginPath()
      ctx.moveTo(0, y)
      ctx.lineTo(W, y)
      ctx.stroke()
      ctx.fillStyle = 'rgba(0,102,204,0.3)'
      ctx.fillText(`-${d * 25}m`, 8, y + 10)
    }

    const animationType = ground_truth.class

    if (animationType === 'DIVE') {
      drawDiveAnimation(ctx, W, H, surfaceY, prog, gtColor)
    } else if (animationType === 'CONTACT') {
      drawContactAnimation(ctx, W, H, surfaceY, prog, gtColor)
    } else if (animationType === 'FORAGE') {
      drawForageAnimation(ctx, W, H, surfaceY, prog, gtColor)
    } else if (animationType === 'NAVIGATE') {
      drawNavigateAnimation(ctx, W, H, surfaceY, prog, gtColor)
    } else if (animationType === 'BROADCAST') {
      drawBroadcastAnimation(ctx, W, H, surfaceY, prog, gtColor)
    }

    // Time indicator
    ctx.fillStyle = 'rgba(0,212,255,0.4)'
    ctx.font = '10px monospace'
    const displayTime = Math.floor(prog * (animation?.duration_s || 60))
    ctx.fillText(`T+${displayTime}s`, W - 50, 20)
  }

  function drawWhale(ctx, x, y, color, size = 1, angle = 0, label = '') {
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(angle)
    ctx.scale(size, size)

    // Body
    const bodyGrad = ctx.createRadialGradient(0, 0, 2, 0, 0, 20)
    bodyGrad.addColorStop(0, color)
    bodyGrad.addColorStop(1, color.replace(')', ',0.3)').replace('rgb', 'rgba'))
    ctx.fillStyle = bodyGrad
    ctx.beginPath()
    ctx.ellipse(0, 0, 22, 8, 0, 0, Math.PI * 2)
    ctx.fill()

    // Tail
    ctx.fillStyle = color
    ctx.beginPath()
    ctx.moveTo(18, 0)
    ctx.lineTo(28, -7)
    ctx.lineTo(30, 0)
    ctx.lineTo(28, 7)
    ctx.closePath()
    ctx.fill()

    // Fin
    ctx.beginPath()
    ctx.moveTo(-5, -8)
    ctx.lineTo(2, -18)
    ctx.lineTo(8, -8)
    ctx.closePath()
    ctx.fill()

    // Glow
    ctx.shadowBlur = 15
    ctx.shadowColor = color
    ctx.strokeStyle = color + '60'
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.ellipse(0, 0, 22, 8, 0, 0, Math.PI * 2)
    ctx.stroke()
    ctx.shadowBlur = 0

    ctx.restore()

    if (label) {
      ctx.fillStyle = 'rgba(0,212,255,0.6)'
      ctx.font = '9px monospace'
      ctx.fillText(label, x - 15, y - 20)
    }
  }

  function drawSonarRing(ctx, x, y, radius, color, alpha) {
    ctx.strokeStyle = color + Math.floor(alpha * 255).toString(16).padStart(2, '0')
    ctx.lineWidth = 1.5
    ctx.beginPath()
    ctx.arc(x, y, radius, 0, Math.PI * 2)
    ctx.stroke()
  }

  function drawDiveAnimation(ctx, W, H, surfaceY, prog, color) {
    const startX = W / 2
    const startY = surfaceY + 10
    const endY = surfaceY + (H - surfaceY) * 0.85
    const currentY = startY + (endY - startY) * Math.min(prog * 1.5, 1)
    const currentX = startX + Math.sin(prog * 2) * 20

    // Dive trail
    ctx.strokeStyle = color + '30'
    ctx.lineWidth = 2
    ctx.setLineDash([3, 6])
    ctx.beginPath()
    ctx.moveTo(startX, startY)
    ctx.quadraticCurveTo(startX + 30, startY + (currentY - startY) * 0.5, currentX, currentY)
    ctx.stroke()
    ctx.setLineDash([])

    // Depth indicator
    const depth = Math.floor(Math.min(prog * 1.5, 1) * 80)
    if (depth > 0) {
      ctx.fillStyle = color + 'AA'
      ctx.font = 'bold 11px monospace'
      ctx.fillText(`-${depth}m`, currentX + 30, currentY)
    }

    drawWhale(ctx, currentX, currentY, color, 0.9, Math.PI * 0.15)

    if (prog < 0.3) {
      for (let i = 0; i < 3; i++) {
        const r = 20 + prog * 100 + i * 30
        drawSonarRing(ctx, startX, startY, r, color, Math.max(0, 0.5 - r/200))
      }
    }
  }

  function drawContactAnimation(ctx, W, H, surfaceY, prog, color) {
    const y = surfaceY + 20
    const w1x = W * 0.2 + prog * W * 0.25
    const w2x = W * 0.8 - prog * W * 0.25

    // Signal waves from caller
    for (let i = 0; i < 4; i++) {
      const r = 20 + (prog * 200 + i * 50) % 200
      drawSonarRing(ctx, W * 0.2, y, r, color, Math.max(0, 0.4 - r/300))
    }

    // Convergence label
    if (prog > 0.5) {
      const dist = Math.floor((w2x - w1x))
      ctx.fillStyle = color + 'AA'
      ctx.font = '10px monospace'
      ctx.textAlign = 'center'
      ctx.fillText(`~${Math.max(0, Math.floor(dist * 0.8))}m apart`, W/2, y - 30)
      ctx.textAlign = 'left'
    }

    drawWhale(ctx, w1x, y, color, 1.0, 0, 'Caller')
    drawWhale(ctx, w2x, y, color + 'CC', 0.85, Math.PI, 'Responder')
  }

  function drawForageAnimation(ctx, W, H, surfaceY, prog, color) {
    const centerX = W / 2
    const centerY = surfaceY + 30
    const spread = prog * 160

    // Pod spreading
    const positions = [
      [0, 0], [1, -0.6], [-1, -0.5], [0.5, 0.8], [-0.5, 0.7]
    ]

    // Prey dots
    if (prog > 0.3) {
      ctx.fillStyle = '#FFFFFF30'
      for (let i = 0; i < 30; i++) {
        const px = centerX + Math.cos(i * 2.1) * (80 + i * 4)
        const py = centerY + Math.sin(i * 1.7) * (40 + i * 2)
        ctx.beginPath()
        ctx.arc(px, py, 2, 0, Math.PI * 2)
        ctx.fill()
      }
    }

    positions.forEach(([dx, dy], i) => {
      const wx = centerX + dx * spread
      const wy = centerY + dy * spread * 0.5
      const angle = Math.atan2(dy, dx)
      drawWhale(ctx, wx, wy, color, 0.8, angle, i === 0 ? 'Leader' : '')
    })

    ctx.fillStyle = color + '40'
    ctx.font = '10px monospace'
    ctx.textAlign = 'center'
    ctx.fillText(`Foraging spread: ~${Math.floor(spread * 1.5)}m`, centerX, surfaceY - 10)
    ctx.textAlign = 'left'
  }

  function drawNavigateAnimation(ctx, W, H, surfaceY, prog, color) {
    const y = surfaceY + 25
    const startX = W * 0.05
    const x = startX + prog * (W * 0.8)

    // Heading trail
    ctx.strokeStyle = color + '20'
    ctx.lineWidth = 3
    ctx.beginPath()
    ctx.moveTo(startX, y)
    ctx.lineTo(x, y)
    ctx.stroke()

    // Direction arrow
    const arrowX = x + 40
    if (arrowX < W - 20) {
      ctx.strokeStyle = color + '60'
      ctx.lineWidth = 1.5
      ctx.beginPath()
      ctx.moveTo(x + 10, y)
      ctx.lineTo(arrowX, y)
      ctx.moveTo(arrowX - 8, y - 5)
      ctx.lineTo(arrowX, y)
      ctx.lineTo(arrowX - 8, y + 5)
      ctx.stroke()
    }

    // Speed indicator
    ctx.fillStyle = color + 'AA'
    ctx.font = '10px monospace'
    ctx.fillText(`~12 km/h`, x - 20, y - 20)

    // Companion whale
    drawWhale(ctx, x - 40, y + 15, color + '80', 0.75, 0)
    drawWhale(ctx, x, y, color, 1.0, 0, 'Leading')
  }

  function drawBroadcastAnimation(ctx, W, H, surfaceY, prog, color) {
    const cx = W / 2
    const cy = surfaceY + 40

    // Expanding signal rings
    for (let i = 0; i < 6; i++) {
      const r = 30 + (prog * 300 + i * 50) % 300
      const alpha = Math.max(0, 0.5 - r / 350)
      drawSonarRing(ctx, cx, cy, r, color, alpha)
    }

    // Range indicator
    ctx.fillStyle = color + '30'
    ctx.beginPath()
    ctx.arc(cx, cy, Math.min(prog * 200, W * 0.45), 0, Math.PI * 2)
    ctx.fill()

    drawWhale(ctx, cx, cy, color, 1.1, 0, 'Broadcasting')

    ctx.fillStyle = color + 'AA'
    ctx.font = '10px monospace'
    ctx.textAlign = 'center'
    ctx.fillText(`Signal range: ~200km`, cx, H - 15)
    ctx.textAlign = 'left'

    // Stationary indicator
    if (prog > 0.5) {
      ctx.fillStyle = '#FFFFFF40'
      ctx.font = '10px monospace'
      ctx.textAlign = 'center'
      ctx.fillText(`Stationary ${Math.floor(prog * 40)}min`, cx, surfaceY - 10)
      ctx.textAlign = 'left'
    }
  }

  function getClassInfo(classId) {
    const info = {
      CONTACT:   { label: 'Contact',   emoji: '📡', color: '#00D4FF' },
      DIVE:      { label: 'Dive',       emoji: '🌊', color: '#0066CC' },
      FORAGE:    { label: 'Forage',     emoji: '🐟', color: '#00CC88' },
      NAVIGATE:  { label: 'Navigate',   emoji: '🧭', color: '#FF9900' },
      BROADCAST: { label: 'Broadcast',  emoji: '📻', color: '#CC44FF' },
    }
    return info[classId] || { label: classId, emoji: '❓', color: '#666' }
  }

  const isHumanCorrect = score.human_correct
  const isModelCorrect = score.model_was_correct
  const modelInfo = getClassInfo(model_prediction.predicted_class)
  const gtInfo = getClassInfo(ground_truth.class)

  return (
    <div className="min-h-screen">
      <div className="max-w-2xl mx-auto px-6 py-8">

        {/* Score header */}
        <div className={`glass p-5 mb-6 text-center border-2 ${isHumanCorrect ? 'border-green-500/50' : 'border-red-500/20'}`}
          style={{ boxShadow: isHumanCorrect ? '0 0 30px rgba(0,255,128,0.2)' : '0 0 30px rgba(255,50,50,0.1)' }}>
          <div className="text-4xl mb-2">{isHumanCorrect ? '🎯' : '🔬'}</div>
          <div className="font-display text-2xl mb-1" style={{ color: isHumanCorrect ? '#00FF88' : '#FF6644' }}>
            {isHumanCorrect ? 'CORRECT!' : 'NOT QUITE'}
          </div>
          <div className="font-display text-4xl text-ocean-100 mb-1">+{score.total_score}</div>
          {score.beat_model_bonus > 0 && (
            <div className="text-xs font-display text-yellow-400">+{score.beat_model_bonus} BEAT THE AI BONUS!</div>
          )}
          <div className="text-xs text-ocean-400 mt-2">{score.result === 'adjacent' ? 'Adjacent class — close but not exact' : ''}</div>
        </div>

        {/* Three-way comparison */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          {/* Human */}
          <div className={`glass p-4 text-center border ${isHumanCorrect ? 'border-green-500/40' : 'border-red-500/20'}`}>
            <div className="text-xs font-display text-ocean-400 mb-2">YOU GUESSED</div>
            <div className="text-2xl mb-1">{humanGuessInfo.emoji}</div>
            <div className="text-sm font-display" style={{ color: humanGuessInfo.color }}>{humanGuessInfo.label}</div>
            <div className="text-lg mt-1">{isHumanCorrect ? '✅' : '❌'}</div>
          </div>

          {/* Model — revealed in phase 1+ */}
          <div className={`glass p-4 text-center border transition-opacity duration-700 ${revealPhase >= 1 ? 'opacity-100' : 'opacity-0'} ${isModelCorrect ? 'border-green-500/30' : 'border-orange-500/20'}`}>
            <div className="text-xs font-display text-ocean-400 mb-2">AI PREDICTED</div>
            <div className="text-2xl mb-1">{modelInfo.emoji}</div>
            <div className="text-sm font-display" style={{ color: modelInfo.color }}>{modelInfo.label}</div>
            <div className="text-lg mt-1">{isModelCorrect ? '✅' : '❌'}</div>
            {revealPhase >= 1 && (
              <div className="text-xs text-ocean-500 mt-1">{Math.round(model_prediction.confidence * 100)}% conf.</div>
            )}
          </div>

          {/* Ground truth — revealed in phase 2+ */}
          <div className={`glass p-4 text-center border-2 transition-opacity duration-700 ${revealPhase >= 2 ? 'opacity-100' : 'opacity-0'}`}
            style={{ borderColor: revealPhase >= 2 ? gtColor + '60' : 'transparent', boxShadow: revealPhase >= 2 ? `0 0 20px ${gtColor}30` : 'none' }}>
            <div className="text-xs font-display text-ocean-400 mb-2">GROUND TRUTH</div>
            <div className="text-2xl mb-1">{ground_truth.emoji}</div>
            <div className="text-sm font-display" style={{ color: gtColor }}>{ground_truth.label}</div>
            <div className="text-xs text-ocean-400 mt-1">Verified</div>
          </div>
        </div>

        {/* What actually happened */}
        {revealPhase >= 2 && (
          <div className="glass p-4 mb-6 border border-ocean-500/20">
            <div className="text-xs font-display text-ocean-400 mb-2 tracking-widest">WHAT ACTUALLY HAPPENED</div>
            <p className="text-ocean-200 text-sm leading-relaxed">{ground_truth.outcome}</p>
            <div className="text-xs text-ocean-500 mt-2">Source: {ground_truth.source}</div>
          </div>
        )}

        {/* Behavioral animation */}
        {revealPhase >= 3 && (
          <div className="glass p-4 mb-6">
            <div className="text-xs font-display text-ocean-400 mb-3 tracking-widest">BEHAVIORAL VISUALIZATION</div>
            <canvas
              ref={canvasRef}
              width={540}
              height={200}
              className="w-full rounded-lg"
            />
            <div className="text-xs text-ocean-500 mt-2 text-center">
              {animation?.pod_response || 'Animated from NOAA tag data'}
            </div>
          </div>
        )}

        {/* Model reasoning */}
        {revealPhase >= 1 && model_prediction.reasoning?.length > 0 && (
          <div className="glass p-4 mb-6">
            <div className="text-xs font-display text-ocean-400 mb-3 tracking-widest">AI REASONING</div>
            <div className="space-y-1">
              {model_prediction.reasoning.map((r, i) => (
                <div key={i} className="flex items-start gap-2 text-xs text-ocean-400">
                  <span className="text-signal-contact mt-0.5">›</span>
                  <span>{r}</span>
                </div>
              ))}
            </div>
            <div className="text-xs text-ocean-600 mt-2">Model: {model_prediction.model_version}</div>
          </div>
        )}

        {/* Fun fact */}
        {revealPhase >= 4 && ground_truth.fun_fact && (
          <div className="glass p-4 mb-6 border border-signal-contact/20">
            <div className="text-xs font-display text-signal-contact mb-2 tracking-widest">🐋 DID YOU KNOW</div>
            <p className="text-ocean-300 text-sm leading-relaxed">{ground_truth.fun_fact}</p>
          </div>
        )}

        {/* Actions */}
        {revealPhase >= 4 && (
          <div className="flex gap-3">
            <button
              onClick={onPlayAgain}
              className="flex-1 flex items-center justify-center gap-2 py-4 font-display text-sm tracking-widest rounded-xl bg-gradient-to-r from-ocean-500 to-ocean-400 text-white hover:from-signal-contact/30 hover:to-ocean-400 transition-all"
            >
              <RotateCcw size={16} />
              PLAY AGAIN
            </button>
            <button
              onClick={onLeaderboard}
              className="flex items-center justify-center gap-2 px-6 py-4 font-display text-sm tracking-widest rounded-xl glass border-ocean-500/30 text-ocean-300 hover:text-signal-contact hover:border-signal-contact/50 transition-all"
            >
              <Award size={16} />
              SCORES
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
