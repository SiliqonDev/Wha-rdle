import io, traceback
from PIL import Image, ImageDraw, ImageFont, ImageOps
import aiohttp, nextcord
from utils.types import CurrentGameInfo, WordleBot
from nextcord import Embed, Interaction, Colour

def get_traceback(exception: Exception) -> str:
    return "".join(traceback.format_exception(exception.__class__, exception, exception.__traceback__))

def flatten(seq : list | tuple) -> list:
    """
    flattens a given nested sequence

    Parameters
    ----------
    seq : list | tuple
        The sequence to flatten
    
    Returns
    -------
    res : list
        The flattened sequence
    """
    res = []
    for i in seq:
        if isinstance(i, list) or isinstance(i, tuple):
            flat_i = flatten(i)
            for j in flat_i:
                res.append(j)
            continue
        res.append(i)
    
    return res

guessColors = {
    "NOT": (58, 58, 60),
    "YES": (83, 141, 78),
    "MAYBE": (181, 159, 59)
}
# Decide what colors to show for each letter in a guess
# Purpose is to limit number of greens and yellows to the actual number of occurances in the word
def getGridColorsFromGuesses(guess : str, answer : str) -> list[tuple]:
    count = {}
    for l in answer:
        if l not in count.keys():
            count[l] = 1
        else:
            count[l] += 1

    res = [guessColors["NOT"]]*5 # assume all as being "NOT"
    checked = [0]*5
    for i in range(5):
        # get the correct ones
        ltr = guess[i]
        if guess[i] == answer[i]:
            count[ltr] -= 1
            res[i] = guessColors["YES"]
            checked[i] = 1
    for i in range(5):
        # get the maybe ones
        if checked[i]: continue # its already accounted for
        ltr = guess[i]
        if ltr in count.keys() and count[ltr] > 0:
            res[i] = guessColors["MAYBE"]
            count[ltr] -= 1
    
    return res

async def getUserResultsImageBytes(bot : WordleBot, guesses : list[str], answer : str, answer_hidden : bool = False) -> bytes:
    res_factor : int = bot.image_res_factor
    gridSpacing : int = 4*res_factor
    resultsImage : Image.Image = Image.new('RGB', (5*res_factor, 6*res_factor), color=(18, 18, 19))
    draw = ImageDraw.Draw(resultsImage)

    # grid for guesses
    for i in range(len(guesses)):
        guess = guesses[i]
        colors = getGridColorsFromGuesses(guess, answer)
        for j in range(5):
            bgcolor = colors[j] or (18, 18, 19)

            corner1 = ((j*res_factor) + gridSpacing, (i*res_factor) + gridSpacing) # leaves a border around the rectangle
            corner2 = (((j+1)*res_factor) - gridSpacing, ((i+1)*res_factor) - gridSpacing) #
            draw.rectangle(corner1+corner2, fill=bgcolor)

            # add letter onto grid
            letter = guesses[i][j]
            font = ImageFont.truetype(f"{bot.config.get('cwd')}/assets/fonts/Helvetica-Bold.ttf", 0.45*res_factor)
            
            _,_,w,h = draw.textbbox((0,0), letter, font=font)
            # position letter in the middle of the grid box
            xpos = ((j*res_factor + (j+1)*res_factor)/2) - (w/2)
            ypos = (((i*res_factor) + (i+1)*res_factor)/2) - (h/2)

            # hide actual letters and only show color or show full?
            if not answer_hidden: draw.text((xpos, ypos), letter, font=font,  fill=(255, 255, 255))
    
    # grid for empty guess lines
    for i in range(len(guesses),6):
        for j in range(5):
            corner1 = ((j*res_factor) + gridSpacing, (i*res_factor) + gridSpacing) # leaves a border around the rectangle
            corner2 = (((j+1)*res_factor) - gridSpacing, ((i+1)*res_factor) - gridSpacing) #
            draw.rectangle(corner1+corner2, outline=(58, 58, 60), width=4*res_factor)
    
    return resultsImage.tobytes()

async def getPlayerAvatarImage(bot : WordleBot, user : nextcord.User):
    if user in bot.avatar_cache.keys(): return bot.avatar_cache[user] # check cache

    res_factor = bot.image_res_factor
    final_image = Image.new('RGB', (res_factor*5, res_factor*3), color=(18,18,19))

    avatar_bytes = await fetchUserAvatarBytes(user)
    if avatar_bytes is None:
        return final_image
    
    avatar_image = Image.open(io.BytesIO(avatar_bytes))
    mask = bot.avatar_mask
    # apply circular border mask
    
    output = ImageOps.fit(avatar_image, mask.size, centering=(0.5, 0.5))
    output.putalpha(mask)

    # paste with mask
    final_image.paste(output, ((final_image.width - output.width)//2,(final_image.height - output.height)//2), output)
    bot.avatar_cache[user] = final_image # cache for later
    
    # done
    return final_image

async def fetchUserAvatarBytes(user : nextcord.User) -> bytes | None:
    avatar_url = user.display_avatar.url
    
    # fetch bytes
    async with aiohttp.ClientSession() as session:
        async with session.get(avatar_url) as response:
            if response.status == 200:
                image_bytes = await response.read()
                return image_bytes            
            else:
                print(f"Error while trying to fetch player avatar for {user}!")
                return None
            
# Creates full personalized result embed for current or past wordle
def createResultsEmbed(game_data : CurrentGameInfo, game_id : int, guesses : list[str], completed : bool, won : bool,  answer : str) -> Embed:
    current_game_id = game_data.getGameId()
    past_game = False

    gameDisplayName = f"Game #{current_game_id} (LIVE GAME)"
    if game_id != current_game_id:
        past_game = True
        gameDisplayName = f"Game #{game_id} (PAST GAME)"

    # embed data
    title = "Last Played Game" if past_game else ("Currently Playing" if not completed else ("You Won!" if won else "You Lost!"))
    description = "" if past_game else ("Use /guess to make a guess" if not completed else (f"You correctly guessed **{answer}**" if won else f"The word was **{answer}**"))
    
    if past_game and completed:
        description += "VERDICT: **"+("WINNER" if won else "LOSER")+"**"
        description += f"\n\nThe correct word was **{answer}**"
    color = Colour.light_grey() if not completed else (Colour.green() if won else Colour.red())

    # assemble embed
    embed = Embed(title=title, description=description, color=color)
    embed.set_footer(text=gameDisplayName)
    if (len(guesses) > 0):
        # image to be added later on as file
        embed.set_image(url=f"attachment://results.png")

    return embed