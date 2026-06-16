import type { RoomInfo } from '../types'
import './RoomBrowser.css'

interface Props {
  rooms: RoomInfo[]
  onJoin: (id: number) => void
}

function statusLabel(room: RoomInfo): string {
  if (room.players >= 2) return room.status === 'playing' ? 'In game' : 'Full'
  if (room.players === 1) return 'Waiting for player'
  return 'Open'
}

function RoomBrowser({ rooms, onJoin }: Props) {
  return (
    <div className="room-browser">
      <h1>Speed</h1>
      <p className="room-subtitle">Pick a room to join</p>
      <div className="room-grid">
        {rooms.map((room) => {
          const full = room.players >= 2
          return (
            <button
              key={room.id}
              className={`room-card ${full ? 'full' : ''}`}
              onClick={() => !full && onJoin(room.id)}
              disabled={full}
            >
              <span className="room-name">Room {room.id}</span>
              <span className="room-count">{room.players}/2</span>
              <span className={`room-status s-${room.players >= 2 ? 'full' : room.players}`}>
                {statusLabel(room)}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default RoomBrowser
