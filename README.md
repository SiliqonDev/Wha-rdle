# Wha?-rdle
Basically a wordle clone but in a discord bot, called Wha?-rdle

Not the best, not the worst, but it works
Requires prior knowledge of discord bots to operate

## How to use:
Go to `shared.py` and fill out any empty fields
Create a `.env` file in the bot directory and put your token in it like `TOKEN="my token"`
Add the bot to your server, and run `main.py`
- Requires message content and members intent

### Commands:
- /play : start playing the current available game of wordle
- /guess : make a guess in your current game of wordle
- /new : starts a new game of wordle for everyone (user must be in ADMIN_IDS)
- /show or /view : view your progress in the last game that you played
- /showall : view everyones progress in the current active wordle
- /stats : view everyones game stats

## Note:

NOT meant to be used on a large scale without modifications, this is just a very simple bot i put together in 2 days so me and my friends could play wordle on our discord server, its not made for larger groups and definitely not made for use in multiple guilds at the same time!