# Artificial-UNO

An UNO-game for AIs.

## Competition

For Knowit Objectnet's internal seminar in Rome. The goal of the competition is to create a program that beats the programs of the other participants in UNO.

### Rules

Uses the standard UNO-rules, see https://en.wikipedia.org/wiki/Uno_(card_game). A few details about the official rules that might be surprising to the average UNO-player:

- The aim of the game is to be the first player to score 500 points.
- Points are achieved by being the first to play all of one's own cards. Points are rewarded based on the cards held by the other players. Number cards count their face value, all action cards count 20, and Wild and Wild Draw Four cards count 50
- the amount of cards still held by the other players.
- "Progressive/Stacking UNO" (see https://en.wikipedia.org/wiki/Uno_(card_game)#House_rules) is not a part of standard UNO.
- A player may play a Wild Draw Four card only if that player has no cards matching the current color. It is however allowed to lie and play it anyway, but the next player may choose to challenge its use. The player who played the Wild Draw Four must privately show their hand to the challenging player in order to demonstrate that they had no prior matching colored cards. If the challenge is successful, then the challenged player must draw four cards instead and play continues with the challenger. Otherwise, the challenger must draw six cards – the four cards they were already required to draw plus two more cards – and lose their turn.

### How to participate

Create a pull request which adds your agent to the `agent`-folder before 19th of October 23:59.

## Setup

`artificial-uno` uses Python 3.10 features, you therefore need to run it with Python 3.10 or greater.

I also recommend setting up a virtual environment for this project (see [venv](https://docs.python.org/3/library/venv.html)).

After setting up your virtual environment with the correct Python version, install the projects dependencies by running

`pip install -r requirements.txt`

### Test setup

Try running

`python unoenv.py`

from your virtual environment. This should start a game with one player-controlled agent and two agents who make random moves. See their implementation in `agents/textagent.py` and `agents/randomagent.py`.

## Creating your own agent

To create your own agent you need to create a class that extends the `UnoAgent` class (see `agents/unoagent.py`) and implements UnoAgent::get_action. Check out `agents/textagent.py` and `agents/randomagent.py` for examples.

### Testing your agent

Create an instance of your custom agent class and pass it into an `UnoEnvironment`. See the example in the main function of `unoenv.py`.

## GUI

A GUI made with Svelte and Flask can be found inside the `gui`-folder. It can be used to visualize an UNO-game. To start the backend you first have to run

`flask --app gui.unoserver run`

from the root-folder of the project. After this, open a new terminal and run

```
cd gui
npm install
npm run dev
```

and head to http://localhost:5173. This will by default start a simulation of an UNO-game with 10 agents doing random actions every time you refresh thr browser window. To change the competing agents you have to change the agents inside the `listen`-function inside `gui/unoserver.py` and restart the server.
