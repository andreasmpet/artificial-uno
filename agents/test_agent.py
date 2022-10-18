from agents.unoagent import UnoAgent
from unotypes import *
import random

UNO_CARD_COUNT = 108
STARTING_HAND_COUNT = 7
EMPTY_COLOR_HISTOGRAM = {Color.RED: 0, Color.BLUE: 0, Color.YELLOW: 0, Color.GREEN: 0, None: 0}
EMPTY_SIGN_HISTOGRAM = {Sign(sign): 0 for sign in Sign}
VALUE_CARD_PR_COLOR_COUNT = 19
ACTION_CARD_PR_COLOR_COUNT = 6
WILD_CARD_COUNT = 8
MAX_COLOR_HISTOGRAM = {Color.RED: VALUE_CARD_PR_COLOR_COUNT + ACTION_CARD_PR_COLOR_COUNT,
                       Color.BLUE: VALUE_CARD_PR_COLOR_COUNT + ACTION_CARD_PR_COLOR_COUNT,
                       Color.YELLOW: VALUE_CARD_PR_COLOR_COUNT + ACTION_CARD_PR_COLOR_COUNT,
                       Color.GREEN: VALUE_CARD_PR_COLOR_COUNT + ACTION_CARD_PR_COLOR_COUNT,
                       None: WILD_CARD_COUNT, }

ZEROES_COUNT = 4
NON_ZEROES_COUNT = 8
STANDARD_ACTION_COUNT = 8
WILD_ACTION_COUNT = 4
MAX_SIGN_HISTOGRAM = {Sign.ZERO: ZEROES_COUNT,
                      Sign.ONE: NON_ZEROES_COUNT,
                      Sign.TWO: NON_ZEROES_COUNT,
                      Sign.THREE: NON_ZEROES_COUNT,
                      Sign.FOUR: NON_ZEROES_COUNT,
                      Sign.FIVE: NON_ZEROES_COUNT,
                      Sign.SIX: NON_ZEROES_COUNT,
                      Sign.SEVEN: NON_ZEROES_COUNT,
                      Sign.EIGHT: NON_ZEROES_COUNT,
                      Sign.NINE: NON_ZEROES_COUNT,
                      Sign.DRAW_TWO: STANDARD_ACTION_COUNT,
                      Sign.REVERSE: STANDARD_ACTION_COUNT,
                      Sign.SKIP: STANDARD_ACTION_COUNT,
                      Sign.DRAW_FOUR: WILD_ACTION_COUNT,
                      Sign.CHANGE_COLOR: WILD_ACTION_COUNT}


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
        self.agent_hand_color_probabilities = {}
        self.agent_hand_sign_probabilities = {}

    def get_action(self, observations, **kwargs) -> Action:
        current_observation = observations[-1]
        current_score = sum(current_observation.scores)

        # If the score has changed, we've reset and started a new round.
        score_has_changed = current_score != self.last_observed_score

        if score_has_changed:
            self.prepare_for_new_round(current_observation, observations[0])

        self.update_from_observations(observations)

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

        for observation in new_observations_since_last_turn:
            self.played_cards.append(observation.top_card)
            self.remaining_cards_in_deck = self.calc_remaining_cards(current_observation)
            self.played_cards_color_histogram, self.played_cards_signs_histogram = self.calc_histograms(
                self.played_cards)
            if self.prev_observation is not None:
                agent_index = self.prev_observation.agent_idx
                self.update_hand_probabilities(agent_index, observation)
                # is_observation_ours = agent_index == current_observation.agent_idx
                # if not is_observation_ours:
                #     self.update_agents_predicted_hand(agent_index, observation)

            self.prev_observation = observation

        print("## PROBABILITIES")
        print(self.agent_hand_color_probabilities)
        print(self.agent_hand_sign_probabilities)
        print("## END PROBABILITIES")

        # self.played_cards.extend(map(lambda obs: obs.top_card, new_observations_since_last_turn))

    def calc_remaining_cards(self, current_observation: Observation):
        cards_in_player_hands = sum(current_observation.cards_left)
        total_cards_in_play_count = cards_in_player_hands + len(self.played_cards)

        return UNO_CARD_COUNT - total_cards_in_play_count

    def prepare_for_new_round(self, current_observation, initial_observation):
        # We must assume that the observation used here is a fresh hand for the current agent

        # cards_dealt_at_start_of_round = player_count * STARTING_HAND_COUNT
        # self.cards_remaining_in_draw_pile = UNO_CARD_COUNT - cards_dealt_at_start_of_round
        self.agent_hand_color_probabilities.clear()
        self.agent_hand_sign_probabilities.clear()
        self.played_cards.clear()
        self.update_hand_probabilities(current_observation.agent_idx, current_observation)

    @staticmethod
    def calc_histograms(cards: list[Card]):
        color_count = deepcopy(EMPTY_COLOR_HISTOGRAM)
        sign_count = deepcopy(EMPTY_SIGN_HISTOGRAM)
        for card in cards:
            color_count[card.color] = color_count[card.color] + 1
            sign_count[card.sign] = sign_count[card.sign] + 1

        return color_count, sign_count

    # def handle_draw_cards(self, agent_index, cards_drawn_count):
    #     print(f"agent {agent_index} drew {cards_drawn_count} cards")
    #
    # def handle_played_cards(self, agent_index, cards_played_count):
    #     print(f"agent {agent_index} played {cards_played_count} cards")

    # def update_agents_predicted_hand(self, agent_index, observation):
    #     card_count_start_of_prev_player_turn = self.prev_observation.cards_left[agent_index]
    #     card_count_start_of_this_player_turn = observation.cards_left[agent_index]
    #     card_count_diff = card_count_start_of_this_player_turn - card_count_start_of_prev_player_turn
    #     did_draw_cards = card_count_diff > 0
    #     did_play_card = card_count_diff < 0
    #     if did_draw_cards:
    #         self.handle_draw_cards(agent_index, card_count_diff)
    #     elif did_play_card:
    #         self.handle_played_cards(agent_index, card_count_diff)

    def update_hand_probabilities(self, our_agent_index, current_observation: Observation):
        agent_hand_sizes = current_observation.cards_left
        known_cards = self.played_cards + current_observation.hand.cards
        for idx, hand_size in enumerate(agent_hand_sizes):
            if idx != our_agent_index:
                new_agent_color_probabilities, new_agent_sign_probabilities = self.calc_hand_probabilities(
                    known_cards, hand_size)
                self.agent_hand_color_probabilities[idx] = \
                    self.avg_probabilities(new_agent_color_probabilities,
                                           self.agent_hand_color_probabilities.get(idx))
                self.agent_hand_sign_probabilities[idx] = \
                    self.avg_probabilities(new_agent_sign_probabilities,
                                           self.agent_hand_sign_probabilities.get(idx))

    @staticmethod
    def avg_probabilities(a: dict[str, float], b: dict[str, float]):
        avg = {}
        if b is None:
            return a
        # We assume that both dictionaries have the same keys
        for key in a.keys():
            prob_a = a.get(key) or 1.0
            prob_b = b.get(key) or 1.0
            avg[key] = (prob_a + prob_b) * 0.5

        return avg

    @staticmethod
    def calc_hand_probabilities(known_cards: list[Card], cards_in_hand_count: int):
        # unknown_cards_count = UNO_CARD_COUNT - len(current_observation.hand)
        unknown_cards_count = UNO_CARD_COUNT - len(known_cards)
        color_hist, sign_hist = TestAgent.calc_histograms(known_cards)
        remaining_colors_hist = {color: MAX_COLOR_HISTOGRAM[color] - count for (color, count) in color_hist.items()}
        remaining_signs_hist = {sign: MAX_SIGN_HISTOGRAM[sign] - count for (sign, count) in sign_hist.items()}
        color_probability = {color: remaining_colors_hist[color] / unknown_cards_count for
                             (color, count) in
                             color_hist.items()}
        sign_probability = {sign: remaining_signs_hist[sign] / unknown_cards_count for
                            (sign, count) in
                            sign_hist.items()}

        col_probs = {}

        for color in EMPTY_COLOR_HISTOGRAM.keys():
            probability_of_not_drawing_color = 1
            for _ in range(0, cards_in_hand_count):
                probability_of_not_drawing_color *= 1 - color_probability[color]

            col_probs[color] = 1 - probability_of_not_drawing_color

        sign_probs = {}
        for sign in Sign:
            probability_of_not_drawing_sign = 1
            for _ in range(0, cards_in_hand_count):
                probability_of_not_drawing_sign *= 1 - sign_probability[sign]

            sign_probs[sign] = 1 - probability_of_not_drawing_sign

        return col_probs, sign_probs
