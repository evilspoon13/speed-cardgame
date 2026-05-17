from pydantic import BaseModel
from typing import Optional


class Card(BaseModel):
    rank: int  # 1=A, 2-10, 11=J, 12=Q, 13=K
    suit: str  # "hearts", "diamonds", "clubs", "spades"

    @property
    def display_rank(self) -> str:
        names = {1: "A", 11: "J", 12: "Q", 13: "K"}
        return names.get(self.rank, str(self.rank))

    @property
    def suit_symbol(self) -> str:
        symbols = {"hearts": "♥", "diamonds": "♦", "clubs": "♣", "spades": "♠"}
        return symbols[self.suit]

    @property
    def color(self) -> str:
        return "red" if self.suit in ("hearts", "diamonds") else "black"

    def to_dict(self) -> dict:
        return {
            "rank": self.rank,
            "suit": self.suit,
            "displayRank": self.display_rank,
            "suitSymbol": self.suit_symbol,
            "color": self.color,
        }


class PlayCardMessage(BaseModel):
    type: str = "play_card"
    card_index: int
    target: str  # "left" or "right"


class ClientMessage(BaseModel):
    type: str
    card_index: Optional[int] = None
    target: Optional[str] = None
