import io
import logging
import string

from nextcord import Colour, Embed, File, Interaction

from utils.shared_functions import createResultsEmbed, getUserResultsImageBytes
from utils.utils import Logger
from utils.types import PlayerGameData, PlayerStats, WordleBot

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
    game_id: int
        The id of the game to play
    answer : str
        The answer word
    starting_guesses: list[str], optional
        The guesses to already count at the time of starting the game
    silent_start: bool, optional
        Whether to avoid informing the player when the game instance is initially created
    """
    def __init__(self,
                 bot : WordleBot, 
                 logger : Logger, 
                 interaction : Interaction, 
                 plr_data: PlayerGameData, 
                 plr_stats : PlayerStats, 
                 game_id : int,
                 answer : str,
                 starting_guesses : list[str] = [],
                 continued : bool = False,
                 silent_start : bool = False
                 ):
        
        assert interaction.user is not None
        
        self._bot = bot
        self._last_user_interaction = interaction # humble attempt to bypass 15 min webhook expiration
        self._plr_data = plr_data
        self._plr_stats = plr_stats
        self._logger = logger # copy GameServiceLogger
        self._logger.name = f"GameInstance({interaction.user.id})"
        self._game_id = game_id
        self._answer = answer
        self._guesses = starting_guesses
        self._continued = continued # this is the continuation of a past game
        self.ongoing = False # game running or paused
        self.finished = False # instance completing all operations
        self._completed = False # user completing the game
        self._won = False
        self._silent_start = silent_start

        self._logger.debug(f"Instance Initialised.")
    
    async def _dataSaveCycle(self, affect_stats : bool = True):
        """
        Save current player game data to keep live track
        """
        self._logger.debug("Saving player game data...")
        self._plr_data.setGuesses(self._guesses)
        self._plr_data.setCompleted(self._completed)
        self._plr_data.setWon(self._won)

        if affect_stats and self._completed: # only runs if game was not terminated
            self._plr_stats.incrementGamesPlayed()
            if self._won:
                self._plr_stats.incrementGamesWon()
                self._plr_stats.incrementWinstreak()
            else:
                self._plr_stats.resetWinStreak()
        
        self._logger.debug("Saved player game data.")
    
    async def initGame(self) -> None:
        """
        Start the game and allow the user to start playing
        """
        self._logger.debug("Starting game.")
        self._plr_data.setLastPlayedGameId(self._game_id)
        self._plr_data.setAnswer(self._answer)
        await self._dataSaveCycle()

        self.ongoing = True
        if self._silent_start: 
            return
        
        # send starting message if not silent
        title = "Game Started" if self._continued else f"Game {self._game_id}"
        embed = Embed(title=title, description="Use /guess to make a guess")
        embed.set_footer(text=f"Game #{self._game_id}")

        # current results image
        result_image_buffer : io.BytesIO = await getUserResultsImageBytes(self._bot, self._guesses, self._answer)
        image_file = File(fp=result_image_buffer, filename="results.webp")
        embed.set_image(url="attachment://results.webp")

        await self._last_user_interaction.edit_original_message(content=None, embed=embed, file=image_file)
        
        self._logger.debug("Game started.")
        return

    async def processGuess(self, interaction : Interaction, guess : str, allowed_guesses : list[str]) -> None:
        """
        Checks the validity of a guess and runs the necessary processes to account for it in an ongoing game
        """
        self._logger.debug(f"Processing guess [{guess}].")

        self._last_user_interaction : Interaction = interaction # need new webhook token to avoid 15min limit
        guess = guess.upper()

        valid_guess = await self._validateGuess(interaction, guess, allowed_guesses)
        if not valid_guess: return # will have been handled in _validateGuess

        self._guesses.append(guess)
        
        # check win
        if guess == self._answer:
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
        
        self._logger.debug("Guess acknowledged.")
        return

    async def _mainLoop(self) -> None:
        """
        Saves player game data and sends a live results message
        """
        self._logger.debug("- main game loop -")
        await self._dataSaveCycle()
        
        # results image
        result_image_buffer : io.BytesIO = await getUserResultsImageBytes(self._bot, self._guesses, self._answer)
        image_file = File(fp=result_image_buffer, filename="results.webp")

        # send complete embed
        self._logger.debug("Sending current results.")
        embed = createResultsEmbed(self._game_id, self._completed, self._won, self._answer)
        embed.set_image(url=f"attachment://results.webp")
        await self._last_user_interaction.send(embed=embed, file=image_file, ephemeral=True)
    
    async def _gameWon(self) -> None:
        """
        Marks game as won, saves player game data, and sends the appropriate message
        """
        self._logger.debug(f"Player guessed the word successfully ({self._answer})")

        self.ongoing = False
        self._won = True
        self._completed = True
        await self._dataSaveCycle()

        # results image
        result_image_buffer : io.BytesIO = await getUserResultsImageBytes(self._bot, self._guesses, self._answer)
        image_file = File(fp=result_image_buffer, filename="results.webp")

        self._logger.debug("Sending final results.")
        embed = createResultsEmbed(self._game_id, True, self._won, self._answer)
        embed.set_image(url=f"attachment://results.webp")
        await self._last_user_interaction.send(embed=embed, file=image_file, ephemeral=True)

        self.finished = True
        self._logger.debug("Game Finished.")
    
    async def _gameLost(self) -> None:
        """
        Marks game as lost, saves player game data, and sends the appropriate message
        """
        self._logger.debug(f"Player failed to guess the word ({self._answer}).")

        self.ongoing = False
        self._won = False
        self._completed = True
        await self._dataSaveCycle()

        # results image
        result_image_buffer : io.BytesIO = await getUserResultsImageBytes(self._bot, self._guesses, self._answer)
        image_file = File(fp=result_image_buffer, filename="results.webp")
        
        self._logger.debug("Sending final results.")
        embed = createResultsEmbed(self._game_id, True, self._won, self._answer)
        embed.set_image(url=f"attachment://results.webp")
        await self._last_user_interaction.send(embed=embed, file=image_file, ephemeral=True)

        self.finished = True
        self._logger.debug("Game Finished.")

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
            self._logger.debug("Guess did not pass length test.")
            await interaction.followup.send("Your guess must contain 5 letters!", delete_after=10)
            return False
        for ch in guess:
            if ch not in string.ascii_uppercase:
                self._logger.debug("Guess did not pass symbol test.")
                await interaction.followup.send("Your guess must only contain alphabets!", delete_after=10)
                return False
        
        # not an allowed guess
        if guess not in allowed_guesses:
            self._logger.debug("Guess not in word list.")
            await interaction.followup.send(f"**{guess}** is not a valid word!", delete_after=10)
            return False
        
        # already guessed this word
        if guess in self._guesses:
            self._logger.debug("Guess already used.")
            await interaction.followup.send(f"You have already guessed **{guess}**!", delete_after=10)
            return False
        
        ### GUESS IS VALID
        self._logger.debug("Guess is valid.")
        return True
        
    async def terminate(self, reason : str = "Unspecified") -> None:
        """
        Terminates an ongoing game without affecting player stats
        """
        self._logger.debug("Terminate command received")
        
        self.ongoing = False
        self._won = False
        self._completed = True
        await self._dataSaveCycle(affect_stats=False)
        
        embed = Embed(title="Oops!", color=Colour.red())
        embed.set_footer(text=f"Game #{self._game_id}")
        embed.add_field(name="Game Terminated", value=f"This game has been **terminated!**\nReason: {reason}")
        
        await self._last_user_interaction.send(embed=embed, delete_after=30, ephemeral=True)

        self._logger.debug("Game Terminated.")
        self.finished = True
        return