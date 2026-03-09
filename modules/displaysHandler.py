import nextcord
from nextcord import Embed, Colour, Interaction
from nextcord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageOps
from modules import shared, fileHandler

resFactor : int = 1 # higher number = sharper images
gridColors = {
    "NOT": (58, 58, 60),
    "YES": (83, 141, 78),
    "MAYBE": (181, 159, 59)
}

# Decide what colors to show for each letter in a guess
# Purpose is to limit number of greens and yellows to the actual number of occurances in the word
def getGridColorsAgainstAnswer(guess : str, answer : str):
    count = {}
    for l in answer:
        if l not in count.keys():
            count[l] = 1
        else:
            count[l] += 1

    res = []
    for i in range(5):
        l = guess[i]
        if l not in count.keys():
            res.append(gridColors["NOT"])
            continue
        if guess[i] == answer[i]:
            res.append(gridColors["YES"])
        elif count[l] <= 0:
            res.append(gridColors["NOT"])
            count[l] -= 1
        else:
            res.append(gridColors["MAYBE"])
            count[l] -= 1
    
    return res

# Creates image to show wordle result based on guesses
def getResultDisplayImage(guesses, answer, masked=False):
    imageResMulti = resFactor*100
    gridSpacing = 4*resFactor
    resultsImage = Image.new('RGB', (5*imageResMulti, 6*imageResMulti), color=(18, 18, 19))
    draw = ImageDraw.Draw(resultsImage)

    # grid for guesses
    for i in range(len(guesses)):
        guess = guesses[i]
        colors = getGridColorsAgainstAnswer(guess, answer)
        for j in range(5):
            bgcolor = colors[j] or (18, 18, 19)

            corner1 = ((j*imageResMulti) + gridSpacing, (i*imageResMulti) + gridSpacing) # leaves a border around the rectangle
            corner2 = (((j+1)*imageResMulti) - gridSpacing, ((i+1)*imageResMulti) - gridSpacing) #
            draw.rectangle(corner1+corner2, fill=bgcolor)

            # add letter onto grid
            letter = guesses[i][j]
            font=ImageFont.truetype(f"{shared.path_to_bot}/files/Helvetica-Bold.ttf", 45*resFactor)
            
            _,_,w,h = draw.textbbox((0,0), letter, font=font)
            # position letter in the middle of the grid box
            xpos = ((j*imageResMulti + (j+1)*imageResMulti)/2) - (w/2)
            ypos = (((i*imageResMulti) + (i+1)*imageResMulti)/2) - (h/2)

            # hide actual letters and only show color or show full?
            if not masked: draw.text((xpos, ypos), letter, font=font,  fill=(255, 255, 255))
    
    # grid for empty guess lines
    for i in range(len(guesses),6):
        for j in range(5):
            corner1 = ((j*imageResMulti) + gridSpacing, (i*imageResMulti) + gridSpacing) # leaves a border around the rectangle
            corner2 = (((j+1)*imageResMulti) - gridSpacing, ((i+1)*imageResMulti) - gridSpacing) #
            draw.rectangle(corner1+corner2, outline=(58, 58, 60), width=4*resFactor)
    
    return resultsImage

def constructMask(size : tuple[int,int]):
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask) 
    draw.ellipse((0, 0) + size, fill=255)

    return mask

async def getPlayerAvatarImage(user : nextcord.User):
    imageResMulti = resFactor*100
    avatarImage = Image.new('RGB', (imageResMulti*5, imageResMulti*3), color=(18,18,19))
    avatarPath = f"{shared.path_to_bot}/temp/images/{user.id}-avatar.png"

    await user.display_avatar.with_format("png").save(avatarPath)
    savedAvatar = Image.open(avatarPath).resize((256, 256))
    
    # apply circular border mask
    mask = Image.open(f"{shared.path_to_bot}/files/avatar-mask.png").resize((256,256)).convert('L')
    output = ImageOps.fit(savedAvatar, mask.size, centering=(0.5, 0.5))
    output.putalpha(mask)
    output.save(avatarPath)

    # paste with mask and return
    maskedAvatar = Image.open(avatarPath)
    avatarImage.paste(maskedAvatar, ((avatarImage.width - maskedAvatar.width)//2,(avatarImage.height - maskedAvatar.height)//2), maskedAvatar)
    return avatarImage

async def getCombinedResultDisplayImage(bot : commands.Bot, masked=True):
    currentGameData = fileHandler.getGameData()
    # get everyones result images
    playerResultImageData = []
    gameData = fileHandler.getLastGameData()
    for p,data in gameData.items():
        if data['id'] != currentGameData['gameId']: continue
        playerResult = getResultDisplayImage(data['guesses'], data['answer'], masked=masked)
        playerResultImageData.append([bot.get_user(int(p)),playerResult])

    players = len(playerResultImageData)
    if players == 0: return None # no data to show
    
    imageResMulti = resFactor*100
    resultsImage = Image.new('RGB', (int( (imageResMulti*players*5) + (players+1)*1*imageResMulti + imageResMulti*2 ), int( imageResMulti*11 )), color=(18, 18, 19)) # accounts for extra space needed for padding and player images

    resultYPos = int(4.5*imageResMulti)
    avatarYPos = int(1.5*imageResMulti)
    for i in range(players):
        playerResult = playerResultImageData[i][1]
        user = playerResultImageData[i][0]
        avatarImage = await getPlayerAvatarImage(user)

        xpos = 1*imageResMulti + int(1*(i+1)*imageResMulti)+(i*500) # account for padding around results
        # paste full player info
        resultsImage.paste(avatarImage, (xpos, avatarYPos))
        resultsImage.paste(playerResult, (xpos, resultYPos))
    
    # adding title text
    currentGameData = fileHandler.getGameData()
    font=ImageFont.truetype(f"{shared.path_to_bot}/files/Helvetica.ttf", 50*resFactor)
    draw = ImageDraw.Draw(resultsImage)
    titleText = f"{shared.name} #{currentGameData["gameId"]}"

    _,_,w,h = draw.textbbox((0,0), titleText, font=font)
    xpos = (resultsImage.width/2) - (w/2)
    ypos = int((1.25*imageResMulti)/2) - (h/2)
    # draw title
    draw.text((xpos, ypos), titleText, font=font,  fill=(255, 255, 255))

    # done
    return resultsImage

# Creates full personalized result embed for current or past wordle
def createResultsEmbed(interaction : Interaction, guesses, completed, won, pastGame=False, answer=None, gameId=None):
    currentGameData = fileHandler.getGameData()
    gameDisplayName = f"{shared.name} #{gameId} (CURRENT LIVE GAME)"
    if not answer:
        answer = currentGameData["answer"]
    if gameId != currentGameData["gameId"]:
        gameDisplayName = f"{shared.name} #{gameId} (PAST GAME)"

    title = "Last Played Game" if pastGame else ("Currently Playing" if not completed else ("You Won!" if won else "You Lost!"))
    description = "" if pastGame else ("Use /guess to make a guess" if not completed else (f"You correctly guessed **{answer}**" if won else f"The word was **{answer}**"))
    # a completed past game
    if pastGame and completed:
        description += "VERDICT: **"+("WINNER" if won else "LOSER")+"**"
        description += f"\n\nThe correct word was **{answer}**"
    # incomplete past game but it is the current one
    elif pastGame and not completed and gameId == currentGameData["gameId"]:
        description = "Your game is incomplete! Use /guess"

    color = Colour.light_grey() if not completed else (Colour.green() if won else Colour.red())

    # initialize
    embed = Embed(title=title, description=description, color=color)
    embed.set_footer(text=gameDisplayName)

    if (len(guesses) > 0):
        resultsImage = getResultDisplayImage(guesses, answer)
        resultsImage.save(f"{shared.path_to_bot}/temp/images/{interaction.user.id}.png")
        embed.set_image(url=f"attachment://{interaction.user.id}.png")

    # done
    return embed

# Create a leaderboard embed, personalized or non-personalized
def getLeaderboardEmbeds(bot : commands.Bot, userId=None, n=None):
    embed1 = Embed(title=f"{shared.name} Leaderboard", color=Colour.gold())

    players : dict = fileHandler.getAllPlayerStats()
    formattedData = []
    for p,data in players.items():
        formattedData.append([(data['wins']/data['gamesPlayed'])*100, data['gamesPlayed'], int(p)]) # add in this order to help sort top users
    
    formattedData.sort(reverse=True) # sort by win rate then by games played
    if not n: n = len(formattedData) # to show top n
    n = min(len(formattedData), n) # make sure n is within bounds
    for i in range(n):
        data = formattedData[i]
        user = bot.get_user(data[2])
        embed1.add_field(name=f"***#{i+1}***: {user.display_name}", value=f"{data[0]:.1f}% WR ***|*** {data[1]} Played", inline=False)
    
    if len(formattedData) == 0:
        embed1.add_field(name="No data available", value="", inline=False)
    embed1.add_field(name="", value="\n", inline=False)

    embed1.set_footer(text=f"{shared.name} | y'all are really bad at this huh")
    if not userId: return (embed1)

    embed2 = Embed(title=f"Your stats", color=Colour.gold())
    user = bot.get_user(userId)
    if str(userId) not in players.keys():
        embed2.add_field(name="No stats available.", value="", inline=False)
    else:
        data = players[str(userId)]
        embed2.add_field(name=f"{(data['wins']/data['gamesPlayed'])*100:.1f}% WR ***|*** {data['gamesPlayed']} Played", value="", inline=False)
    
    return (embed1, embed2)