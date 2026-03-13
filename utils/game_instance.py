import io
import string

from nextcord import Colour, Embed, File, Interaction

from utils.shared_functions import createResultsEmbed, getUserResultsImageBytes
from utils.utils import Logger
from utils.types import CurrentGameInfo, PlayerGameData, PlayerStats, WordleBot

class GameInstance():
    """
    A class to create and manage a particular game instance

    Parameters
    ----------
    bot: utils.types.WordleBot
        The bot
    interaction: nextcord.Interaction
        The interaction to use for communication with the user
    plr_data: utils.types.PlayerGameData
        The user's current game data
    plr_stats: utils.types.PlayerStats
        The user's current stats
    logger: utils.utils.Logger
        The logger to use for logging
    current_game_info: utils.types.CurrentGameInfo
        The bot's current game info
    starting_guesses: list[str], optional
        The guesses to already count at the time of starting the game
    silent_start: bool, optional
        Whether to avoid informing the player when the game instance is initially created
    """
    def __init__(self,
                 bot : WordleBot, 
                 interaction : Interaction, 
                 plr_data: PlayerGameData, 
                 plr_stats : PlayerStats, 
                 logger : Logger, 
                 current_game_info : CurrentGameInfo, 
                 starting_guesses : list[str] = [],
                 silent_start : bool = False
                 ):
        
        self._bot = bot
        self._last_user_interaction = interaction
        self._plr_data = plr_data
        self._plr_stats = plr_stats
        self._logger = logger # logger is shared with GameService
        self._current_game_info = current_game_info
        self._game_id = current_game_info.getGameId()
        self._answer = current_game_info.getAnswer()
        self._guesses = starting_guesses
        self._continued = len(self._guesses) > 0 # game is being continued
        self.ongoing = False
        self.completed = False
        self._won = False
        self._silent_start = silent_start
    
    async def _dataSaveCycle(self, affect_stats : bool = True):
        """
        Save current player game data to keep live track
        """
        self._plr_data.setGuesses(self._guesses)
        self._plr_data.setCompleted(self.completed)
        self._plr_data.setWon(self._won)

        if affect_stats and self.completed: # only runs if game was not terminated
            self._plr_stats.incrementGamesPlayed()
            if self._won:
                self._plr_stats.incrementGamesWon()
                self._plr_stats.incrementWinstreak()
            else:
                self._plr_stats.resetWinStreak()
    
    async def initGame(self):
        """
        Start the game and allow the user to start playing
        """
        self._plr_data.setLastPlayedGameId(self._game_id)
        self._plr_data.setAnswer(self._answer)
        await self._dataSaveCycle()

        self.ongoing = True
        if self._silent_start: 
            return
        
        # send starting message if not silent
        title = "Game Started" if self._continued else "Game Ongoing"
        embed = Embed(title=title, description="Use /guess to make a guess")
        embed.set_footer(text=f"Game #{self._game_id}")

        # current results image
        result_image_buffer : io.BytesIO = await getUserResultsImageBytes(self._bot, self._guesses, self._answer)
        image_file = File(fp=result_image_buffer, filename="results.png")
        embed.set_image(url="attachment://results.png")

        await self._last_user_interaction.followup.send(embed=embed, file=image_file)

    async def processGuess(self, interaction : Interaction, guess : str, allowed_guesses : list[str]):
        """
        Checks the validity of a guess and runs the necessary processes to account for it in an ongoing game
        """
        self._last_user_interaction : Interaction = interaction # refresh webhook token
        guess = guess.upper()

        valid_guess = await self._validateGuess(interaction, guess, allowed_guesses)
        if not valid_guess: return # will have been handled in _validateGuess

        self._guesses.append(guess)
        
        # check win
        if guess == self._answer:
            self._logger.debug(f"{interaction.user} guessed the word correctly.")
            await interaction.send("You guessed the word correctly!", delete_after=5, ephemeral=True)
            await self._gameWon()
            return
        
        # out of guesses?
        if len(self._guesses) >= 6:
            await interaction.send("You are out of guesses!", delete_after=5, ephemeral=True)
            await self._gameLost()
            return
        
        await self._mainLoop()
        await interaction.send(f"You guessed {guess}", delete_after=5, ephemeral=True)
        return

    async def _mainLoop(self):
        """
        Saves player game data and sends a live results message
        """
        await self._dataSaveCycle()
        
        # results image
        result_image_buffer : io.BytesIO = await getUserResultsImageBytes(self._bot, self._guesses, self._answer)
        image_file = File(fp=result_image_buffer, filename="results.png")

        # send complete embed
        embed = createResultsEmbed(self._game_id, self.completed, self._won, self._answer)
        embed.set_image(url=f"attachment://results.png")
        await self._last_user_interaction.send(embed=embed, file=image_file, ephemeral=True)
    
    async def _gameWon(self):
        """
        Marks game as won, saves player game data, and sends the appropriate message
        """
        self.ongoing = False
        self._won = True

        # results image
        result_image_buffer : io.BytesIO = await getUserResultsImageBytes(self._bot, self._guesses, self._answer)
        image_file = File(fp=result_image_buffer, filename="results.png")

        embed = createResultsEmbed(self._game_id, True, self._won, self._answer)
        embed.set_image(url=f"attachment://results.png")
        await self._last_user_interaction.send(embed=embed, file=image_file, ephemeral=True)
        
        self.completed = True
        await self._dataSaveCycle()
    
    async def _gameLost(self):
        """
        Marks game as lost, saves player game data, and sends the appropriate message
        """
        self.ongoing = False
        self._won = False

        # results image
        result_image_buffer : io.BytesIO = await getUserResultsImageBytes(self._bot, self._guesses, self._answer)
        image_file = File(fp=result_image_buffer, filename="results.png")
        
        embed = createResultsEmbed(self._game_id, True, self._won, self._answer)
        embed.set_image(url=f"attachment://results.png")
        await self._last_user_interaction.send(embed=embed, file=image_file, ephemeral=True)
        
        self.completed = True
        await self._dataSaveCycle()

    async def _validateGuess(self, interaction : Interaction, guess : str, allowed_guesses : list[str]) -> bool:
        """
        Checks whether a guess is valid and can be used at the current state of the game

        Parameters
        ----------
        interaction: nextcord.Interaction
            an interaction of the user who is playing the game in order to send replies and continue game
        guess : str
            The guess as a string
        allowed_guesses : list[str]
            A list of all allowed guesses in lowercase
        """

        # character count and alphabet check
        if len(guess) != 5:
            await interaction.followup.send("Your guess must contain 5 letters!", delete_after=10)
            return False
        for ch in guess:
            if ch not in string.ascii_uppercase:
                await interaction.followup.send("Your guess must only contain alphabets!", delete_after=10)
                return False
        
        # not an allowed guess
        if guess not in allowed_guesses:
            await interaction.followup.send(f"**{guess}** is not a valid word!", delete_after=10)
            return False
        
        # already guessed this word
        if guess in self._guesses:
            await interaction.followup.send(f"You have already guessed **{guess}**!", delete_after=10)
            return False
        
        ### GUESS IS VALID
        return True
        
    async def terminate(self, reason : str = "Unspecified"):
        """
        Terminates an ongoing game without affecting player stats
        """
        self.ongoing = False
        self._won = False
        
        embed = Embed(title="Oops!", color=Colour.red())
        embed.set_footer(text=f"Game #{self._game_id}")
        embed.add_field(name="Game Terminated", value=f"This game has been **terminated!**\nReason: {reason}")
        
        await self._last_user_interaction.send(embed=embed, delete_after=30, ephemeral=True)
        self.completed = True
        await self._dataSaveCycle(affect_stats=False)