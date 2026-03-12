import nextcord, json, inspect, os
from nextcord import Activity, ActivityType, TextChannel
import atexit
from os.path import isfile, join
from typing import cast
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path
import asyncio
from cogs.services.data import DataService
from utils.types import Config, WordleBot
from utils.utils import Logger

# get directory that main.py is in
currentFrame = inspect.currentframe()
if currentFrame is None:
    print("ERROR: Could not find current working directory!")
    exit()
filename = inspect.getframeinfo(currentFrame).filename
cwd = os.path.dirname(os.path.abspath(filename)) # current working directory

# setup logging
log_file_name = f"{datetime.now()}.txt".replace(":", "-")

log_dir = Path(cwd) / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

log_file_path = log_dir / log_file_name
with open(log_file_path, "w"):
    pass

_logger = Logger("MAIN", str(log_file_path))

# load bot config
config = None
try:
    with open(f"{cwd}/config.json") as cf:
        config = Config(json.load(cf))
except Exception as e:
    _logger.error("Could not load config file!")
    _logger.exception(e)
    exit()
config.set("cwd", cwd)
config.set("log_file_path", log_file_path) 

# load bot lang
lang = None
try:
    with open(f"{cwd}/lang.json") as lf:
        lang = Config(json.load(lf))
except Exception as e:
    _logger.error("Could not load lang file!")
    _logger.exception(e)
    exit()

def load_cogs_from(dir_relative_path : str):
    """
    recursively searches for and loads every cog(.py file) from a subfolder
    """
    dir_absolute_path = join(cwd, dir_relative_path)
    for filename in os.listdir(dir_absolute_path):
        file_absolute_path = join(dir_absolute_path, filename)
        file_relative_path = join(dir_relative_path, filename)

        # load if .py
        if filename.endswith('.py'):
            load_cog(file_relative_path)
        # if folder, recursively check for cogs inside
        elif not isfile(file_absolute_path):
            load_cogs_from(file_relative_path)
        
def load_cog(relative_path : str):
        module_path = relative_path.replace('/', '.').replace('\\','.')[:-3]
        try:
            # load cog using module path
            bot.load_extension(module_path)
            _logger.info(f"Loaded cog: {module_path}", printToConsole=True)
        except Exception as e:
            _logger.error(f"Failed to load cog {module_path}")
            _logger.exception(e)

# check token and start bot
load_dotenv()
token = os.getenv("TOKEN")
if not token:
    _logger.error("BOT TOKEN NOT FOUND OR INVALID TOKEN")
    exit()

activity = Activity(name = "Playing Self", type = ActivityType.custom)
bot = WordleBot(intents=nextcord.Intents.all(), activity=activity)
bot.config = config
bot.lang = lang

async def main(token):
    load_cogs_from("cogs")
    try:
        await bot.start(token)
    except:
        print(f"Error trying to establish connection with discord: {e}")

''' TODO: figure this out
@atexit.register
async def on_close():
    data_service : DataService = cast(DataService, bot.get_cog("data_service"))
    await data_service._autosave()
'''
    
@bot.event
async def on_ready():
    await bot.wait_until_ready()
    bot.alerts_channel = cast(TextChannel, bot.get_channel(bot.config.get('alerts_channel_id')))

if __name__ == "__main__":
    assert token is not None
    asyncio.run(main(token))

"""
###
### COMMANDS
###

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
"""