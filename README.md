# Wha?-rdle [DEV BRANCH]
Basically a wordle clone but in a discord bot, called Wha?-rdle</br>
Not the best, not the worst, but it works</br>
<b>Requires prior knowledge of discord bots and bot hosting to operate</b>

## How to use:
1. Refer to the `config.json.example` and create a `config.json` for the bot

2. Refer to the `lang.json.example` and create a `lang.json` for the bot

3. Refer to the `.env.example` and create a `.env` for the bot

4. Refer to `requirements.txt` and download all the required packages

5. Add the bot to your server, and run `main.py`

<b>(Bot requires message content and members intent)</b>

## Commands:

- /new : starts a new game for everyone
- /play : start playing the current active game
- /guess : make a guess in the current active game
- /peek : peek at your current game progress
- /leaderboard : view a leaderboard of all user's stats
- /stats : view your own stats
- /help : command to view all commands

## Note:

<b>NOT meant to be used on a large scale without modifications</b><br>
This is not currently meant to be used in multiple guilds at the same time!

## IDEAS FOR LATER

- Switch out the game end embed for an image instead, more like the actual wordle discord application
- Add an alerts channel for logging and stuff
- Bias against rolling recent past words