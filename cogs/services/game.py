import random
from typing import Literal, cast # use of cast is to make the typechecker happy
from nextcord import Colour, Embed, Interaction, Role, TextChannel
from nextcord.ext.commands import Cog
from utils.types import CurrentGameInfo, WordleBot, Config, PlayerGameState, PlayerGameData
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
        
        embed : Embed = await self.getGameEndEmbed()
        answer : str = random.choice(await self._data_service.getPossibleAnswers())
        answer = answer.upper()
        self._current_game_info.setAnswer(answer)
        self._current_game_info.incrementGameId()

        # alert everyone
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
        pdata : PlayerGameData = await self._data_service.getPlayerGameDataFor(userId)
        print(interaction.user, resume, pdata)
    
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
        pdata : PlayerGameData = await self._data_service.getPlayerGameDataFor(userId)

        if pdata.getLastPlayedGameId() != self._current_game_info.getGameId():
            return PlayerGameState.NOT_STARTED # never started current game
        if not pdata.isCompleted():
            return PlayerGameState.INCOMPLETE # started game earlier but didnt complete
        elif pdata.isCompleted():
            return PlayerGameState.COMPLETED # already completed current game
        return PlayerGameState.UNKNOWN # something went wrong
    
    async def getGameEndEmbed(self) -> Embed:
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

class GameInstance():
    """
    A class to create and manage a particular game instance
    """
    def __init__(self, bot : WordleBot, logger : Logger, answer : str, starting_guesses : list[str] = []):
        self._bot : WordleBot = bot
        self._logger : Logger = logger # logger is shared with GameService
        self._answer = answer
        self._starting_guesses = starting_guesses