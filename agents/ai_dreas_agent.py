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

class AIDreasAgent(UnoAgent):
    remaining_cards_in_deck = None
    prev_observation = None
    discard_pile = None
    played_cards_color_histogram = None
    played_cards_sign_histogram = None
    agent_hand_color_probabilities = None
    agent_hand_sign_probabilities = None
    agent_card_delta_last_play = None
    agent_unplayable_hand = None

    def __init__(self, alias):
        super().__init__(alias)
        self.last_observed_score = None
        self.reset_round()

    def get_action(self, observations, **kwargs) -> Action:
        action_space = observations[-1].action_space()

        # try:
        current_observation = observations[-1]
        current_score = sum(current_observation.scores)

        # If the score has changed, we've reset and started a new round.
        score_has_changed = current_score != self.last_observed_score

        if score_has_changed:
            self.prepare_for_new_round(current_observation)

        self.update_from_observations(observations)

        self.last_observed_score = current_score

        last_obs = observations[-2] if len(observations) >= 2 else None
        return self.pick_action(current_observation, last_obs, action_space)
        # If any of my code crashes, let's just pick a random action why don't we? Better than crashing the game.
        # except Exception:
        #     play_card_actions = [action for action in action_space if isinstance(action, PlayCard)]
        #     if play_card_actions:
        #         return random.sample(play_card_actions, 1)[0]
        #     else:
        #         return random.sample(action_space, 1)[0]

    def pick_action(self, current_observation: Observation,
                    last_observation: Observation,
                    action_space: set[Action]):
        # If we only have one choice, we just have to choose it regardless. Skip all other logic.
        is_only_choice = len(action_space) == 1
        if is_only_choice:
            return action_space.pop()

        next_agent_index = self.get_next_agent_idx(current_observation)
        prev_agent_index = self.get_prev_agent_idx(current_observation)

        hand_color_histogram = AIDreasAgent.calc_color_histogram(current_observation.hand.cards)
        hand_sign_histogram = AIDreasAgent.calc_sign_histogram(current_observation.hand.cards)

        if current_observation.can_challenge_draw_four:
            if self.calc_should_challenge_draw_four(current_observation, next_agent_index, prev_agent_index,
                                                    hand_color_histogram):
                return ChallengeDrawFour()
            else:
                return AcceptDrawFour()

        ranked_actions = self.determine_optimal_card_plays(current_observation,
                                                           next_agent_index,
                                                           prev_agent_index,
                                                           hand_color_histogram,
                                                           hand_sign_histogram)

        if len(ranked_actions) > 0:
            # If we have more than one optimal play, pick one at random
            picked_action = random.sample(ranked_actions, 1)[0]
            # print(picked_action)
            return picked_action

        # We shouldn't really ever get down all the way here, but just in case we do, the contingency is to play a
        # random action so we don't stall the game.
        return random.sample(action_space, 1)[0]

    def determine_optimal_card_plays(self, current_observation,
                                     next_agent_index,
                                     prev_agent_index,
                                     hand_color_histogram,
                                     hand_sign_histogram):
        next_agent_remaining_cards = current_observation.cards_left[next_agent_index]
        prev_agent_remaining_cards = current_observation.cards_left[prev_agent_index]

        play_card_actions = [action for action in current_observation.action_space() if isinstance(action, PlayCard)]
        card_scores = {}

        # TODO: Make color priority rating have more or less weight on decision making
        remaining_card_count = len(current_observation.hand)
        is_in_low_card_mode = remaining_card_count <= 3
        color_priority_ratings = \
            self.calc_color_priority_rating(current_observation, is_in_low_card_mode, hand_color_histogram)
        sign_probabilities = self.agent_hand_sign_probabilities[next_agent_index]
        zero_value = 50  # Zeroes get extra priority to be played since they are hard to play
        bin_size = 2

        aggressive_mode_threshold = 3
        is_in_aggressive_mode = len([x for x in current_observation.cards_left if x < aggressive_mode_threshold]) > 0
        desire_to_do_action_modifier_in_passive_mode = 0.3
        desire_to_play_draw_cards_in_passive_mode = 0.01
        desire_to_do_action_modifier = 1 if is_in_aggressive_mode else desire_to_do_action_modifier_in_passive_mode
        # Drop everything! Main priority is either getting rid of high scoring cards, or preventing the next player
        # from finishing.
        is_in_panic_mode = 1 in current_observation.cards_left

        # Score each card action, then put similarly scoring cards in the same score bin
        binned_cards = {}
        # TODO: Refactor the following section to not be terribly confusing and bad.
        for idx, card_action in enumerate(play_card_actions):
            card = card_action.card
            color_priority_rating = color_priority_ratings[card.color]
            card_score = card.sign.score

            if card.is_number:
                card_score = zero_value if card.sign is Sign.ZERO else card.sign.score
                # De-prioritize playing numbers that are more likely for the next player to have
                card_score *= (1 - sign_probabilities[card.sign])
            else:
                match card.sign:
                    case Sign.DRAW_FOUR | Sign.DRAW_TWO:
                        if card.sign == Sign.DRAW_FOUR:
                            is_allowed_to_play_draw_four = \
                                self.calc_can_legally_play_draw_four(current_observation, hand_color_histogram)
                            if not is_allowed_to_play_draw_four:
                                should_bluff = False  # TODO: Bluff when we're losing anyway to see if we can catch up
                                if not should_bluff:
                                    card_score *= 0
                        if not is_in_aggressive_mode:
                            # Modify desire to play draw cards even further when not in aggressive mode
                            card_score *= desire_to_play_draw_cards_in_passive_mode
                        if is_in_panic_mode:
                            card_score *= 10
                    case Sign.SKIP:
                        # TODO: Could potentially take into account if
                        #  the player after the next has only one card too, but might be overkill
                        if next_agent_remaining_cards == 1:
                            card_score *= 5
                    case Sign.REVERSE:
                        prev_player_had_to_draw = self.agent_unplayable_hand[prev_agent_index]
                        if prev_player_had_to_draw:
                            card_score *= 100
                        if next_agent_remaining_cards == 1:
                            card_score *= 5
                        if prev_agent_remaining_cards == 1:
                            card_score *= 0.1
                    case Sign.CHANGE_COLOR:
                        if is_in_panic_mode:
                            card_score *= 5

                card_score *= desire_to_do_action_modifier

            card_score *= color_priority_rating
            # Move decimal place for score a bit to make it easier to bin with integers.
            card_score *= 100
            card_scores[idx] = card_score
            card_bin_key = int(card_score / bin_size)
            card_bin = binned_cards.get(card_bin_key) or []
            card_bin.append(card_action)
            binned_cards[card_bin_key] = card_bin

        sorted_scores = sorted(binned_cards.keys(), reverse=True)
        best_bin = binned_cards[sorted_scores[0]]

        return best_bin

    def update_from_observations(self, observations):
        if self.prev_observation is not None:
            index = observations.index(self.prev_observation)
            new_observations_since_last_turn = observations[index:]
        else:
            new_observations_since_last_turn = observations

        # TODO: Take into account that we get information from when players have to
        #  draw their previous round.
        for observation in new_observations_since_last_turn:
            self.played_cards_color_histogram = self.calc_color_histogram(self.discard_pile)
            self.played_cards_sign_histogram = self.calc_sign_histogram(self.discard_pile)

            did_reshuffle = observation.draw_pile_size > self.prev_observation.draw_pile_size \
                if self.prev_observation is not None else False
            if did_reshuffle:
                self.handle_deck_has_been_reshuffled()

            if len(self.discard_pile) < observation.discard_pile_size:
                self.discard_pile.append(observation.top_card)

            if self.prev_observation is not None:
                prev_agent_index = self.get_prev_agent_idx(observation)
                prev_agent_cards_delta = observation.cards_left[prev_agent_index] - self.prev_observation.cards_left[
                    prev_agent_index]

                this_agent_cards_delta = \
                    observation.cards_left[observation.current_agent_idx] - \
                    self.prev_observation.cards_left[observation.current_agent_idx]

                self.agent_card_delta_last_play[observation.current_agent_idx] = this_agent_cards_delta
                prev_agent_delta = self.agent_card_delta_last_play.get(prev_agent_index) or 0
                prev_agent_did_draw_card_because_hand_was_unplayable = \
                    prev_agent_cards_delta == 0 and prev_agent_delta == 1

                self.update_hand_probabilities(observation, prev_agent_did_draw_card_because_hand_was_unplayable)

            self.prev_observation = observation
            # if len(self.discard_pile) != observation.discard_pile_size:
            #     print("Out o sync. No idea why")

    def calc_remaining_cards(self, current_observation: Observation):
        cards_in_player_hands = sum(current_observation.cards_left)
        total_cards_in_play_count = cards_in_player_hands + len(self.discard_pile)

        return UNO_CARD_COUNT - total_cards_in_play_count

    def prepare_for_new_round(self, current_observation):
        # We must assume that the observation used here is a fresh hand for the current agent
        self.reset_round()
        self.update_hand_probabilities(current_observation, False)

    @staticmethod
    def calc_color_histogram(cards: list[Card]):
        color_count = deepcopy(EMPTY_COLOR_HISTOGRAM)
        for card in cards:
            color_count[card.color] = color_count[card.color] + 1

        return color_count

    @staticmethod
    def calc_sign_histogram(cards: list[Card]):
        sign_count = deepcopy(EMPTY_SIGN_HISTOGRAM)
        for card in cards:
            sign_count[card.sign] = sign_count[card.sign] + 1

        return sign_count

    def update_hand_probabilities(self,
                                  observation: Observation,
                                  prev_agent_did_draw_card_because_hand_was_unplayable: bool):
        known_cards = self.discard_pile + observation.hand.cards
        # TODO: Probably should keep track of revealed hand data over time,
        #  but this micro-optimization doesn't have priority right now.
        if observation.revealed_hand is not None:
            known_cards += observation.revealed_hand.cards

        agent_hand_sizes = observation.cards_left
        for idx, hand_size in enumerate(agent_hand_sizes):
            if idx != observation.agent_idx:
                new_agent_color_probabilities, new_agent_sign_probabilities = self.calc_opponent_hand_probabilities(
                    known_cards, hand_size)
                self.agent_hand_color_probabilities[idx] = \
                    self.avg_probabilities(new_agent_color_probabilities,
                                           self.agent_hand_color_probabilities.get(idx))
                self.agent_hand_sign_probabilities[idx] = \
                    self.avg_probabilities(new_agent_sign_probabilities,
                                           self.agent_hand_sign_probabilities.get(idx))

        prev_agent_idx = self.get_prev_agent_idx(observation)
        self.agent_unplayable_hand[prev_agent_idx] = prev_agent_did_draw_card_because_hand_was_unplayable
        # If we saw that the previous player had to draw a card then we know they're out.
        if prev_agent_did_draw_card_because_hand_was_unplayable:
            top_color = observation.top_card.color
            if top_color is not None:
                probs_for_prev_agent = self.agent_hand_color_probabilities[prev_agent_idx]
                probs_for_prev_agent[top_color] = None

            # If a card is not stackable with itself, you can't rule out the fact that the player
            # has the card or not if they don't play the card. Example: You can't stack draw cards or +4,
            # so you can't rule out that the player has one of those
            # cards if the previously played card was one of those.
            top_sign = observation.top_card.sign
            is_card_stackable_with_self = observation.top_card.stacks_on(observation.top_card)
            if is_card_stackable_with_self:
                probs_for_prev_agent = self.agent_hand_sign_probabilities[prev_agent_idx]
                probs_for_prev_agent[top_sign] = None

    @staticmethod
    def avg_probabilities(a: dict[str, float], b: dict[str, float]):
        avg = {}
        if b is None:
            return a
        # We assume that both dictionaries have the same keys
        for key in a.keys():
            vals = []
            prob_a = a.get(key)
            if prob_a is not None:
                vals.append(prob_a)
            prob_b = b.get(key)
            if prob_b is not None:
                vals.append(prob_b)

            avg[key] = sum(vals) / max(1, len(vals))

        return avg

    @staticmethod
    def calc_opponent_hand_probabilities(known_cards: list[Card], cards_in_hand_count: int):
        # TODO: Take into account cards from enemy players
        #  we actually know and leave them out of the probability equation
        unknown_cards_count = UNO_CARD_COUNT - len(known_cards)
        color_hist = AIDreasAgent.calc_color_histogram(known_cards)
        sign_hist = AIDreasAgent.calc_sign_histogram(known_cards)
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

    def calc_should_challenge_draw_four(self, current_observation, next_agent_index, prev_agent_index, color_hist):
        color_probabilities = self.agent_hand_color_probabilities[prev_agent_index]
        prob_that_prev_agent_has_matching_color = color_probabilities[current_observation.top_card.color]
        should_challenge = prob_that_prev_agent_has_matching_color > 0.95
        return should_challenge

    @staticmethod
    def get_next_agent_idx(observation):
        return (observation.current_agent_idx + observation.direction) % len(
            observation.cards_left)

    @staticmethod
    def get_prev_agent_idx(observation):
        return (observation.current_agent_idx - observation.direction) % len(
            observation.cards_left)

    def calc_color_priority_rating(self, observation, is_in_low_card_mode, hand_color_histogram):
        cards_remaining = len(observation.hand)

        # When we're down to 3 cards, we try to make sure we have two cards of the same color
        get_rid_of_single_colors = is_in_low_card_mode

        priorities_based_on_own_cards = {}
        has_single_card_of_color = 1 in hand_color_histogram.values()
        for color in hand_color_histogram.keys():
            cards_in_color_count = hand_color_histogram[color]
            priority = cards_in_color_count / cards_remaining
            # If we at least have one color with just 1 card left, and we're in "low cards mode"
            # we just give priority 0 to all other colors so that they are not even considered.
            if get_rid_of_single_colors and has_single_card_of_color:
                priority = 1 if cards_in_color_count == 1 else 0

            priorities_based_on_own_cards[color] = priority

        priorities_after_modified_by_probabilities = {}
        next_agent_idx = self.get_next_agent_idx(observation)
        color_probabilities_for_next_agent = self.agent_hand_color_probabilities[next_agent_idx]
        # Prioritize colors that the next player are likely to be low on
        for color in priorities_based_on_own_cards.keys():
            priorities_after_modified_by_probabilities[color] = priorities_based_on_own_cards[color] * (
                    1 - color_probabilities_for_next_agent[color])

        return priorities_after_modified_by_probabilities

    def reset_round(self):
        self.remaining_cards_in_deck = None
        self.prev_observation = None
        self.discard_pile = []
        self.played_cards_color_histogram = deepcopy(EMPTY_COLOR_HISTOGRAM)
        self.played_cards_sign_histogram = deepcopy(EMPTY_SIGN_HISTOGRAM)
        self.agent_hand_color_probabilities = {}
        self.agent_hand_sign_probabilities = {}
        self.agent_card_delta_last_play = {}
        self.agent_unplayable_hand = {}

    def handle_deck_has_been_reshuffled(self):
        self.discard_pile.clear()

    @staticmethod
    def calc_can_legally_play_draw_four(current_observation, hand_color_histogram):
        has_cards_in_same_color_as_top_card = hand_color_histogram[current_observation.top_card.color]
        return has_cards_in_same_color_as_top_card == 0
