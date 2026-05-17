import { useState, useEffect, useRef, useCallback } from 'react'
import Lobby from './components/Lobby'
import Game from './components/Game'
import type { GameStateData } from './types'

function App() {
  const [gameState, setGameState] = useState<GameStateData | null>(null)
  const [player, setPlayer] = useState<number>(0)
  const [error, setError] = useState<string>('')
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const mountedRef = useRef(true)

  const connect = useCallback(() => {
    if (!mountedRef.current) return

    // Close any existing connection
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.close()
    }

    const wsUrl = import.meta.env.VITE_WS_URL || `ws://${window.location.hostname}:8000/ws`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws
    let intentionalClose = false

    ws.onopen = () => {
      if (mountedRef.current) setConnected(true)
    }

    ws.onmessage = (event) => {
      if (!mountedRef.current) return
      const data = JSON.parse(event.data)

      if (data.type === 'connected') {
        setPlayer(data.player)
      } else if (data.type === 'game_state') {
        setGameState(data)
        setError('')
      } else if (data.type === 'error') {
        if (data.message === 'Game is full') {
          intentionalClose = true
          setError('Game is full — waiting for a slot...')
        } else {
          setError(data.message)
          setTimeout(() => setError(''), 2000)
        }
      } else if (data.type === 'opponent_disconnected') {
        setGameState(null)
        setPlayer(0)
        setConnected(false)
        intentionalClose = true
        ws.close()
        setTimeout(connect, 1000)
      }
    }

    ws.onclose = () => {
      if (!mountedRef.current) return
      setConnected(false)
      if (!intentionalClose) {
        setTimeout(connect, 2000)
      }
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    connect()
    return () => {
      mountedRef.current = false
      if (wsRef.current) {
        wsRef.current.onclose = null
        wsRef.current.close()
      }
    }
  }, [connect])

  const send = useCallback((msg: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg))
    }
  }, [])

  if (!connected) {
    return <div className="status">Connecting...</div>
  }

  if (!gameState || gameState.status === 'waiting') {
    return (
      <Lobby
        player={player}
        gameState={gameState}
        onReady={() => send({ type: 'ready' })}
      />
    )
  }

  return (
    <Game
      gameState={gameState}
      player={player}
      error={error}
      onPlayCard={(cardIndex, target) =>
        send({ type: 'play_card', cardIndex, target })
      }
      onDraw={() => send({ type: 'draw_card' })}
      onStuck={() => send({ type: 'stuck' })}
      onPlayAgain={() => send({ type: 'play_again' })}
    />
  )
}

export default App
