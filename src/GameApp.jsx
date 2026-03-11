import { useState, useCallback } from 'react'
import LandingPage from './pages/LandingPage'
import GamePage from './pages/GamePage'
import ResultsPage from './pages/ResultsPage'
import LeaderboardPage from './pages/LeaderboardPage'

export default function GameApp({ onBack }) {
  const [page, setPage] = useState('landing')
  const [currentCall, setCurrentCall] = useState(null)
  const [gameResult, setGameResult] = useState(null)
  const [sessionId] = useState(() => `session_${Date.now()}_${Math.random().toString(36).slice(2)}`)
  const [sessionScore, setSessionScore] = useState(0)
  const [roundsPlayed, setRoundsPlayed] = useState(0)

  const startGame = useCallback((call) => {
    setCurrentCall(call)
    setGameResult(null)
    setPage('game')
  }, [])

  const handleGuessResult = useCallback((result) => {
    setGameResult(result)
    setSessionScore(prev => prev + (result.score?.total_score || 0))
    setRoundsPlayed(prev => prev + 1)
    setPage('results')
  }, [])

  const playAgain = useCallback(() => {
    setCurrentCall(null)
    setGameResult(null)
    setPage('landing')
  }, [])

  const goToLeaderboard = useCallback(() => {
    setPage('leaderboard')
  }, [])

  return (
    <div className="min-h-screen">
      {page === 'landing' && (
        <LandingPage
          onStart={startGame}
          sessionScore={sessionScore}
          roundsPlayed={roundsPlayed}
          onLeaderboard={goToLeaderboard}
          onBack={onBack}
        />
      )}
      {page === 'game' && currentCall && (
        <GamePage
          call={currentCall}
          sessionId={sessionId}
          onResult={handleGuessResult}
          onBack={playAgain}
        />
      )}
      {page === 'results' && gameResult && (
        <ResultsPage
          result={gameResult}
          call={currentCall}
          onPlayAgain={playAgain}
          onLeaderboard={goToLeaderboard}
        />
      )}
      {page === 'leaderboard' && (
        <LeaderboardPage
          onBack={() => setPage('landing')}
          sessionScore={sessionScore}
        />
      )}
    </div>
  )
}
