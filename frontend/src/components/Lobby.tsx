import type { GameStateData } from '../types'
import './Lobby.css'

interface LobbyProps {
  player: number
  gameState: GameStateData | null
  onReady: () => void
}

function Lobby({ player, gameState, onReady }: LobbyProps) {
  const myReady = player === 1 ? gameState?.player1Ready : gameState?.player2Ready
  const opponentReady = player === 1 ? gameState?.player2Ready : gameState?.player1Ready
  const opponentConnected =
    (player === 1 && gameState?.player2Ready !== undefined) ||
    (player === 2 && gameState?.player1Ready !== undefined)

  return (
    <div className="lobby">
      <h1>Speed</h1>
      <p className="player-label">You are Player {player}</p>

      {!opponentConnected && (
        <p className="waiting">Waiting for opponent to connect...</p>
      )}

      {opponentConnected && !myReady && (
        <>
          {opponentReady && (
            <p className="opponent-ready">Opponent is ready!</p>
          )}
          <button className="ready-btn" onClick={onReady}>
            Ready!
          </button>
        </>
      )}

      {myReady && (
        <p className="waiting">Waiting for opponent to ready up...</p>
      )}
    </div>
  )
}

export default Lobby
