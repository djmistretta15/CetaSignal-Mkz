import { useState } from 'react'
import ResearchApp from './ResearchApp'
import GameApp from './GameApp'

export default function App() {
  const [mode, setMode] = useState('research')
  if (mode === 'game') return <GameApp onBack={() => setMode('research')} />
  return <ResearchApp onPlayGame={() => setMode('game')} />
}
