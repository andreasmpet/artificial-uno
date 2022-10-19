from enum import Enum
from dataclasses import dataclass
from typing import Literal
import itertools
import random
from unoexceptions import IllegalMoveException
from copy import deepcopy


class Color(str, Enum):
    RED = "RED"
    GREEN = "GREEN"
    BLUE = "BLUE"
    YELLOW = "YELLOW"


class Sign(str, Enum):
    ZERO = "ZERO"
    ONE = "ONE"
    TWO = "TWO"
    THREE = "THREE"
    FOUR = "FOUR"
    FIVE = "FIVE"
    SIX = "SIX"
    SEVEN = "SEVEN"
    EIGHT = "EIGHT"
    NINE = "NINE"
    SKIP = "SKIP"
    REVERSE = "REVERSE"
    DRAW_TWO = "DRAW_TWO"
    DRAW_FOUR = "DRAW_FOUR"
    CHANGE_COLOR = "CHANGE_COLOR"

    @property
    def is_wild(self):
        return self == Sign.DRAW_FOUR or self == Sign.CHANGE_COLOR

    @property
    def is_action(self):
        return (self == Sign.SKIP or
                self == Sign.REVERSE or
                self == Sign.DRAW_TWO or
                self.is_wild)

    @property
    def is_number(self):
        return not self.is_wild and not self.is_action

    @property
    def score(self) -> int:
        match self:
            case "ZERO":
                return 0
            case "ONE":
                return 1
            case "TWO":
                return 2
            case "THREE":
                return 3
            case "FOUR":
                return 4
            case "FIVE":
                return 5
            case "SIX":
                return 6
            case "SEVEN":
                return 7
            case "EIGHT":
                return 8
            case "NINE":
                return 9
            case "SKIP":
                return 20
            case "REVERSE":
                return 20
            case "DRAW_TWO":
                return 20
            case "DRAW_FOUR":
                return 50
            case "CHANGE_COLOR":
                return 50


@dataclass(frozen=True)
class Card:
    sign: Sign
    color: Color | None

    @property
    def is_wild(self) -> bool:
        return self.sign.is_wild

    @property
    def is_action(self):
        return self.sign.is_action

    @property
    def is_number(self):
        return self.sign.is_number

    def stacks_on(self, card):
        return (card is None or
                self.is_wild or
                self.color == card.color or
                self.sign == card.sign)

    def __eq__(self, other):
        if other is None:
            return False
        elif self.is_wild:
            return self.sign == other.sign
        else:
            return self.sign == other.sign and self.color == other.color

    def __post_init__(self):
        if not self.is_wild and self.color is None:
            raise TypeError("Color can only be None for DRAW_FOUR and CHANGE_COLOR cards")


@dataclass
class Hand:
    cards: list[Card]

    def __init__(self, initial_cards: list[Card]):
        self.cards = []
        self.add(initial_cards)

    def add(self, added_cards: list[Card]):
        for card in added_cards:
            if card.is_wild and card.color is not None:
                self.cards.append(Card(card.sign, None))
            else:
                self.cards.append(card)

    def remove(self, card: Card):
        if card in self:
            if card.is_wild:
                self.cards.remove(Card(card.sign, None))
            else:
                self.cards.remove(card)
            return card
        else:
            raise IllegalMoveException("Card not in hand")

    def __iter__(self):
        return self.cards.__iter__()

    def __len__(self):
        return len(self.cards)


@dataclass
class DrawPile:
    cards: list[Card]

    def __init__(self):
        self.cards = []

        non_wild_signs = [Sign(sign) for sign in Sign if not Sign(sign).is_wild]

        for c, s in itertools.product(Color, non_wild_signs):
            if s == Sign.ZERO:
                self.cards.append(Card(sign=s, color=c))
            else:
                self.cards.extend([Card(sign=s, color=c) for _ in range(2)])

        # Add wildcards
        self.cards.extend([Card(sign=Sign.CHANGE_COLOR, color=None) for _ in range(4)])
        self.cards.extend([Card(sign=Sign.DRAW_FOUR, color=None) for _ in range(4)])

        random.shuffle(self.cards)

    def top(self):
        return self.cards[-1]

    def shuffle(self):
        random.shuffle(self.cards)

    def pop(self) -> Card:
        card = self.cards[-1]
        self.cards = self.cards[:-1]
        return card

    def draw_cards(self, amount) -> list[Card]:
        drawn_cards = self.cards[-amount:]
        self.cards = self.cards[:-amount]
        return drawn_cards

    def distribute_hands(self, hand_amount) -> list[Hand]:
        return [Hand(self.draw_cards(7)) for _ in range(hand_amount)]

    def __len__(self):
        return len(self.cards)


@dataclass
class DiscardPile:
    cards: list[Card]

    def __init__(self, initial_card: Card):
        self.cards = [initial_card]

    def top(self):
        return self.cards[-1]

    def stack(self, card):
        if card.stacks_on(self.top()):
            self.cards.append(card)
        else:
            raise IllegalMoveException(f"{card} can not be placed on top of {self.top()}")

    def __len__(self):
        return len(self.cards)


@dataclass(frozen=True)
class PlayCard:
    card: Card


@dataclass(frozen=True)
class DrawCard:
    pass


@dataclass(frozen=True)
class SkipTurn:
    pass


@dataclass(frozen=True)
class AcceptDrawFour:
    pass


@dataclass(frozen=True)
class ChallengeDrawFour:
    pass


Action = PlayCard | DrawCard | SkipTurn | AcceptDrawFour | ChallengeDrawFour


@dataclass(frozen=True)
class Observation:
    game_won: bool
    is_initial_state: bool
    agent_idx: int
    top_card: Card
    hand: Hand
    cards_left: list[int]
    draw_pile_size: int
    discard_pile_size: int
    current_agent_idx: int
    direction: Literal[-1, 1]
    previously_drawn_card: Card | None
    can_challenge_draw_four: bool
    draw_four_stacked_on: Card | None
    challenger_idx: int | None
    revealed_hand_idx: int | None
    revealed_hand: Hand | None
    scores: list[int]

    def action_space(self) -> set[Action]:
        if self.agent_idx != self.current_agent_idx:
            return set()

        if self.can_challenge_draw_four:
            return {AcceptDrawFour(), ChallengeDrawFour()}

        action_space = set()
        playable_cards = []
        if self.previously_drawn_card:
            action_space.add(SkipTurn())
            if self.previously_drawn_card.stacks_on(self.top_card):
                playable_cards.append(self.previously_drawn_card)
        else:
            action_space.add(DrawCard())
            for card in self.hand:
                if card.stacks_on(self.top_card):
                    playable_cards.append(card)

        for card in playable_cards:
            if card.is_wild:
                action_space = action_space.union([PlayCard(Card(card.sign, Color(color))) for color in Color])
            else:
                action_space.add(PlayCard(card))

        return action_space

    # Raises exception
    def assert_valid(self, action: Action):
        assert self.agent_idx == self.current_agent_idx

        # Player has to either accept or challenge a played DRAW_FOUR-card
        if self.can_challenge_draw_four:
            assert action in [AcceptDrawFour(), ChallengeDrawFour()]
        else:
            assert action not in [AcceptDrawFour(), ChallengeDrawFour()]
            match action:
                case PlayCard(card):
                    assert card.color is not None
                    assert card in self.hand
                    assert card.stacks_on(self.top_card)
                    assert self.previously_drawn_card is None or card == self.previously_drawn_card

                case DrawCard():
                    assert self.previously_drawn_card is None

                case SkipTurn():
                    assert self.previously_drawn_card is not None

    def is_valid_action(self, action: Action) -> bool:
        try:
            self.assert_valid(action)
            return True
        except AssertionError:
            return False


@dataclass(frozen=True)
class GameState:
    game_won: bool
    is_initial_state: bool
    draw_pile: DrawPile
    hands: list[Hand]
    discard_pile: DiscardPile
    current_agent_idx: int
    direction: Literal[-1, 1]
    previously_drawn_card: Card | None
    can_challenge_draw_four: bool
    draw_four_stacked_on: Card | None
    challenger_idx: int | None
    revealed_hand_idx: int | None
    revealed_hand: Hand | None
    scores: list[int]

    def observe(self, agent_idx) -> Observation:
        if agent_idx == self.current_agent_idx:
            previously_drawn_card = self.previously_drawn_card
        else:
            previously_drawn_card = None

        if self.challenger_idx == agent_idx:
            revealed_hand = self.revealed_hand
        else:
            revealed_hand = None

        return deepcopy(Observation(
            game_won=self.game_won,
            is_initial_state=self.is_initial_state,
            agent_idx=agent_idx,
            hand=self.hands[agent_idx],
            cards_left=[len(hand) for hand in self.hands],
            draw_pile_size=len(self.draw_pile),
            discard_pile_size=len(self.discard_pile),
            top_card=self.discard_pile.top(),
            current_agent_idx=self.current_agent_idx,
            direction=self.direction,
            previously_drawn_card=previously_drawn_card,
            can_challenge_draw_four=self.can_challenge_draw_four,
            draw_four_stacked_on=self.draw_four_stacked_on,
            challenger_idx=self.challenger_idx,
            revealed_hand_idx=self.revealed_hand_idx,
            revealed_hand=revealed_hand,
            scores=self.scores))

    def assert_valid(self, agent_idx, action):
        self.observe(agent_idx).assert_valid(action)

    def is_valid_action(self, agent_idx, action) -> bool:
        try:
            self.assert_valid(agent_idx, action)
            return True
        except AssertionError:
            return False
