import nextcord, json, inspect, os
from os.path import isfile, join
from modules import fileHandler, gameHandler, displaysHandler
from nextcord import Interaction, File, SlashOption
from nextcord.ext import commands, tasks
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
from utils.types import BotConfig

bot = commands.Bot(command_prefix="w?", intents=nextcord.Intents.all())

# get directory that main.py is in
currentFrame = inspect.currentframe()
if currentFrame is None:
    print("CRITICAL: Could not find current working directory!")
    exit()
filename = inspect.getframeinfo(currentFrame).filename
cwd = os.path.dirname(os.path.abspath(filename)) # current working directory

# load bot config
config = None
try:
    with open(f"{cwd}/config.json") as f:
        config = BotConfig(json.load(f))
    if not config:
        raise(Exception)
except Exception as e:
    print("CRITICAL: Could not load config file!",e)
    exit()

config.set("cwd", cwd)
config.set("log_file_path", f"{cwd}/{str(datetime.now())}.log") # set seperate log file name each time

"""
## CONSTANTS
admin_ids_string = os.getenv("ADMIN_USER_IDS")
admin_ids = [] if admin_ids_string == None else [int(id) for id in admin_ids_string.strip().split(',')]
name = shared.name

# game cache
active_games = {}
autoCleanup = True

###
### BOT EVENTS
###

@tasks.loop(seconds=5.0)
async def gameCleanupLoop():
    if not autoCleanup: return
    toclean = []
    for user in active_games.keys():
        instance : gameHandler.GameInstance = active_games[user]
        if not instance or instance.completed:
            toclean.append(user)
            print(f"Cleaned up game from {user}")
    
    for user in toclean:
        del active_games[user]

@bot.event
async def on_ready():
    data = fileHandler.getGameData()
    if data['gameId'] < 0: gameHandler.createNewGame() # start new game if first time running
    gameCleanupLoop.start()
    
    print(f"Started bot as {bot.user}")

###
### COMMANDS
###

@bot.slash_command(description=f"Play a game of {name}")
async def play(interaction : Interaction):
    if interaction.user == None: return
    userId = interaction.user.id

    # leftover game from earlier?
    data = fileHandler.getLastGameDataOf(userId)
    if (userId not in active_games.keys()) and (not data["completed"]) and (data["id"] == gameHandler.currentGameData["gameId"]):
        await interaction.response.send_message("You already have an ongoing game! Use /guess", ephemeral=True, delete_after=10)
        return

    # eligibility check to start new game right now
    eligible = canUserPlayGame(userId)
    if not eligible:
        await interaction.response.send_message("You cannot start a new game right now!", ephemeral=True, delete_after=10)
        return

    await interaction.response.defer() # prevent webhook token expiration during game
    # alerts
    await interaction.send(f"Starting a game of {name}",ephemeral=True, delete_after=5)

    # make game instance and run
    instance = gameHandler.GameInstance(bot, interaction)
    await instance.initGame()
    print(f"{interaction.user} started playing")

    active_games[userId] = instance

@bot.slash_command(description=f"Make a guess in your game of {name}")
async def guess(interaction : Interaction, guess : str = SlashOption(description="Your guess", required=True)):
    if interaction.user == None: return
    userId = interaction.user.id

    # continuing a game from earlier?
    data = fileHandler.getLastGameDataOf(userId)
    if (userId not in active_games.keys()) and (not data["completed"]) and (data["id"] == gameHandler.currentGameData["gameId"]):
        # build new game instance
        await interaction.response.defer() # prevent webhook token expiration during game
        instance = gameHandler.GameInstance(bot, interaction, silentStart=True)
        await instance.initGame()
        active_games[userId] = instance

    # not continuing past game and no current game is being played
    if userId not in active_games.keys():
        await interaction.response.send_message("You do not have an ongoing game! Try using /play", ephemeral=True, delete_after=10)
        return
     
    # current game being played but is completed
    instance : gameHandler.GameInstance = active_games[userId]
    if instance.completed:
        await interaction.response.send_message("You already completed the current game!", ephemeral=True, delete_after=10)
        return
    
    # game currently running and is not completed
    await instance.validateGuess(interaction, guess)

@bot.slash_command(description="View your last game's progress.")
async def view(interaction : Interaction):
    if interaction.user == None: return
    userId = interaction.user.id

    data = fileHandler.getLastGameDataOf(userId)
    gameId = data["id"]
    if gameId < 0:
        await interaction.response.send_message("You dont have any past games!", ephemeral=True, delete_after=10)
        return

    embed = displaysHandler.createResultsEmbed(interaction, data["guesses"], data["completed"], data["won"], True, data["answer"], gameId)
    if len(data["guesses"]) > 0:
        await interaction.response.send_message(embed=embed, file=File(f"{shared.path_to_bot}/temp/images/{userId}.png", filename=f"{userId}.png"), ephemeral=True)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=True)
@bot.slash_command(description="View your last game's progress.")
async def show(interaction: Interaction):
    await view(interaction)

## create new game
@bot.slash_command(description=f"Start a new {name}")
async def new(interaction: Interaction):
    if interaction.user == None: return
    userId = interaction.user.id

    if userId not in admin_ids:
        await interaction.response.send_message("Nuh uh.", ephemeral=True, delete_after=10)
        return
    await cleanupGameData()
    await gameHandler.endCurrentGame(bot, interaction)

@bot.slash_command(description="Show everyone's progress on the current game")
async def showall(interaction: Interaction):
    resultsImage = await displaysHandler.getCombinedResultDisplayImage(bot)
    if not resultsImage: # no current results to show
        await interaction.response.send_message("There are currently no results to show!", ephemeral=True, delete_after=10)
        return

    resultsImage.save(f"{shared.path_to_bot}/temp/images/combined-result-showall.png")
    await interaction.response.send_message(file=File(f"{shared.path_to_bot}/temp/images/combined-result-showall.png", "combined-results.png"))
    return

@bot.slash_command(description="View the stats leaderboard")
async def stats(interaction: Interaction):
    embeds = displaysHandler.getLeaderboardEmbeds(bot, interaction.user.id)
    await interaction.send(embed=embeds[0])
    await interaction.send(embed=embeds[1], ephemeral=True, delete_after=60)

###
### MISC METHODS
###

async def cleanupGameData():
    global active_games, autoCleanup
    autoCleanup = False

    for user in active_games:
        instance : gameHandler.GameInstance = active_games[user]
        if not instance.completed:
            await instance.terminate(f"The current {name} has ended! A **new one** has started in its place!")
    active_games = {}
    for filename in os.listdir(f"{shared.path_to_bot}/temp/images"):
        file_path = os.path.join(f"{shared.path_to_bot}/temp/images", filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    
    autoCleanup = True

def canUserPlayGame(userId):
    # game running
    if userId in active_games.keys():
        return False
    # already played this one
    playerData = fileHandler.getLastGameDataOf(userId)
    latestGameId = fileHandler.getGameData()["gameId"]
    # some bug??
    if playerData["id"] > latestGameId:
        playerData["id"] = latestGameId
        return True
    # current game also completed
    if playerData["id"] == latestGameId and playerData["completed"]:
        return False
    # all good
    return True
"""

cogs_path = f'{cwd}/cogs'
async def load_cogs():
    for filename in os.listdir(cogs_path):
        filepath = join(cogs_path, filename)
        if not isfile(filepath): continue
        # is a file, try loading
        if filename.endswith('.py'):
            try:
                # load cog using module path
                bot.load_extension(filepath.replace('/', '.').replace('//','.'))
                print(f"Loaded cog: {filename[:-3]}")
            except Exception as e:
                print(f"Failed to load cog {filename}: {e}")

# check token and start bot
load_dotenv()
token = os.getenv("TOKEN")
if not token:
    print("TOKEN NOT FOUND OR INVALID TOKEN DETECTED")
    exit()

async def main(token):
    await load_cogs()
    await bot.start(token)

if __name__ == "__main__":
    assert token is not None
    import asyncio
    asyncio.run(main(token))