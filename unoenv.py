from agents.ai_dreas_agent import AIDreasAgent
from agents.unoagent import UnoAgent
from unogame import UnoGame
from unotypes import *
from textutils import print_gamestate


class UnoEnvironment:
    def __init__(self, agents, winning_score=500):
        self.agents: list[UnoAgent] = agents
        self.aliases = [agent.alias for agent in self.agents]
        self.observations: list[list[Observation]] = [[] for _ in range(len(agents))]
        self.uno_game = UnoGame(len(agents), winning_score=winning_score)

    def agent_iter(self):
        while not self.uno_game.game_won:
            agent_idx = self.uno_game.current_agent_idx
            yield agent_idx, self.agents[agent_idx]

    def __iter__(self):
        yield self.uno_game.gamestate()
        for agent_idx, agent in self.agent_iter():
            for i in range(len(self.agents)):
                observation = self.uno_game.last_observation(i)
                if observation.is_initial_state:
                    self.observations[i] = [observation]
                else:
                    self.observations[i].append(observation)

            observations = self.observations[agent_idx]
            action = agent.get_action(observations, aliases=self.aliases)

            try:
                self.step(agent_idx, action)
            except Exception as e:
                print(e)
                print("Invalid action:", action)
                action = observations[-1].action_space().intersection([DrawCard(), SkipTurn(), AcceptDrawFour()]).pop()
                self.step(agent_idx, action)
            yield self.uno_game.gamestate()

    def step(self, agent_idx: int, action: Action):
        self.uno_game.step(agent_idx, action)

    def print_state(self):
        print_gamestate(self.uno_game.state_log[-1], self.aliases)

    def print_winner(self):
        if self.uno_game.game_won:
            winner_idx = next(i for (i, score) in
                              enumerate(self.uno_game.scores)
                              if score >= self.uno_game.winning_score)
            winner_alias = self.aliases[winner_idx]
            print(f"THE WINNER IS {winner_alias}!!!!")
        else:
            print("No winner yet")


def main():
    from agents.randomagent import RandomAgent
    from agents.textagent import TextAgent

    agents = [
        # TextAgent("Player"),
        RandomAgent("RandomAgent 1"),
        RandomAgent("RandomAgent 2"),
        RandomAgent("RandomAgent 3"),
        AIDreasAgent("AI-Dreas")]
    games_to_play = 50
    games_won = {}
    for idx, _ in enumerate(range(0, games_to_play)):
        env = UnoEnvironment(agents=agents, winning_score=2000)
        for i, state in enumerate(env):
            if state.game_won:
                winner_idx = next(i for (i, score) in
                                  enumerate(env.uno_game.scores)
                                  if score >= env.uno_game.winning_score)
                prev_won_games = games_won.get(winner_idx) or 0
                games_won[winner_idx] = prev_won_games + 1
                print(state.scores)
                env.print_winner()
                print("finished " + str(idx + 1) + "/" + str(games_to_play) + "games")

    print("WIN PERCENTAGES")
    for idx, agent in enumerate(agents):
        games_won_by_agent = games_won.get(idx) or 0
        win_percentage = (games_won_by_agent / games_to_play) * 100
        print(agent.alias + ":" + str(win_percentage) + "%")


if __name__ == '__main__':
    main()
