import nextcord, os
from modules import fileHandler, gameHandler, shared, displaysHandler
from nextcord import Interaction, File, SlashOption
from nextcord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()
intents = nextcord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="w?", intents=intents)

## CONSTANTS
guild_ids = shared.guild_ids 
admin_ids = shared.admin_ids 
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
    
    for u in toclean:
        del active_games[u]

@bot.event
async def on_ready():
    fileHandler.initDataFile()
    data = fileHandler.getGameData()
    if data['gameId'] < 0: gameHandler.createNewGame() # start new game is none exist
    gameCleanupLoop.start()
    
    print(f"Started bot as {bot.user} (ID: {bot.user.id})")

###
### COMMANDS
###

@bot.slash_command(guild_ids=guild_ids, description=f"Play a game of {name}")
async def play(interaction : Interaction):
    # leftover game from earlier?
    data = fileHandler.getLastGameDataOf(interaction.user.id)
    if (interaction.user.id not in active_games.keys()) and (not data["completed"]) and (data["id"] == gameHandler.currentGameData["gameId"]):
        await interaction.response.send_message("You already have an ongoing game! Use /guess", ephemeral=True, delete_after=10)
        return

    # eligibility check to start new game right now
    eligible = canUserPlayGame(interaction.user.id)
    if not eligible:
        await interaction.response.send_message("You cannot start a new game right now!", ephemeral=True, delete_after=10)
        return

    # alerts
    await interaction.send(f"Starting a game of {name}",ephemeral=True, delete_after=5)

    # make game instance and run
    instance = gameHandler.GameInstance(bot, interaction)
    await instance.initGame()
    print(f"{interaction.user} started playing")

    active_games[interaction.user.id] = instance

@bot.slash_command(guild_ids=guild_ids, description=f"Make a guess in your game of {name}")
async def guess(interaction : Interaction, guess : str = SlashOption(description="Your guess", required=True)):
    # continuing a game from earlier?
    data = fileHandler.getLastGameDataOf(interaction.user.id)
    if (interaction.user.id not in active_games.keys()) and (not data["completed"]) and (data["id"] == gameHandler.currentGameData["gameId"]):
        # build new game instance
        instance = gameHandler.GameInstance(bot, interaction, silentStart=True)
        await instance.initGame()
        active_games[interaction.user.id] = instance

    # not continuing past game and no current game is being played
    if interaction.user.id not in active_games.keys():
        await interaction.response.send_message("You do not have an ongoing game! Try using /play", ephemeral=True, delete_after=10)
        return
     
    # current game being played but is completed
    instance : gameHandler.GameInstance = active_games[interaction.user.id]
    if instance.completed:
        await interaction.response.send_message("You already completed the current game!", ephemeral=True, delete_after=10)
        return
    
    # game currently running and is not completed
    await instance.validateGuess(interaction, guess)

@bot.slash_command(guild_ids=guild_ids, description="View your last game's progress.")
async def view(interaction : Interaction):
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
@bot.slash_command(guild_ids=guild_ids, description="View your last game's progress.")
async def show(interaction: Interaction):
    await view(interaction)

## create new game
@bot.slash_command(guild_ids=guild_ids, description=f"Start a new {name}")
async def new(interaction: Interaction):
    if interaction.user.id not in admin_ids:
        await interaction.response.send_message("Nuh uh.", ephemeral=True, delete_after=10)
        return
    await cleanupGameData()

    # save last game result
    resultsImage = await displaysHandler.getCombinedResultDisplayImage(bot)
    if not resultsImage: # no past results to show
        await interaction.channel.send(content="**A new game has started!**")
        return
    # show past results
    resultsImage.save(f"{shared.path_to_bot}/temp/images/combined-result-new.png")

    # create server alert for new game and stats for last game
    text = "__LAST GAME RESULTS__\n"
    currentGameData = gameHandler.currentGameData
    gameData = fileHandler.getLastGameData()
    for p,data in gameData.items():
        if data['id'] != currentGameData['gameId']: continue
        text += f"<@{p}>: " + ("Won" if data['won'] else "Lost") + f" in {len(data['guesses'])} moves.\n"
    text += "\n**A new game has started!**"

    # init new game
    gameHandler.createNewGame()
    
    # send
    await interaction.send("A new game has been started.", ephemeral=True, delete_after=5)
    await interaction.channel.send(content=text, file=File(f"{shared.path_to_bot}/temp/images/combined-result-new.png", "combined-results.png"))

@bot.slash_command(guild_ids=guild_ids, description="Show everyone's progress on the current game")
async def showall(interaction: Interaction):
    resultsImage = await displaysHandler.getCombinedResultDisplayImage(bot)
    if not resultsImage: # no current results to show
        await interaction.response.send_message("There are currently no results to show!", ephemeral=True, delete_after=10)
        return

    resultsImage.save(f"{shared.path_to_bot}/temp/images/combined-result-showall.png")
    await interaction.response.send_message(file=File(f"{shared.path_to_bot}/temp/images/combined-result-showall.png", "combined-results.png"))
    return

@bot.slash_command(guild_ids=guild_ids, description="View the stats leaderboard")
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
        return False
    # current game also completed
    if playerData["id"] == latestGameId and playerData["completed"]:
        return False
    # all good
    return True

# start the bot
token = os.getenv("TOKEN")
if not token:
    print("TOKEN NOT FOUND OR INVALID TOKEN DETECTED")
    exit()
bot.run(token)