# Wha?-rdle
Basically a wordle clone but in a discord bot, called Wha?-rdle

Not the best, not the worst, but it works

<b>Requires prior knowledge of discord bots to operate</b>

## How to use:
Go to `shared.py` and change fields as necessary
Create a `.env` file in the bot directory with the following format
```env
TOKEN = "mytoken"
ADMIN_USER_IDS = "1234, 5678, 10000111" # all ids must be seperated by commmas
```
Add the bot to your server, and run `main.py`

<b>(Bot requires message content and members intents)</b>

## Commands:
- /play : start playing the current active game
- /guess : make a guess in the current active game
- /new : starts a new game for everyone (user must be admin)
- /show or /view : view your progress in the last game that you played
- /showall : view everyones progress in the current active game
- /stats : view everyones game stats

## Note:

NOT meant to be used on a large scale without modifications, this is just a very simple bot i put together in 2 days so me and my friends could play wordle on our discord server, its not made for larger groups and definitely not made for use in multiple guilds at the same time!