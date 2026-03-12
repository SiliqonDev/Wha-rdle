# epic tower of imports
import pickle
from nextcord.ext import tasks
from nextcord.ext.commands import Cog
from pathlib import Path
from data.interface import DBInterface
from utils.types import WordleBot, BotConfig, PlayerGameData, PlayerStats, InternalData
from utils.utils import Logger, Cache

class DataService(Cog, name="data_service"):
    def __init__(self, bot : WordleBot) -> None:
        """A service to manage all data related to players and games

        Parameters
        ----------
        bot: nextcord.ext.commands.Bot
            The nextcord bot object
        """
        self._bot = bot
        self._config : BotConfig = bot.config

        # logger
        self._log_file_path = self._config.get('log_file_path')
        assert self._log_file_path is not None
        self._logger = Logger("DataService", self._log_file_path)

        self._logger.info("Started up successfully.", printToConsole=True)

    async def initService(self) -> None:
        """Connect to the database and build the cache

        Parameters
        ----------
        bot_config: modules.types.BotConfig
            The config file of the bot
        """
        self._cwd = self._config.get('cwd')
        assert self._cwd is not None

        self._cache = Cache(logger=self._logger, initial_data={
            "player_game_data": {},
            "player_stats": {},
            "internal_data": InternalData()
            })
        
        # connect with db
        try:
            self._db_interface = DBInterface()
            await self._db_interface.connect(self._cwd)
            await self._db_interface.build()
        except Exception as e:
            self._logger.critical("Failed to connect to database!", printToConsole=True)
            self._logger.exception(e)
            # shutdown bot
            await self._bot.close()
        
        await self._makeDirectories()
        await self._buildCache()
        # all done and dusted
        self._logger.info("Cache initialised", printToConsole=True)
    
    @tasks.loop(seconds=120)
    async def _autosave(self) -> None:
        """
        autosaves data to protect against crashes
        """
        self._logger.info("Beginning autosave.")
        await self._savePlayerGameData(self.getPlayerGameData())
        await self._savePlayerStats(self.getPlayerStats())
        await self._saveInternalData(self.getInternalData())
        self._logger.info("Autosave completed.")

    async def _buildCache(self) -> None:
        """
        executes necessary methods to cache all available data
        """
        await self._cacheWordList()
        await self._cachePlayerGameData()
        await self._cachePlayerStats()
        await self._cacheInternalData()
        
        # all done
        self._autosave.start()

    async def _makeDirectories(self) -> None:
        """
        initialises important directories if they do not exist.
        """
        Path(f"{self._cwd}/temp/images").mkdir(parents=True, exist_ok=True)
        Path(f"{self._cwd}/logs").mkdir(parents=True, exist_ok=True)
    
    ###
    ### CHECKERS
    def userExists(self, userId : int) -> bool:
        """
        returns whether the user is present in the database

        Parameters
        ----------
        userId : int
            The discord ID of the user to check for

        Returns
        -------
        value: bool
            True if any data is present, else False
        """
        return self._cache.exists('player_game_data', userId) 
    
    ###
    ### GETTERS
    def _getterWarning(self, key, userId):
        self._logger.warning(f'Attemping to retrieve `{key}` for non-existent user `{userId}`!', printToConsole=True)

    def getPlayerGameData(self) -> dict[int, PlayerGameData]:
        """
        returns the available PlayerGameData object for all users
        
        Returns
        -------
        data: dict[int, utils.types.PlayerGameData]
            The data of all users users indexed by user id
        """
        player_data = self._cache.get('player_game_data')
        assert player_data is not None
        return player_data
    
    def getPlayerGameDataFor(self, userId : int) -> PlayerGameData | None:
        """
        returns the PlayerGameData object for a user

        Parameters
        ----------
        userId: int
            The user's discord ID

        Returns
        -------
        data: utils.types.PlayerGameData | None
            The data if found, else None
        """
        user_data : PlayerGameData | None = self._cache.get(['player_game_data', userId])
        if not user_data: self._getterWarning('player_game_data', userId)
        return user_data
    
    def getPlayerStats(self) -> dict[int, PlayerStats]:
        """
        returns the available PlayerStats objects for all users

        Returns
        -------
        stats: dict[int, utils.types.PlayerStats]:
            The stats of all users indexed by user id
        """
        player_stats = self._cache.get('player_stats')
        assert player_stats is not None
        return player_stats
    
    def getPlayerStatsFor(self, userId : int) -> PlayerStats | None:
        """
        returns the PlayerStats object of a user

        Parameters
        ----------
        userId: int
            The user's discord ID

        Returns
        -------
        stats: utils.types.PlayerStats
            The stats if found, else None
        """
        user_stats : PlayerStats | None = self._cache.get(['player_stats', userId])
        if not user_stats: self._getterWarning('player_stats', userId)
        return user_stats

    def getInternalData(self) -> InternalData:
        """
        returns the InternalData object for the bot

        Returns
        ----------
        data: utils.types.InternalData
            The data object
        """
        data = self._cache.get('internal_data')
        assert data is not None
        return data

    ###
    ### SETTERS
    def setPlayerGameData(self, data : dict[int, PlayerGameData]) -> None:
        """
        sets the global player game data in the cache

        Parameters
        ----------
        data: dict[int, utils.types.PlayerGameData]
            PlayerGameData object of every player, indexed by discord user ID
        """
        self._cache.put(key='player_game_data', value=data)
    
    def setPlayerStats(self, stats: dict[int, PlayerStats]) -> None:
        """
        sets the global player stats in the cache

        Parameters
        ----------
        data: dict[int, utils.types.PlayerStats]
            PlayerStats object of every player, indexed by discord user ID
        """
        self._cache.put(key="player_stats", value=stats)

    def setInternalData(self, data : InternalData) -> None:
        """
        sets the bot's InternalData object

        Parameters
        ----------
        data: utils.types.InternalData
            the new InternalData object
        """
        self._cache.put(key='internal_data',value=data)

    def setPlayerGameDataFor(self, userId : int, data : PlayerGameData) -> None:
        """
        sets the PlayerGameData object for a specific user

        Parameters
        ----------
        userId: int
            The user's discord ID
        data: utils.types.PlayerGameData
            the new PlayerGameData object
        """
        self._cache.put('player_game_data',key=userId, value=data)
    
    def setPlayerStatsFor(self, userId : int, stats : PlayerStats) -> None:
        """
        sets the PlayerStats object for a specific user

        Parameters
        ----------
        userId: int
            The user's discord ID
        data: utils.types.PlayerStats
            the new PlayerStats object
        """
        self._cache.put('player_stats', key=userId, value=stats)
    
    ###
    ### SAVING
    ###

    async def _savePlayerGameData(self, data : dict[int, PlayerGameData] | None = None) -> None:
        """
        saves the game data of all given players

        Parameters
        ----------
        data: dict[int, utils.types.PlayerGameData] | None, optional
            The data to save, grabs from cache if not specified.
        """
        if not data:
            data = self._cache.get('player_game_data')
            assert data is not None
        # go through each user
        for userId, pdata in data.items():
            last_played_game_id : int = pdata.getLastPlayedGameId()
            guesses : bytes = pickle.dumps(pdata.getGuesses())
            completed : bool = pdata.isCompleted()
            won : bool = pdata.isWon()
            answer : str = pdata.getAnswer()
            # insert if new, else update
            await self._db_interface.execute("INSERT INTO player_game_data (userId, last_played_game_id, guesses, completed, won, answer) "\
                                            "values(?,?,?,?,?,?) ON CONFLICT(userId) Do UPDATE SET "\
                                            "last_played_game_id=excluded.last_played_game_id, guesses=excluded.guesses, completed=excluded.completed, won=excluded.won, answer=excluded.answer",
                                            userId, last_played_game_id, guesses, completed, won, answer)
        # bulk commit all of it
        await self._db_interface.commit()
    
    async def _savePlayerStats(self, data : dict[int, PlayerStats] | None = None) -> None:
        """
        saves the stats of all given players

        Parameters
        ----------
        data: dict[int, utils.types.PlayerStats] | None, optional
            The stats to save, grabs from cache if not specified.
        """
        if not data:
            data = self._cache.get('player_stats')
            assert data is not None
        # go through each user
        for userId, stats in data.items():
            games_played : int = stats.getGamesPlayed()
            games_won : int = stats.getGamesWon()
            # insert if new, else update
            await self._db_interface.execute("INSERT INTO player_stats (userId, games_played, games_won) "\
                                            "values(?,?,?) ON CONFLICT DO UPDATE SET "\
                                            "games_played=exclueded.games_played, gamesWon=excluded.games_won",
                                            userId, games_played, games_won)
        # bulk commit all of it
        await self._db_interface.commit()
    
    async def _saveInternalData(self, data : InternalData | None = None) -> None:
        """
        saves the internal data of the bot

        Parameters
        ----------
        data: dict[int, utils.types.InternalData] | None, optional
            The data to save, grabs from cache if not specified.
        """
        if not data:
            data = self._cache.get('internal_data')
            assert data is not None

        # save
        gameId : int = data.getGameId()
        answer : str = data.getAnswer()
        past_words : bytes = pickle.dumps(data.getPastWords())

        # insert if doesn't exist, else update
        await self._db_interface.execute("INSERT INTO internal_data (_id, gameId, answer, past_words) "\
                                        "values(0, ?, ?, ?) "\
                                        "ON CONFLICT(_id) DO UPDATE SET "\
                                        "gameId=excluded.gameId, answer=excluded.answer, past_words=excluded.past_words", 
                                        gameId, answer, past_words)
        await self._db_interface.commit()

    ###
    ### CACHING
    ###

    # aint no wordle without words
    async def _cacheWordList(self) -> None:
        """
        cache all the allowed guesses and possible answers\n
        grabs from ./assets/files/
        """
        allowed_guesses = []
        possible_answers = []
        with open(f"{self._cwd}/assets/files/allowed-guesses.txt", 'r') as f1:
            for line in f1:
                allowed_guesses.append(line.strip())
        with open(f"{self._cwd}/assets/files/possible-answers.txt", 'r') as f2:
            for line in f2:
                possible_answers.append(line.strip())
        
        # put in cache
        self._cache.put('word_list', key='allowed_guesses', value=allowed_guesses)
        self._cache.put('word_list', key='possible_answers', value=possible_answers)

    async def _cachePlayerGameData(self) -> None:
        """
        grabs all available player game data from the database and caches it
        """
        reply = await self._db_interface.records("SELECT * FROM player_game_data")
        for record in reply:
            userId, last_played_game_id, guesses, completed, won, answer = record
            pdata = PlayerGameData(userId, last_played_game_id, pickle.loads(guesses), completed, won, answer)
            self._cache.put('player_game_data', key=userId, value=pdata)
    
    async def _cachePlayerStats(self) -> None:
        """
        grabs all available player stats from the database and caches them
        """
        reply = await self._db_interface.records("SELECT * FROM player_stats")
        for record in reply:
            userId, games_played, games_won = record
            pstats = PlayerStats(userId, games_played, games_won)

            self._cache.put('player_stats', key=userId, value=pstats)
    
    async def _cacheInternalData(self):
        """
        grabs all available internal bot data from the database and caches it
        """
        reply = await self._db_interface.record("SELECT * FROM internal_data WHERE _id=0")
        if reply is None:
            # initial data was not created
            await self._saveInternalData()
            await self._cacheInternalData()
            return
        
        _, gameId, answer, past_words = reply
        data = InternalData(gameId, answer, past_words)
        self._cache.put(key='internal_data', value=data)

def setup(bot : WordleBot) -> None:
    bot.add_cog(DataService(bot))