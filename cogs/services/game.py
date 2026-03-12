from typing import cast # use of cast is to make the typechecker happy
from nextcord.ext.commands import Cog
from utils.types import WordleBot, BotConfig, PlayerGameState, PlayerGameData, InternalData
from utils.utils import Cache, Logger
from cogs.services.data import DataService

class GameService(Cog, name="game_service"):
    """
    A service to make and manage all the games of wordle
    """
    def __init__(self, bot : WordleBot) -> None:
        self._bot : WordleBot = bot
        self._config : BotConfig = bot.config
        self._data_service : DataService = cast(DataService, bot.get_cog("data_service"))

        # logger
        self._log_file_path : str | None = self._config.get('log_file_path')
        assert self._log_file_path is not None
        self._logger : Logger = Logger("GameService", self._log_file_path)

        self._active_games : Cache = Cache(self._logger)
        self._internal_data : InternalData = self._data_service.getInternalData()
        
        # setup done
        self._logger.info("Started up successfully.", printToConsole=True)
    
    def startGameFor(self, userId : int, pdata : PlayerGameData):
        """
        Starts a new game of wordle for a user\n
        If data for a previous incomplete game exists and is playable, continues that game

        Parameters
        ----------
        userId : int
            The discord ID of the user to start the game for
        pdata : utils.types.PlayerGameData
            Existing player game data of the user to use
        """
    
    def canUserStartGame(self, userId : int) -> tuple[bool, PlayerGameState]:
        """
        Checks whether a user is eligible to start a new game of wordle

        Parameters
        -------
        userId : int
            The discord ID of the user to check for
        
        Returns
        -------
        can_start: bool
            True if eligible, else False
        game_status: utils.types.GameStatus
            The current game status of the user
        """
        instance : GameInstance | None = self._active_games.get(userId)    
        # has an assigned game instance
        if instance is not None:
            return False, PlayerGameState.ONGOING
        
        # check past data
        if not self._data_service.userExists(userId):
            return False, PlayerGameState.UNKNOWN # no record of this player existing
        
        pdata : PlayerGameData | None = self._data_service.getPlayerGameDataFor(userId)
        assert pdata is not None

        if pdata.getLastPlayedGameId() != self._internal_data.getGameId():
            return True, PlayerGameState.NOT_STARTED # never started current game
        if pdata.isCompleted():
            return False, PlayerGameState.COMPLETED # already completed current game
        if self._active_games.exists(userId):
            return False, PlayerGameState.ONGOING # playing right now
        return True, PlayerGameState.INCOMPLETE # started game earlier but didnt complete

def setup(bot : WordleBot) -> None:
    bot.add_cog(GameService(bot))

#####
#####
#####

class GameData():
    """
    A class to store and manage the data for a GameInstance
    """
    def __init__(self):
        self.completed = False
        self.won = False
        self.answer = None
        self.guesses = []

class GameInstance():
    """
    A class to create and manage a game of wordle that is being played
    """
    def __init__(self, bot : WordleBot, logger : Logger, starting_data : GameData):
        self._bot : WordleBot = bot
        self._logger : Logger = logger # logger is shared with GameService
        self._gameInfo : Cache = Cache(self._logger)

        self._data : GameData = starting_data