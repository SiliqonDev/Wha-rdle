# epic tower of imports
import pickle
from typing import Any
from nextcord.ext import tasks
from nextcord.ext.commands import Cog
from pathlib import Path
from data.interface import DBInterface
from utils.types import WordleBot, Config, PlayerGameData, PlayerStats, CurrentGameInfo
from utils.utils import Logger, Cache

class DataService(Cog, name="data_service"):
    """
    A service to manage all data related to players and games
    """
    def __init__(self, bot : WordleBot) -> None:
        self._bot = bot
        self._config : Config = bot.config

        # logger
        self._log_file_path = self._config.get('log_file_path')
        assert self._log_file_path is not None
        self._logger = Logger("DataService", self._log_file_path, debug_mode=self._config.get('debug_mode'))

    async def initService(self) -> None:
        """
        Connects to the database and builds the cache
        """
        self._cwd = self._config.get('cwd')
        assert self._cwd is not None

        self._cache = Cache(logger=self._logger, initial_data={
            "player_game_data": {},
            "player_stats": {},
            "current_game_info": CurrentGameInfo()
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
        
        self._logger.debug("Started up successfully.", printToConsole=True)
        
        await self._makeDirectories()
        await self._buildCache()
        # all done and dusted
        self._logger.debug("Cache initialised", printToConsole=True)
    
    @tasks.loop(seconds=60)
    async def _autosave(self) -> None:
        """
        autosaves data to protect against crashes
        """
        self._logger.info("Beginning autosave.")
        await self._savePlayerGameData()
        await self._savePlayerStats()
        await self._saveCurrentGameInfo()
        self._logger.info("Autosave completed.")

    async def _buildCache(self) -> None:
        """
        executes necessary methods to cache all available data
        """
        await self._cacheWordList()
        await self._cachePlayerGameData()
        await self._cachePlayerStats()
        await self._cacheCurrentGameInfo()
        
        # all done
        self._autosave.start()

    async def _makeDirectories(self) -> None:
        """
        initialises important directories if they do not exist.
        """
        Path(f"{self._cwd}/temp").mkdir(parents=True, exist_ok=True)
        Path(f"{self._cwd}/logs").mkdir(parents=True, exist_ok=True)
    
    async def registerUser(self, userId : int) -> None:
        """
        Sets up default data for a new user in the database\n
        Does nothing if user already exists in database

        Parameters
        ----------
        userId : int
            The user to register
        """
        if self.userExists(userId): return
        # save default data
        data = PlayerGameData(userId)
        stats = PlayerStats(userId)
        self._cache.put('player_game_data', key=userId, value=data)
        self._cache.put('player_stats', key=userId, value=stats)
        await self._savePlayerGameDataFor(userId, data)
        await self._savePlayerStatsFor(userId, stats)
    
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

    async def getAllowedGuesses(self) -> list:
        words : Any = self._cache.get(['word_list', 'allowed_guesses'])
        return words
    
    async def getPossibleAnswers(self) -> list:
        words : Any = self._cache.get(['word_list', 'possible_answers'])
        return words

    async def getPlayerGameData(self) -> dict[int, PlayerGameData]:
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
    
    async def getPlayerGameDataFor(self, userId : int) -> PlayerGameData:
        """
        returns the PlayerGameData object for a user

        Parameters
        ----------
        userId: int
            The user's discord ID

        Returns
        -------
        data: utils.types.PlayerGameData
            The data associated with the user
        """
        user_data : PlayerGameData | None = self._cache.get(['player_game_data', userId])
        if not user_data:
            await self.registerUser(userId)
            user_data : PlayerGameData | None = self._cache.get(['player_game_data', userId])
        assert user_data is not None
        return user_data
    
    async def getPlayerStats(self) -> dict[int, PlayerStats]:
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
    
    async def getPlayerStatsFor(self, userId : int) -> PlayerStats:
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
        if not user_stats:
            await self.registerUser(userId)
            user_stats : PlayerStats | None = self._cache.get(['player_stats', userId])
        assert user_stats is not None
        return user_stats

    async def getCurrentGameInfo(self) -> CurrentGameInfo:
        """
        returns the CurrentGameInfo object for the bot

        Returns
        ----------
        data: utils.types.CurrentGameInfo
            The data object
        """
        data = self._cache.get('current_game_info')
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

    def setCurrentGameInfo(self, data : CurrentGameInfo) -> None:
        """
        sets the bot's CurrentGameInfo object

        Parameters
        ----------
        data: utils.types.CurrentGameInfo
            the new CurrentGameInfo object
        """
        self._cache.put(key='current_game_info',value=data)

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
    async def _savePlayerGameData(self, data : dict[int, PlayerGameData] | None = None) -> None:
        """
        Saves the game data of all given players

        Parameters
        ----------
        data: dict[int, utils.types.PlayerGameData] | None, optional
            The data to save, grabs from cache if not specified.
        """
        if not data:
            data = self._cache.get('player_game_data')
            assert data is not None

        for userId, pdata in data.items():
            await self._savePlayerGameDataFor(userId, pdata, commit=False)
        # bulk commit everything
        await self._db_interface.commit()
    async def _savePlayerGameDataFor(self, userId : int, data : PlayerGameData, commit : bool | None = True) -> None:
        """
        Saves given player game data for a specific user

        Parameters
        ----------
        userId: int
            The user to save the data for
        data: utils.types.PlayerGameData
            The data to save
        commit: boolean, optional
            Whether to commit the data to the database right away
        """
        last_played_game_id : int = data.getLastPlayedGameId()
        guesses : bytes = pickle.dumps(data.getGuesses())
        completed : bool = data.isCompleted()
        won : bool = data.isWon()
        answer : str = data.getAnswer()
        # insert if new, else update
        await self._db_interface.execute("INSERT INTO player_game_data (userId, last_played_game_id, guesses, completed, won, answer) "\
                                        "values(?,?,?,?,?,?) ON CONFLICT(userId) DO UPDATE SET "\
                                        "last_played_game_id=excluded.last_played_game_id, guesses=excluded.guesses, completed=excluded.completed, won=excluded.won, answer=excluded.answer",
                                        userId, last_played_game_id, guesses, completed, won, answer)
        if commit: await self._db_interface.commit()
    
    async def _savePlayerStats(self, data : dict[int, PlayerStats] | None = None) -> None:
        """
        Saves the stats of all given players

        Parameters
        ----------
        data: dict[int, utils.types.PlayerStats] | None, optional
            The stats to save, grabs from cache if not specified.
        """
        if not data:
            data = self._cache.get('player_stats')
            assert data is not None
        
        for userId, stats in data.items():
            await self._savePlayerStatsFor(userId, stats, commit=False)
        # bulk commit everything
        await self._db_interface.commit()
    async def _savePlayerStatsFor(self, userId : int, stats : PlayerStats, commit : bool | None = False) -> None:
        """
        Saves given player stats for a specific user

        Parameters
        ----------
        userId: int
            The user to save the data for
        stats: utils.types.PlayerStats
            The stats to save
        commit: boolean, optional
            Whether to commit the data to the database right away
        """
        games_played : int = stats.getGamesPlayed()
        games_won : int = stats.getGamesWon()
        win_streak : int = stats.getWinStreak()
        # insert if new, else update
        await self._db_interface.execute("INSERT INTO player_stats (userId, games_played, games_won, win_streak) "\
                                        "values(?,?,?, ?) ON CONFLICT DO UPDATE SET "\
                                        "games_played=excluded.games_played, games_won=excluded.games_won, win_streak=excluded.win_streak",
                                        userId, games_played, games_won, win_streak)
        if commit: await self._db_interface.commit()
    
    async def _saveCurrentGameInfo(self, data : CurrentGameInfo | None = None) -> None:
        """
        Saves the current game info of the bot

        Parameters
        ----------
        data: dict[int, utils.types.CurrentGameInfo] | None, optional
            The data to save, grabs from cache if not specified.
        """
        if not data:
            data = self._cache.get('current_game_info')
            assert data is not None

        # save
        gameId : int = data.getGameId()
        answer : str = data.getAnswer()
        participants : bytes = pickle.dumps(data.getParticipants())
        past_words : bytes = pickle.dumps(data.getPastWords())

        # insert if doesn't exist, else update
        await self._db_interface.execute("INSERT INTO current_game_info (_id, gameId, answer, participants, past_words) "\
                                        "values(0, ?, ?, ?, ?) "\
                                        "ON CONFLICT(_id) DO UPDATE SET "\
                                        "gameId=excluded.gameId, answer=excluded.answer, participants=excluded.participants, past_words=excluded.past_words", 
                                        gameId, answer, participants, past_words)
        await self._db_interface.commit()

    ###
    ### CACHING
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
            userId, games_played, games_won, win_streak = record
            pstats = PlayerStats(userId, games_played, games_won, win_streak)

            self._cache.put('player_stats', key=userId, value=pstats)
    
    async def _cacheCurrentGameInfo(self):
        """
        grabs all available current game info from the database and caches it
        """
        reply = await self._db_interface.record("SELECT * FROM current_game_info WHERE _id=0")
        if reply is None:
            # initial data was not created
            await self._saveCurrentGameInfo()
            await self._cacheCurrentGameInfo()
            return
        
        _, gameId, answer, participants, past_words = reply
        data = CurrentGameInfo(gameId, answer, pickle.loads(participants), pickle.loads(past_words))
        self._cache.put(key='current_game_info', value=data)

def setup(bot : WordleBot) -> None:
    bot.add_cog(DataService(bot))