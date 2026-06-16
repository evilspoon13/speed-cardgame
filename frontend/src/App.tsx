import { useState, useEffect, useRef, useCallback } from 'react'
import Lobby from './components/Lobby'
import Game from './components/Game'
import type { GameStateData } from './types'

type Status = 'idle' | 'connecting' | 'connected'

function getClientId(): string {
  let id = localStorage.getItem('speed_client_id')
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem('speed_client_id', id)
  }
  return id
}

function App() {
  const [gameState, setGameState] = useState<GameStateData | null>(null)
  const [player, setPlayer] = useState<number>(0)
  const [error, setError] = useState<string>('')
  const [notice, setNotice] = useState<string>('')
  const [status, setStatus] = useState<Status>('idle')
  const wsRef = useRef<WebSocket | null>(null)
  const mountedRef = useRef(true)

  const connect = useCallback(() => {
    if (!mountedRef.current) return

    // Close any existing connection without triggering its handlers.
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.close()
    }

    setNotice('')
    setError('')
    setStatus('connecting')

    const wsUrl =
      import.meta.env.VITE_WS_URL || `ws://${window.location.hostname}:8000/ws`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws
    let intentionalClose = false

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: 'join', clientId: getClientId() }))
    }

    ws.onmessage = (event) => {
      if (!mountedRef.current) return
      const data = JSON.parse(event.data)

      switch (data.type) {
        case 'ping':
          ws.send(JSON.stringify({ type: 'pong' }))
          break
        case 'connected':
          setPlayer(data.player)
          setStatus('connected')
          break
        case 'game_state':
          if (data.player) setPlayer(data.player)
          setGameState(data)
          setStatus('connected')
          setError('')
          break
        case 'error':
          if (data.message === 'Game is full') {
            intentionalClose = true
            setStatus('idle')
            setNotice('Game is full — both seats are taken right now.')
          } else {
            setError(data.message)
            setTimeout(() => setError(''), 2000)
          }
          break
        case 'taken_over':
          intentionalClose = true
          setStatus('idle')
          setGameState(null)
          setPlayer(0)
          setNotice('This game was opened in another tab.')
          break
        case 'opponent_disconnected':
          intentionalClose = true
          setStatus('idle')
          setGameState(null)
          setPlayer(0)
          setNotice('Your opponent left. Rejoin to start a new game.')
          ws.close()
          break
      }
    }

    ws.onclose = () => {
      if (!mountedRef.current) return
      if (!intentionalClose) {
        setStatus('idle')
        setGameState(null)
        setPlayer(0)
        setNotice('Connection lost. Tap Rejoin to reconnect.')
      }
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      if (wsRef.current) {
        wsRef.current.onclose = null
        wsRef.current.close()
      }
    }
  }, [])

  const send = useCallback((msg: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg))
    }
  }, [])

  if (status === 'idle') {
    return (
      <div className="landing">
        <h1>Speed</h1>
        {notice && <p className="notice">{notice}</p>}
        <button className="join-btn" onClick={connect}>
          {notice ? 'Rejoin' : 'Join Game'}
        </button>
      </div>
    )
  }

  if (status === 'connecting' || player === 0 || !gameState) {
    return <div className="status">Connecting...</div>
  }

  if (gameState.status === 'waiting') {
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
