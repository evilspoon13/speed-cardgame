import type { ConnState } from '../types'
import './ConnectionBanner.css'

interface Props {
  conn: ConnState
  onRejoin: () => void
}

const LABELS: Record<ConnState, string> = {
  connecting: 'Connecting…',
  online: 'Connected',
  reconnecting: 'Reconnecting…',
}

function ConnectionBanner({ conn, onRejoin }: Props) {
  if (conn === 'reconnecting') {
    return (
      <div className="conn-banner reconnecting">
        <div className="conn-reconnect-inner">
          <span className="conn-spinner" />
          <span className="conn-reconnect-text">Connection lost — reconnecting…</span>
          <button className="conn-rejoin-btn" onClick={onRejoin}>
            Rejoin now
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className={`conn-banner ${conn}`}>
      <span className={`conn-dot ${conn}`} />
      <span>{LABELS[conn]}</span>
    </div>
  )
}

export default ConnectionBanner
