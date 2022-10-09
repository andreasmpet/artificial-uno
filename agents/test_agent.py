from agents.unoagent import UnoAgent
from unotypes import *
import random

UNO_CARD_COUNT = 108
STARTING_HAND_COUNT = 7
EMPTY_COLOR_HISTOGRAM = {Color.RED: 0, Color.BLUE: 0, Color.YELLOW: 0, Color.GREEN: 0, None: 0}
EMPTY_SIGN_HISTOGRAM = {Sign(sign): 0 for sign in Sign}
VALUE_CARD_COUNT = 19
ACTION_CARD_COUNT = 6
WILD_CARD_COUNT = 8
MAX_COLOR_HISTOGRAM = {Color.RED: VALUE_CARD_COUNT + ACTION_CARD_COUNT,
                       Color.BLUE: VALUE_CARD_COUNT + ACTION_CARD_COUNT,
                       Color.YELLOW: VALUE_CARD_COUNT + ACTION_CARD_COUNT,
                       Color.GREEN: VALUE_CARD_COUNT + ACTION_CARD_COUNT,
                       None: WILD_CARD_COUNT, }

MAX_SIGN_HISTOGRAM = {Color.RED: VALUE_CARD_COUNT + ACTION_CARD_COUNT,
                       Color.BLUE: VALUE_CARD_COUNT + ACTION_CARD_COUNT,
                       Color.YELLOW: VALUE_CARD_COUNT + ACTION_CARD_COUNT,
                       Color.GREEN: VALUE_CARD_COUNT + ACTION_CARD_COUNT,
                       None: WILD_CARD_COUNT, }


# NUMBER_OF_COLORED_CARDS = 19

class TestAgent(UnoAgent):

    def __init__(self, alias):
        super().__init__(alias)
        self.remaining_cards_in_deck = None
        self.prev_observation = None
        self.last_observed_score = None
        self.played_cards = []
        self.played_cards_color_histogram = deepcopy(EMPTY_COLOR_HISTOGRAM)
        self.played_cards_signs_histogram = deepcopy(EMPTY_SIGN_HISTOGRAM)
        self.color_drawn_probability = deepcopy(EMPTY_COLOR_HISTOGRAM)
        self.sign_drawn_probability = deepcopy(EMPTY_SIGN_HISTOGRAM)

    def get_action(self, observations, **kwargs) -> Action:
        current_observation = observations[-1]
        current_score = sum(current_observation.scores)

        # If the score has changed, we've reset and started a new round.
        score_has_changed = current_score != self.last_observed_score

        if score_has_changed:
            self.prepare_for_new_round(current_observation)

        self.update_from_observations(observations)

        self.prev_observation = current_observation
        self.last_observed_score = current_score

        action_space = observations[-1].action_space()

        play_card_actions = [action for action in action_space if isinstance(action, PlayCard)]
        if play_card_actions:
            return random.sample(play_card_actions, 1)[0]
        else:
            return random.sample(action_space, 1)[0]

    def update_from_observations(self, observations):
        current_observation = observations[-1]

        if self.prev_observation is not None:
            index = observations.index(self.prev_observation)
            new_observations_since_last_turn = observations[index:]
        else:
            new_observations_since_last_turn = observations

        self.played_cards.extend(map(lambda obs: obs.top_card, new_observations_since_last_turn))
        self.remaining_cards_in_deck = self.calc_remaining_cards(current_observation)
        self.update_histograms(self.played_cards)

    def calc_remaining_cards(self, current_observation: Observation):
        cards_in_player_hands = sum(current_observation.cards_left)
        total_cards_in_play_count = cards_in_player_hands + len(self.played_cards)

        return UNO_CARD_COUNT - total_cards_in_play_count

    def prepare_for_new_round(self, current_observation):
        # We must assume that the observation used here is a fresh hand for the current agent

        # cards_dealt_at_start_of_round = player_count * STARTING_HAND_COUNT
        # self.cards_remaining_in_draw_pile = UNO_CARD_COUNT - cards_dealt_at_start_of_round
        self.played_cards.clear()

    def update_histograms(self, played_cards: list):
        color_count = deepcopy(EMPTY_COLOR_HISTOGRAM)
        sign_count = deepcopy(EMPTY_SIGN_HISTOGRAM)
        for card in played_cards:
            color_count[card.color] = color_count[card.color] + 1
            sign_count[card.sign] = sign_count[card.sign] + 1

        self.played_cards_signs_histogram = sign_count
        self.played_cards_color_histogram = color_count
