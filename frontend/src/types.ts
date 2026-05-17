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
