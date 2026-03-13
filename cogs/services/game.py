import io
import random
import string
from typing import Literal, cast # use of cast is to make the typechecker happy
from nextcord import Colour, Embed, File, Interaction, TextChannel
from nextcord.ext.commands import Cog
from utils.shared_functions import createResultsEmbed, getUserResultsImageBytes
from utils.types import CurrentGameInfo, PlayerStats, WordleBot, Config, PlayerGameState, PlayerGameData
from utils.utils import Logger
from cogs.services.data import DataService

class GameService(Cog, name="game_service"):
    """
    A service to make and manage all game instances
    """
    def __init__(self, bot : WordleBot) -> None:
        self._bot : WordleBot = bot
        self._config : Config = bot.config
        self._lang : Config = bot.lang

        # logger
        self._log_file_path : str | None = self._config.get('log_file_path')
        assert self._log_file_path is not None
        self._logger : Logger = Logger("GameService", self._log_file_path, debug_mode=self._config.get('debug_mode'))

        self._data_service : DataService

    @Cog.listener()
    async def on_ready(self):
        await self._bot.wait_until_ready()
        self._data_service = cast(DataService, self._bot.get_cog("data_service"))

    async def initService(self) -> None:
        self._active_games : dict = {}
        self._current_game_info : CurrentGameInfo = await self._data_service.getCurrentGameInfo()

        # setup done
        self._logger.debug("Started up successfully.", printToConsole=True)
    
    async def initNewGame(self, terminate_ongoing : bool = False) -> Literal["SUCCESS", "NEED_CONFIRMATION"]:
        """
        Creates a new game for users to play

        Parameters
        ----------
        terminate_ongoing : bool, optional
            Whether to terminate any ongoing games and force start a new one\n
            Requests confirmation if True, else directly starts new game
        """
        if (len(self._active_games) > 0) and (not terminate_ongoing):
            return "NEED_CONFIRMATION"
        
        # TODO: terminate games
        
        embed : Embed = await self._getGameEndEmbed()
        answer : str = random.choice(await self._data_service.getPossibleAnswers())
        answer = answer.upper()
        self._current_game_info.setAnswer(answer)
        self._current_game_info.incrementGameId()
        self._current_game_info.resetParticipants()

        # send out an alert
        alerts_channel : TextChannel = self._bot.alerts_channel
        await alerts_channel.send(embed=embed)

        return "SUCCESS"

    async def startGameFor(self, userId : int, interaction : Interaction, resume : bool = False) -> None:
        """
        Starts a new game for a user\n
        If data for a previous incomplete game exists and is playable, continues that game

        Parameters
        ----------
        userId : int
            The discord ID of the user to start the game for
        pdata : utils.types.PlayerGameData
            Existing player game data of the user to use
        resume : bool, optional
            Resume the last played game (if any) if True, else start new
        """
        plr_game : PlayerGameData = await self._data_service.getPlayerGameDataFor(userId)
        plr_stats : PlayerStats = await self._data_service.getPlayerStatsFor(userId)

        # check for a started but incomplete game
        starting_guesses = []
        if (plr_game.getLastPlayedGameId() == self._current_game_info.getGameId()) and (not plr_game.isCompleted()) and resume:
            starting_guesses = plr_game.getGuesses()

        # create and begin game    
        instance = GameInstance(self._bot, interaction, plr_game, plr_stats, self._logger, self._current_game_info, starting_guesses)
        self._active_games[userId] = instance
        await instance.initGame()
    
    async def getUserGameState(self, userId : int) -> PlayerGameState:
        """
        Returns the current state of a user's ongoing or past game

        Parameters
        -------
        userId : int
            The discord ID of the user to check for
        
        Returns
        -------
        game_state: utils.types.PlayerGameState
            The current game state for the user
        """
        existing_game : bool = userId in self._active_games.keys()    
        if existing_game:
            return PlayerGameState.ONGOING # has assigned game instance
        
        # check game data
        plr_game : PlayerGameData = await self._data_service.getPlayerGameDataFor(userId)

        if plr_game.getLastPlayedGameId() != self._current_game_info.getGameId():
            return PlayerGameState.NOT_STARTED # never started current game
        if not plr_game.isCompleted():
            return PlayerGameState.INCOMPLETE # started game but didnt complete
        elif plr_game.isCompleted():
            return PlayerGameState.COMPLETED # already completed current game
        return PlayerGameState.UNKNOWN # something went wrong
    
    async def _getGameEndEmbed(self) -> Embed:
        embed = Embed(title=self._lang.get('game_end_title'), description=f"{self._lang.get('game_end_description')}\n", color=Colour.red())
        embed.set_footer(text=self._lang.get('game_end_footer').replace('{id}', f'{self._current_game_info.getGameId()}'))

        # no one played
        if len(self._current_game_info.getParticipants()) == 0:
            embed.add_field(name=self._lang.get('no_available_results'), value="", inline=False)
            return embed
        
        # build results message
        lines = "\n"
        all_p_data : dict[int, PlayerGameData] = await self._data_service.getPlayerGameData()
        for userId in self._current_game_info.getParticipants():
            pdata : PlayerGameData = all_p_data[userId]
            if not pdata.isCompleted():
                text = self._lang.get('user_did_not_finish_game')
            else:
                result = self._lang.get('won') if pdata.isWon() else self._lang.get('lost')
                text = self._lang.get('user_result_text').replace('{user_id}', userId).replace('{result}', result).replace('{move_count}', f'{len(pdata.getGuesses())}')
            lines += text
        embed.add_field(name=self._lang.get('game_results_title'), value=lines, inline=False)
        embed.add_field(name="", value=f"*{self._lang.get('new_game_started')}*", inline=False)

        return embed

def setup(bot : WordleBot) -> None:
    bot.add_cog(GameService(bot))

#####
#####
#####

# TODO live update message
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
        self._continued = len(self._guesses) > 0
        self._ongoing = True
        self._completed = False
        self._won = False
        self._silent_start = silent_start
        self._last_results_image : io.BytesIO
        self._plr_data.setLastPlayedGameId(self._game_id)
    
    async def _dataSaveCycle(self):
        self._plr_data.setAnswer(self._answer)
        self._plr_data.setGuesses(self._guesses)
        self._plr_data.setCompleted(self._completed)
        self._plr_data.setWon(self._won)

        if self._completed:
            self._plr_stats.incrementGamesPlayed()
            if self._won:
                self._plr_stats.incrementGamesWon()
                self._plr_stats.incrementWinstreak()
            else:
                self._plr_stats.resetWinStreak()
    
    async def initGame(self):
        await self._dataSaveCycle()
        if self._silent_start: 
            return
        
        title = "Game Started" if self._continued else "Game Ongoing"
        embed = Embed(title=title, description="Use /guess to make a guess")
        embed.set_footer(text=f"Game #{self._game_id}")

        if self._continued:
            # get results image and convert to send
            result_image_bytes : bytes = await getUserResultsImageBytes(self._bot, self._guesses, self._answer)
            result_image = io.BytesIO(result_image_bytes)
            result_image.seek(0)

            image_file = File(fp=result_image, filename="result.png")
            await self._last_user_interaction.followup.send(embed=embed, file=image_file)
        # no available result
        await self._last_user_interaction.followup.send(embed=embed)

    async def mainLoop(self):
        await self._dataSaveCycle()
        
        embed = createResultsEmbed(self._current_game_info, self._current_game_info.getGameId(), self._guesses, self._completed, self._won, self._answer)
        # results image
        result_image_bytes : bytes = await getUserResultsImageBytes(self._bot, self._guesses, self._answer)
        result_image = io.BytesIO(result_image_bytes)
        result_image.seek(0)
        self._last_results_image = result_image
        # send complete embed
        await self._last_user_interaction.followup.send(embed=embed, file=File(fp=self._last_results_image, filename="results.png"), ephemeral=True, delete_after=30)
    
    async def gameWon(self):
        self._ongoing = False
        self._completed = True
        self._won = True
        await self._dataSaveCycle()

        embed = createResultsEmbed(self._current_game_info, self._current_game_info.getGameId(), self._guesses, self._completed, self._won, self._answer)
        await self._last_user_interaction.followup.send(embed=embed, file=File(fp=self._last_results_image, filename="results.png"), ephemeral=True, delete_after=30)
    
    async def gameLost(self):
        self._ongoing = False
        self._completed = True
        self._won = False
        await self._dataSaveCycle()
        
        embed = createResultsEmbed(self._current_game_info, self._current_game_info.getGameId(), self._guesses, self._completed, self._won, self._answer)
        await self._last_user_interaction.followup.send(embed=embed, file=File(fp=self._last_results_image, filename="results.png"), ephemeral=True, delete_after=30)

    async def validateGuess(self, interaction : Interaction, guess : str, allowed_guesses : list[str]):
        self._last_user_interaction = interaction
        guess = guess.upper()

        # valid guess?
        if len(guess) != 5:
            await interaction.followup.send("Your guess must contain 5 letters!", ephemeral=True, delete_after=10)
            return
        for ch in guess:
            if ch not in string.ascii_uppercase:
                await interaction.followup.send("Your guess must only contain alphabets!", ephemeral=True, delete_after=10)
                return
        
        # check against allowed guesses
        if guess.lower() not in allowed_guesses:
            await interaction.followup.send(f"**{guess}** is not a valid word!", ephemeral=True, delete_after=10)
            return
        
        # already guessed this word?
        if guess in self._guesses:
            await interaction.followup.send(f"You have already guessed **{guess}**!", ephemeral=True, delete_after=10)
            return
        
        ### GUESS IS VALID
        self._guesses.append(guess)
        await self.mainLoop()
        
        # check win
        if guess == self._answer:
            self._logger.debug(f"{interaction.user} guessed the word correctly.")
            await interaction.followup.send("You guessed the word correctly!", ephemeral=True, delete_after=5)
            await self.gameWon()
            return
        
        # out of guesses?
        if len(self._guesses) >= 6:
            await interaction.followup.send("You are out of guesses!", ephemeral=True, delete_after=5)
            await self.gameLost()
            return
        
        await interaction.followup.send(f"You guessed {guess}.", ephemeral=True, delete_after=5)
        
    async def terminate(self, reason : str = "Unspecified"):
        self._ongoing = False
        self._won = False
        self._completed = False
        await self._dataSaveCycle()

        embed = Embed(title="Oops!", color=Colour.red())
        embed.set_footer(text=f"Game #{self._current_game_info.gameId}")
        embed.add_field(name="Game Terminated", value=f"This game has been **terminated!**\nReason: {reason}")
        
        await self._last_user_interaction.followup.send(embed=embed, ephemeral=True, delete_after=30)