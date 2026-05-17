import { useState } from 'react'
import type { GameStateData } from '../types'
import Card from './Card'
import './Game.css'

interface GameProps {
  gameState: GameStateData
  player: number
  error: string
  onPlayCard: (cardIndex: number, target: string) => void
  onDraw: () => void
  onStuck: () => void
  onPlayAgain: () => void
}

function Game({ gameState, player, error, onPlayCard, onDraw, onStuck, onPlayAgain }: GameProps) {
  const [selectedCard, setSelectedCard] = useState<number | null>(null)

  if (gameState.status === 'finished') {
    const won = gameState.winner === player
    return (
      <div className="game-over">
        <h1>{won ? 'SPEED! You win!' : 'You lost!'}</h1>
        <button className="play-again-btn" onClick={onPlayAgain}>
          Play Again
        </button>
      </div>
    )
  }

  const handleCenterClick = (target: string) => {
    if (selectedCard !== null) {
      onPlayCard(selectedCard, target)
      setSelectedCard(null)
    }
  }

  const handleHandClick = (index: number) => {
    setSelectedCard(selectedCard === index ? null : index)
  }

  return (
    <div className="game-board">
      {error && <div className="error-toast">{error}</div>}

      {/* Opponent area */}
      <div className="opponent-area">
        <div className="opponent-hand">
          {Array.from({ length: gameState.opponentHandCount || 0 }).map((_, i) => (
            <Card key={i} faceDown small />
          ))}
        </div>
        <div className="opponent-draw">
          {(gameState.opponentDrawCount || 0) > 0 && (
            <div className="pile-indicator">
              <Card faceDown small />
              <span className="pile-count">{gameState.opponentDrawCount}</span>
            </div>
          )}
        </div>
      </div>

      {/* Center area */}
      <div className="center-area">
        <div className="side-pile">
          {(gameState.sideLeftCount || 0) > 0 && (
            <div className="pile-indicator">
              <Card faceDown />
              <span className="pile-count">{gameState.sideLeftCount}</span>
            </div>
          )}
        </div>

        <div
          className={`center-card-slot ${selectedCard !== null ? 'target' : ''}`}
          onClick={() => handleCenterClick('left')}
        >
          {gameState.centerLeft && <Card card={gameState.centerLeft} />}
        </div>

        <div
          className={`center-card-slot ${selectedCard !== null ? 'target' : ''}`}
          onClick={() => handleCenterClick('right')}
        >
          {gameState.centerRight && <Card card={gameState.centerRight} />}
        </div>

        <div className="side-pile">
          {(gameState.sideRightCount || 0) > 0 && (
            <div className="pile-indicator">
              <Card faceDown />
              <span className="pile-count">{gameState.sideRightCount}</span>
            </div>
          )}
        </div>
      </div>

      {/* Player area */}
      <div className="player-area">
        <div className="player-draw">
          {(gameState.myDrawCount || 0) > 0 && (
            <div className="pile-indicator">
              <Card
                faceDown
                onClick={(gameState.myHand?.length || 0) < 5 ? onDraw : undefined}
              />
              <span className="pile-count">{gameState.myDrawCount}</span>
            </div>
          )}
        </div>
        <div className="player-hand">
          {gameState.myHand?.map((card, i) => (
            <Card
              key={`${card.rank}-${card.suit}-${i}`}
              card={card}
              selected={selectedCard === i}
              onClick={() => handleHandClick(i)}
            />
          ))}
        </div>
        <button
          className={`stuck-btn ${gameState.myStuck ? 'stuck-active' : ''}`}
          onClick={onStuck}
          disabled={gameState.myStuck}
        >
          {gameState.myStuck ? 'Waiting...' : 'Stuck!'}
        </button>
        {gameState.opponentStuck && (
          <span className="opponent-stuck-label">Opponent is stuck</span>
        )}
      </div>
    </div>
  )
}

export default Game
