import random, string
from nextcord.ext import commands
from nextcord import Interaction, Embed, Colour, File, TextChannel
from modules import fileHandler, shared, displaysHandler
from PIL import Image

fileHandler.initDataFile()

# intialize cache
allowed_guesses, possible_answers = fileHandler.getWordList()
currentGameData = fileHandler.getGameData()

# message to update live with current game stats
currentGameStatusMessageId = None
currentGameStatusChannelId = None

def createNewGame():
    global currentGameStatusChannelId, currentGameStatusMessageId, currentGameData

    newId = max(0, currentGameData["gameId"] + 1)
    answer : str = random.choice(possible_answers)
    answer = answer.upper()
    
    currentGameData["gameId"] = newId
    currentGameData["answer"] = answer
    
    fileHandler.setGameData(currentGameData)
    currentGameStatusMessageId = None
    currentGameStatusChannelId = None

    print(f"New game started: #{newId}")

async def createCurrentGameStatusMessage(bot : commands.Bot):
    gameData = fileHandler.getLastGameData()
    playing = []
    # get names of all people who have played current game
    for p,data in gameData.items():
        if data['id'] != currentGameData['gameId']: continue
        playing.append(bot.get_user(int(p)).display_name)
    text = playing[0] + (f" and {len(playing)-1} other"+ ("s" if len(playing) > 2 else "") + " were playing..." if len(playing) > 1 else " was playing...")
    # grab same image as everywhere else
    image : Image = await displaysHandler.getCombinedResultDisplayImage(bot)
    image.save(f"{shared.path_to_bot}/temp/images/combined-result-gameStatus.png")

    file = File(f"{shared.path_to_bot}/temp/images/combined-result-gameStatus.png", filename="combined-result-gameStatus.png")
    return text, file

async def sendOrUpdateGameStatusMessage(bot : commands.Bot, interaction : Interaction):
    global currentGameStatusChannelId, currentGameStatusMessageId
    if not currentGameStatusMessageId:
        # new message
        message, file = await createCurrentGameStatusMessage(bot)
        statusMessage = await interaction.channel.send(content=message, file=file)
        currentGameStatusMessageId = statusMessage.id
        currentGameStatusChannelId = interaction.channel.id
    else:
        # replace existing
        channel = bot.get_channel(currentGameStatusChannelId)
        message = channel.get_partial_message(currentGameStatusMessageId)
        try:
            await message.delete()
        except:
            a = 1+1 # do nothing

        message, file = await createCurrentGameStatusMessage(bot)
        statusMessage = await interaction.channel.send(content=message, file=file)
        currentGameStatusMessageId = statusMessage.id

# reusable game instance template
class GameInstance():
    def __init__(self, bot : commands.Bot, interaction : Interaction, silentStart=False):
        self.interaction = interaction
        self.userId = interaction.user.id
        self.completed = False
        self.won = False
        self.silentStart = silentStart
        self.bot = bot
        
    async def updatePlayerData(self):
        fileHandler.setLastGameDataFor(self.userId, {
            "id":self.gameId,
            "guesses": self.guesses,
            "completed": self.completed,
            "won": self.won,
            "answer": self.answer,
        })

        if self.completed:
            fileHandler.incrementPlayerStats(self.userId, {
                "gamesPlayed": 1,
                "wins": 1 if self.won else 0,
            })

    async def initGame(self):
        # init data
        self.gameId = currentGameData["gameId"]
        self.answer = currentGameData["answer"]

        # if continuing last game which is the same as this one, account for past guesses
        pdata = fileHandler.getLastGameDataOf(self.userId)
        if (pdata["id"] == self.gameId) and ("completed" in pdata.keys()) and (not pdata["completed"]):
            self.guesses = pdata["guesses"]
        else:
            self.guesses = []
        
        # begin cycle
        if not self.silentStart: await self.gameLoop()
    
    async def gameLoop(self):
        await self.updatePlayerData() # save current game state
        await sendOrUpdateGameStatusMessage(self.bot, self.interaction) # update live message

        # construct embed and send
        embed = displaysHandler.createResultsEmbed(self.interaction, self.guesses, self.completed, self.won, gameId=self.gameId)

        if len(self.guesses) > 0:
            await self.interaction.send(embed=embed, file=File(f"{shared.path_to_bot}/temp/images/{self.userId}.png", filename=f"{self.userId}.png"), ephemeral=True)
        else:
            await self.interaction.send(embed=embed, ephemeral=True)

    async def gameLost(self):
        self.completed = True
        self.won = False
        await self.updatePlayerData() # save final game state
        await sendOrUpdateGameStatusMessage(self.bot, self.interaction) # update live message

        # construct embed and send
        embed = displaysHandler.createResultsEmbed(self.interaction, self.guesses, self.completed, self.won, gameId=self.gameId)
        await self.interaction.send(embed=embed, file=File(f"{shared.path_to_bot}/temp/images/{self.userId}.png", filename=f"{self.userId}.png"), ephemeral=True, delete_after=30)

    async def gameWon(self):
        self.completed = True
        self.won = True
        await self.updatePlayerData() # save final game state
        await sendOrUpdateGameStatusMessage(self.bot, self.interaction) # update live message

        # construct embed and send
        embed = displaysHandler.createResultsEmbed(self.interaction, self.guesses, self.completed, self.won, gameId=self.gameId)
        await self.interaction.send(embed=embed, file=File(f"{shared.path_to_bot}/temp/images/{self.userId}.png", filename=f"{self.userId}.png"), ephemeral=True, delete_after=30)

    async def validateGuess(self, curInteraction : Interaction, guess : str):
        guess = guess.upper()

        # valid guess?
        if len(guess) != 5:
            await curInteraction.response.send_message("Your guess must contain 5 letters!", ephemeral=True, delete_after=10)
            return
        for ch in guess:
            if ch not in string.ascii_uppercase:
                await curInteraction.response.send_message("Your guess must contain alphabets!", ephemeral=True, delete_after=10)
                return
        
        # check against allowed guesses
        if guess.lower() not in allowed_guesses:
            await curInteraction.response.send_message(f"**{guess}** is not a valid word!", ephemeral=True, delete_after=10)
            return
        
        # already guessed this word?
        if guess in self.guesses:
            await curInteraction.response.send_message(f"You have already used **{guess}**!", ephemeral=True, delete_after=10)
            return
        
        ### GUESS IS VALID
        self.guesses.append(guess)
        
        # check win
        if guess == self.answer:
            print(f"{curInteraction.user} guessed the word correctly.")
            await curInteraction.send("You guessed the word correctly!", ephemeral=True, delete_after=5)
            await self.gameWon()
            return
        
        # out of guesses?
        if len(self.guesses) >= 6:
            await curInteraction.send("You are out of guesses!", ephemeral=True, delete_after=5)
            await self.gameLost()
            return
        
        # keep playing
        await curInteraction.send(f"You guessed {guess}.", ephemeral=True, delete_after=5)
        await self.gameLoop()
    
    async def terminate(self, reason="Unknown"):
        self.won = False
        self.completed = True
        await self.updatePlayerData() # save final game state

        embed = Embed(title="Oops!", color=Colour.red())
        embed.set_footer(text=f"{shared.name} #{currentGameData["gameId"]}")
        embed.add_field(name="Game Terminated", value=f"This game has been **terminated!**\nReason: {reason}")
        
        await self.interaction.send(embed=embed, ephemeral=True, delete_after=30)

async def endCurrentGame(bot : commands.Bot, interaction : Interaction, startNew=True, announce=True):
    channel = bot.get_channel(shared.alerts_channel_id)
    if interaction != None and interaction.channel != None:
        channel = interaction.channel
    elif channel == None or not isinstance(channel, TextChannel):
        print("Alerts channel not found! Invalid ID!")
        announce = False

    # get last game results
    resultsImage = await displaysHandler.getCombinedResultDisplayImage(bot)
    # init new game
    if startNew: createNewGame()

    embed = Embed(title="GAME ENDED!", description=f"The current game of {shared.name} has ended!\n", color=Colour.red())
    embed.set_footer(text=f"{shared.name} #{currentGameData["gameId"]-1}")

    if not resultsImage: # no past results to show
        embed.add_field(name="No available results.", value="", inline=False)
        if startNew:
            embed.add_field(name="",value="*A new game has been started*", inline=False)
        if announce: await channel.send(embed=embed)
        if interaction: await interaction.send("Command executed.", ephemeral=True, delete_after=5)
        return
    resultsImage.save(f"{shared.path_to_bot}/temp/images/combined-result-new.png")
    
    if not announce: return
    # create server alert for new game and stats for last game
    lines = "\n"
    gameData = fileHandler.getLastGameData()
    for p,data in gameData.items():
        if data['id'] != currentGameData['gameId']-1: continue
        text = f"<@{p}>: " + ("Won" if data['won'] else "Lost") + f" in {len(data['guesses'])} moves.\n"
        lines += text
    lines+="\n"
    embed.add_field(name="Game Results", value=lines,inline=False)

    if startNew:
        embed.add_field(name="",value="*A new game has been started*", inline=False)
    
    # send alert
    if interaction: await interaction.send("Command executed.", ephemeral=True, delete_after=5)
    await channel.send(embed=embed, file=File(f"{shared.path_to_bot}/temp/images/combined-result-new.png", "combined-results.png"))

    
