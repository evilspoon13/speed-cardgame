import { useState, useEffect, useRef, useCallback } from 'react'
import Lobby from './components/Lobby'
import Game from './components/Game'
import RoomBrowser from './components/RoomBrowser'
import ConnectionBanner from './components/ConnectionBanner'
import type { GameStateData, RoomInfo, ConnState } from './types'

function getClientId(): string {
  let id = localStorage.getItem('speed_client_id')
  if (!id) {
    id =
      typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : `c-${Date.now()}-${Math.random().toString(36).slice(2)}`
    localStorage.setItem('speed_client_id', id)
  }
  return id
}

function App() {
  const [conn, setConn] = useState<ConnState>('connecting')
  const [rooms, setRooms] = useState<RoomInfo[]>([])
  const [gameState, setGameState] = useState<GameStateData | null>(null)
  const [player, setPlayer] = useState<number>(0)
  const [roomId, setRoomId] = useState<number | null>(null)
  const [error, setError] = useState<string>('')
  const [notice, setNotice] = useState<string>('')

  const wsRef = useRef<WebSocket | null>(null)
  const mountedRef = useRef(true)
  const roomIdRef = useRef<number | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const attemptRef = useRef(0)

  const setRoom = (id: number | null) => {
    roomIdRef.current = id
    setRoomId(id)
  }

  const connect = useCallback(() => {
    if (!mountedRef.current) return
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current)
      reconnectTimer.current = null
    }
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.close()
    }
    if (attemptRef.current === 0) setConn('connecting')

    const wsUrl =
      import.meta.env.VITE_WS_URL || `ws://${window.location.hostname}:8000/ws`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws
    let stop = false // set when we must not auto-reconnect (e.g. taken over)

    ws.onopen = () => {
      if (!mountedRef.current) return
      attemptRef.current = 0
      setConn('online')
      // Resume the room we were in (grace-period reconnect).
      if (roomIdRef.current != null) {
        ws.send(JSON.stringify({ type: 'join', clientId: getClientId(), room: roomIdRef.current }))
      }
    }

    ws.onmessage = (event) => {
      if (!mountedRef.current) return
      const data = JSON.parse(event.data)
      switch (data.type) {
        case 'ping':
          ws.send(JSON.stringify({ type: 'pong' }))
          break
        case 'rooms':
          setRooms(data.rooms)
          break
        case 'connected':
          setPlayer(data.player)
          setRoom(data.room)
          break
        case 'game_state':
          if (data.player) setPlayer(data.player)
          if (data.room != null) setRoom(data.room)
          setGameState(data)
          break
        case 'notice':
          setNotice(data.message)
          break
        case 'error':
          if (data.message === 'Game is full') {
            setRoom(null)
            setGameState(null)
            setNotice('That room is full. Pick another.')
          } else {
            setError(data.message)
            setTimeout(() => setError(''), 2000)
          }
          break
        case 'taken_over':
          stop = true
          setRoom(null)
          setGameState(null)
          setPlayer(0)
          setNotice('This game was opened in another tab.')
          setConn('online')
          break
      }
    }

    ws.onclose = () => {
      if (!mountedRef.current || stop) return
      setConn('reconnecting')
      attemptRef.current += 1
      const delay = Math.min(1000 * attemptRef.current, 5000)
      reconnectTimer.current = setTimeout(connect, delay)
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    connect()
    return () => {
      mountedRef.current = false
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
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

  const joinRoom = (id: number) => {
    setNotice('')
    setRoom(id)
    send({ type: 'join', clientId: getClientId(), room: id })
  }

  const leaveRoom = () => {
    send({ type: 'leave' })
    setRoom(null)
    setGameState(null)
    setPlayer(0)
    setNotice('')
  }

  const rejoinNow = () => {
    attemptRef.current = 0
    connect()
  }

  const banner = <ConnectionBanner conn={conn} onRejoin={rejoinNow} />

  // Never connected yet.
  if (conn === 'connecting' && rooms.length === 0 && roomId === null) {
    return <div className="status">Connecting…</div>
  }

  // Browsing the room list.
  if (roomId === null) {
    return (
      <div className="screen">
        {banner}
        {notice && <p className="notice">{notice}</p>}
        <RoomBrowser rooms={rooms} onJoin={joinRoom} />
      </div>
    )
  }

  // Joined a room but no state yet.
  if (!gameState) {
    return (
      <div className="screen">
        {banner}
        <div className="status">Joining room {roomId}…</div>
      </div>
    )
  }

  if (gameState.status === 'waiting') {
    return (
      <div className="screen">
        {banner}
        <Lobby
          player={player}
          gameState={gameState}
          notice={notice}
          onReady={() => send({ type: 'ready' })}
          onLeave={leaveRoom}
        />
      </div>
    )
  }

  return (
    <div className="screen">
      {banner}
      <Game
        gameState={gameState}
        player={player}
        error={error}
        onPlayCard={(cardIndex, target) => send({ type: 'play_card', cardIndex, target })}
        onDraw={() => send({ type: 'draw_card' })}
        onStuck={() => send({ type: 'stuck' })}
        onPlayAgain={() => send({ type: 'play_again' })}
        onLeave={leaveRoom}
      />
    </div>
  )
}

export default App
