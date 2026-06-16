import random
from models import Card


def create_deck() -> list[Card]:
    suits = ["hearts", "diamonds", "clubs", "spades"]
    return [Card(rank=r, suit=s) for s in suits for r in range(1, 14)]


def is_valid_play(card: Card, center_card: Card) -> bool:
    diff = abs(card.rank - center_card.rank)
    return diff == 1 or diff == 12  # diff==12 handles K↔A wrap


class GameState:
    def __init__(self):
        self.status: str = "waiting"  # waiting, playing, finished
        self.winner: int | None = None

        self.player1_hand: list[Card] = []
        self.player2_hand: list[Card] = []
        self.player1_draw_pile: list[Card] = []
        self.player2_draw_pile: list[Card] = []

        self.center_left: Card | None = None
        self.center_right: Card | None = None
        self.center_left_pile: list[Card] = []
        self.center_right_pile: list[Card] = []

        self.side_left: list[Card] = []
        self.side_right: list[Card] = []

        self.player1_stuck: bool = False
        self.player2_stuck: bool = False

        self.player1_ready: bool = False
        self.player2_ready: bool = False

    def deal(self):
        deck = create_deck()
        random.shuffle(deck)

        i = 0
        self.player1_hand = deck[i:i+5]; i += 5
        self.player1_draw_pile = deck[i:i+15]; i += 15
        self.center_left = deck[i]; i += 1
        self.side_left = deck[i:i+5]; i += 5
        self.side_right = deck[i:i+5]; i += 5
        self.center_right = deck[i]; i += 1
        self.player2_draw_pile = deck[i:i+15]; i += 15
        self.player2_hand = deck[i:i+5]

        self.center_left_pile = []
        self.center_right_pile = []
        self.status = "playing"
        self.winner = None
        self.player1_stuck = False
        self.player2_stuck = False

    def play_card(self, player: int, card_index: int, target: str) -> str | None:
        """Returns error message or None on success."""
        if self.status != "playing":
            return "Game is not in progress"

        hand = self.player1_hand if player == 1 else self.player2_hand

        if card_index < 0 or card_index >= len(hand):
            return "Invalid card index"

        if target not in ("left", "right"):
            return "Invalid target"

        center_card = self.center_left if target == "left" else self.center_right
        card = hand[card_index]

        if not is_valid_play(card, center_card):
            return f"Cannot play {card.display_rank} on {center_card.display_rank}"

        hand.pop(card_index)

        if target == "left":
            self.center_left_pile.append(self.center_left)
            self.center_left = card
        else:
            self.center_right_pile.append(self.center_right)
            self.center_right = card

        # Reset stuck flags when a card is played
        self.player1_stuck = False
        self.player2_stuck = False

        self._check_win(player)
        return None

    def draw_card(self, player: int) -> str | None:
        """Returns error message or None on success."""
        if self.status != "playing":
            return "Game is not in progress"

        hand = self.player1_hand if player == 1 else self.player2_hand
        draw_pile = self.player1_draw_pile if player == 1 else self.player2_draw_pile

        if len(hand) >= 5:
            return "Hand is full"

        if len(draw_pile) == 0:
            return "Draw pile is empty"

        hand.append(draw_pile.pop(0))
        return None

    def declare_stuck(self, player: int) -> str | None:
        """Returns error message or None. Handles flip if both stuck."""
        if self.status != "playing":
            return "Game is not in progress"

        if player == 1:
            self.player1_stuck = True
        else:
            self.player2_stuck = True

        if self.player1_stuck and self.player2_stuck:
            self._flip_side_cards()
            self.player1_stuck = False
            self.player2_stuck = False

        return None

    def _flip_side_cards(self):
        if self.side_left and self.side_right:
            # Flip one from each side onto the center
            self.center_left_pile.append(self.center_left)
            self.center_left = self.side_left.pop(0)
            self.center_right_pile.append(self.center_right)
            self.center_right = self.side_right.pop(0)
        else:
            # Side piles exhausted — reshuffle center piles
            self._reshuffle_center()

    def _reshuffle_center(self):
        all_cards = self.center_left_pile + self.center_right_pile
        all_cards.append(self.center_left)
        all_cards.append(self.center_right)
        random.shuffle(all_cards)

        self.center_left = all_cards.pop(0)
        self.center_right = all_cards.pop(0)
        self.center_left_pile = []
        self.center_right_pile = []

        # Distribute remaining as side piles
        mid = len(all_cards) // 2
        self.side_left = all_cards[:mid]
        self.side_right = all_cards[mid:]

    def _check_win(self, player: int):
        hand = self.player1_hand if player == 1 else self.player2_hand
        draw_pile = self.player1_draw_pile if player == 1 else self.player2_draw_pile

        if len(hand) == 0 and len(draw_pile) == 0:
            self.status = "finished"
            self.winner = player

    def get_state_for_player(self, player: int) -> dict:
        """Returns game state from a player's perspective."""
        my_hand = self.player1_hand if player == 1 else self.player2_hand
        my_draw_count = len(self.player1_draw_pile if player == 1 else self.player2_draw_pile)
        opp_hand_count = len(self.player2_hand if player == 1 else self.player1_hand)
        opp_draw_count = len(self.player2_draw_pile if player == 1 else self.player1_draw_pile)

        return {
            "status": self.status,
            "winner": self.winner,
            "myHand": [c.to_dict() for c in my_hand],
            "myDrawCount": my_draw_count,
            "opponentHandCount": opp_hand_count,
            "opponentDrawCount": opp_draw_count,
            "centerLeft": self.center_left.to_dict() if self.center_left else None,
            "centerRight": self.center_right.to_dict() if self.center_right else None,
            "sideLeftCount": len(self.side_left),
            "sideRightCount": len(self.side_right),
            "myStuck": self.player1_stuck if player == 1 else self.player2_stuck,
            "opponentStuck": self.player2_stuck if player == 1 else self.player1_stuck,
            "player": player,
        }

    def get_lobby_state(self, player: int) -> dict:
        return {
            "status": "waiting",
            "player": player,
            "player1Ready": self.player1_ready,
            "player2Ready": self.player2_ready,
        }
