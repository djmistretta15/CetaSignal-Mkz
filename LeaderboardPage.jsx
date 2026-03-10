import { useState, useEffect } from 'react'
import { ArrowLeft, Trophy, Zap } from 'lucide-react'
import api from '../utils/api'

export default function LeaderboardPage({ onBack, sessionScore }) {
  const [leaderboard, setLeaderboard] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([api.getLeaderboard(), api.getStats()])
      .then(([lb, st]) => {
        setLeaderboard(lb.leaderboard || [])
        setStats(st)
      })
      .catch(() => {
        setLeaderboard([])
        setStats(null)
      })
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="min-h-screen">
      <header className="flex items-center gap-4 px-6 py-4 border-b border-ocean-700/30">
        <button onClick={onBack} className="flex items-center gap-2 text-ocean-400 hover:text-ocean-200 transition-colors text-sm">
          <ArrowLeft size={16} />
          <span className="font-display">BACK</span>
        </button>
        <div className="flex items-center gap-2">
          <Trophy size={18} className="text-yellow-400" />
          <span className="font-display text-ocean-100">LEADERBOARD</span>
        </div>
      </header>

      <div className="max-w-2xl mx-auto px-6 py-8">

        {/* Global stats */}
        {stats && stats.total_guesses > 0 && (
          <div className="grid grid-cols-3 gap-3 mb-8">
            <div className="glass p-4 text-center">
              <div className="text-xs font-display text-ocean-400 mb-1">TOTAL GUESSES</div>
              <div className="font-display text-2xl text-ocean-100">{stats.total_guesses}</div>
            </div>
            <div className="glass p-4 text-center">
              <div className="text-xs font-display text-ocean-400 mb-1">HUMAN ACCURACY</div>
              <div className="font-display text-2xl text-signal-contact">{Math.round(stats.human_accuracy * 100)}%</div>
            </div>
            <div className="glass p-4 text-center">
              <div className="text-xs font-display text-ocean-400 mb-1">AI ACCURACY</div>
              <div className="font-display text-2xl text-signal-broadcast">{Math.round(stats.model_accuracy * 100)}%</div>
            </div>
          </div>
        )}

        {/* Hypothesis meter */}
        {stats && stats.total_guesses > 0 && (
          <div className="glass p-5 mb-6">
            <div className="flex items-center gap-2 mb-3">
              <Zap size={14} className="text-signal-contact" />
              <div className="font-display text-xs text-ocean-300 tracking-widest">HYPOTHESIS STATUS</div>
            </div>
            <div className="text-sm text-ocean-300 mb-3">
              AI accuracy vs human accuracy on same calls
            </div>
            <div className="flex gap-3 items-center">
              <div className="flex-1 h-2 bg-ocean-800 rounded-full overflow-hidden">
                <div className="h-full rounded-full bg-signal-contact transition-all duration-1000"
                  style={{ width: `${Math.round(stats.human_accuracy * 100)}%` }} />
              </div>
              <span className="text-xs font-display text-signal-contact w-16">Human {Math.round(stats.human_accuracy * 100)}%</span>
            </div>
            <div className="flex gap-3 items-center mt-2">
              <div className="flex-1 h-2 bg-ocean-800 rounded-full overflow-hidden">
                <div className="h-full rounded-full bg-signal-broadcast transition-all duration-1000"
                  style={{ width: `${Math.round(stats.model_accuracy * 100)}%` }} />
              </div>
              <span className="text-xs font-display text-signal-broadcast w-16">AI {Math.round(stats.model_accuracy * 100)}%</span>
            </div>
            <div className="mt-3 text-xs text-ocean-500">
              {stats.hypothesis_support
                ? '✅ AI exceeds human baseline — cadence encoding hypothesis gaining support'
                : '⏳ More data needed — keep playing to build the validation set'}
            </div>
          </div>
        )}

        {/* Current session */}
        {sessionScore > 0 && (
          <div className="glass p-4 mb-6 border border-signal-contact/30">
            <div className="flex items-center justify-between">
              <div className="font-display text-xs text-signal-contact tracking-widest">YOUR SESSION</div>
              <div className="font-display text-xl text-ocean-100">{sessionScore} pts</div>
            </div>
          </div>
        )}

        {/* Leaderboard */}
        <div className="font-display text-xs text-ocean-400 mb-3 tracking-widest">TOP DECODERS</div>

        {loading ? (
          <div className="text-center text-ocean-500 py-8 text-sm">Loading...</div>
        ) : leaderboard.length === 0 ? (
          <div className="glass p-8 text-center">
            <div className="text-3xl mb-3">🐋</div>
            <div className="font-display text-ocean-300 mb-2">NO SCORES YET</div>
            <div className="text-sm text-ocean-500">Be the first to decode a whale call.</div>
          </div>
        ) : (
          <div className="space-y-2">
            {leaderboard.map((entry, i) => (
              <div key={entry.session_id} className="glass p-4 flex items-center gap-4">
                <div className="font-display text-sm w-6 text-center" style={{ color: i < 3 ? ['#FFD700','#C0C0C0','#CD7F32'][i] : '#444' }}>
                  {i + 1}
                </div>
                <div className="flex-1">
                  <div className="font-display text-sm text-ocean-200">
                    {entry.player_name || `Decoder #${entry.session_id.slice(-4)}`}
                  </div>
                  <div className="text-xs text-ocean-500">
                    {entry.correct}/{entry.total} correct · {Math.round(entry.accuracy * 100)}% accuracy
                  </div>
                </div>
                <div className="font-display text-lg text-signal-contact">{entry.total_score}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
