export interface CardData {
  rank: number
  suit: string
  displayRank: string
  suitSymbol: string
  color: string
}

export interface GameStateData {
  type: string
  status: string
  winner?: number
  player?: number
  room?: number
  opponentPresent?: boolean
  opponentConnected?: boolean
  paused?: boolean
  myHand?: CardData[]
  myDrawCount?: number
  opponentHandCount?: number
  opponentDrawCount?: number
  centerLeft?: CardData
  centerRight?: CardData
  sideLeftCount?: number
  sideRightCount?: number
  myStuck?: boolean
  opponentStuck?: boolean
  player1Ready?: boolean
  player2Ready?: boolean
}

export interface RoomInfo {
  id: number
  players: number
  status: string
}

export type ConnState = 'connecting' | 'online' | 'reconnecting'
