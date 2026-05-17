import type { CardData } from '../types'
import './Card.css'

interface CardProps {
  card?: CardData
  faceDown?: boolean
  selected?: boolean
  onClick?: () => void
  small?: boolean
}

function Card({ card, faceDown, selected, onClick, small }: CardProps) {
  const className = [
    'card',
    faceDown ? 'face-down' : '',
    selected ? 'selected' : '',
    small ? 'small' : '',
    card?.color === 'red' ? 'red' : 'black',
    onClick ? 'clickable' : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className={className} onClick={onClick}>
      {!faceDown && card && (
        <>
          <span className="card-rank top-left">{card.displayRank}</span>
          <span className="card-suit center">{card.suitSymbol}</span>
          <span className="card-rank bottom-right">{card.displayRank}</span>
        </>
      )}
      {faceDown && <span className="card-back">?</span>}
    </div>
  )
}

export default Card
