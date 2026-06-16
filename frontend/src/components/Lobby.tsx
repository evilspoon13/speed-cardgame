import type { GameStateData } from '../types'
import './Lobby.css'

interface LobbyProps {
  player: number
  gameState: GameStateData | null
  notice?: string
  onReady: () => void
  onLeave: () => void
}

function Lobby({ player, gameState, notice, onReady, onLeave }: LobbyProps) {
  const myReady = player === 1 ? gameState?.player1Ready : gameState?.player2Ready
  const opponentReady = player === 1 ? gameState?.player2Ready : gameState?.player1Ready
  const opponentPresent = gameState?.opponentPresent ?? false

  return (
    <div className="lobby">
      <h1>Speed</h1>
      <p className="player-label">
        Room {gameState?.room} · You are Player {player}
      </p>

      {notice && <p className="notice">{notice}</p>}

      <div className="seat-list">
        <div className="seat you">
          <span className="seat-name">You</span>
          <span className={`seat-state ${myReady ? 'ready' : ''}`}>
            {myReady ? 'Ready' : 'Not ready'}
          </span>
        </div>
        <div className="seat">
          <span className="seat-name">Opponent</span>
          <span className={`seat-state ${opponentPresent ? (opponentReady ? 'ready' : '') : 'absent'}`}>
            {opponentPresent ? (opponentReady ? 'Ready' : 'Not ready') : 'Empty'}
          </span>
        </div>
      </div>

      {!opponentPresent && (
        <p className="waiting">Waiting for an opponent to join…</p>
      )}

      {opponentPresent && !myReady && (
        <button className="ready-btn" onClick={onReady}>
          Ready!
        </button>
      )}

      {myReady && (
        <p className="waiting">Waiting for opponent to ready up…</p>
      )}

      <button className="leave-btn" onClick={onLeave}>
        Leave room
      </button>
    </div>
  )
}

export default Lobby
