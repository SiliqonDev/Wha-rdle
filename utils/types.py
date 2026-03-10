from typing import Any
from utils.shared_functions import flatten
from utils.logger import Logger

class Cache:
    """
    A class to allow easy creation and handling of a cache
    """
    def __init__(self, logger : Logger, initial_data : dict = {}):
        """
        Parameters
        ----------
        logger: utils.logger.Logger
            the logger object that the cache will utilise
        initial_data : dict, optional
            cache data at initialisation, `{}` if None
        """
        self._logger = logger
        self._cache = initial_data
    
    def put(self, *path : str | int | list[str | int] | tuple[str | int], key : Any, value : Any) -> None:
        """
        puts a specified key:value pair in the cache at a given path

        Parameters
        ----------
        *path : str | int | list[str|int] | tuple[str|int]
            The path inside the cache at which to insert the key:value pair.\n
            Example paths: `"my_data"`, `["previous_games", "round_data", 1]`, `("items", "legendary")`
        key : Any
            The key. Must be an immutable object
        value : Any
            The value to put.
        """
        if not path: # set at root
            self._cache[key] = value
            return None
        # support nested sequences in given path
        flatpath = flatten(path)
        # follow path
        curLoc : dict = self._cache
        try:
            for loc in flatpath:
                # account for keys in the path that do not exist
                if loc not in curLoc.keys():
                    curLoc[loc] = {}
                curLoc = curLoc[loc]  
            # successfully found location
            curLoc[key] = value  
        except Exception as e:
            self._logger.error(f"Invalid Cache.set() operation to path {path}")
            self._logger.exception(e)

    def get(self, *path : str | int | list[str | int] | tuple[str | int]) -> Any | None:
        """
        returns the value present in the cache at a given path\n
        returns whole cache if no path specified

        Parameters
        ----------
        *path : str | int | list[str|int] | tuple[str|int]
            The path inside the cache from which to return the value.\n
            Example paths: `"my_data"`, `["previous_games", "round_data", 1]`, `("items", "legendary")`
        
        Returns
        -------
        value : Any | None
            The retrieved value if any, else None
        """
        if not path: return self._cache
        # support nested sequences in given path
        flatpath = flatten(path)
        # follow path
        curLoc : dict = self._cache.copy()
        try:
            for loc in flatpath:
                # wanted key doesnt exist in cache
                if loc not in curLoc.keys():
                    return None
                curLoc = curLoc[loc]
            # successfully found
            return curLoc
        except Exception as e:
            self._logger.error(f"Invalid Cache.get() operation for path {path}")
            self._logger.exception(e)
            return None
    
    def exists(self, *path : str | int | list[str | int] | tuple[str | int]) -> bool:
        """
        checks whether any data is stored in the cache at a given path

        Parameters
        ----------
        *path : str | int | list[str|int] | tuple[str|int]
            The path inside the cache from which to return the value.\n
            Example paths: `"my_data"`, `["previous_games", "round_data", 1]`, `("items", "legendary")`
        
        Returns
        -------
        exists : bool
            True if value assigned, else False
        """
        obj : Any = self.get(*path)
        return obj is not None

class BotConfig:
    """
    a class to streamline bot configuration data access
    """
    def __init__(self, config : dict):
        """
        Parameters
        ----------
        config : dict
            The bot's config data
        """
        self.config = config
    
    def set(self, key : str, value : Any) -> None:
        self.config[key] = value
    def get(self, key : str) -> Any | None:
        if key in self.config.keys():
            return self.config[key]
        return None

class InternalData:
    """
    a class to manage data for internal use
    """
    def __init__(self,
                 gameId : int = 0,
                 answer : str = "",
                 past_words : list[str] = []
                ):
        """
        Parameters
        ----------
        gameId : int, optional
            The id of the current ongoing game or last played game
        answer : str, optional
            The answer for the current ongoing game or last played game
        past_words : list[str], optional
            A record of past game answers
        """
        self.gameId = gameId
        self.answer = answer
        self.past_words = past_words

    def getGameId(self) -> int: return self.gameId
    def getAnswer(self) -> str: return self.answer
    def getPastWords(self) -> list[str]: return self.past_words

    def setGameId(self, value : int) -> None: self.gameId = value
    def setAnswer(self, value : str) -> None: self.answer = value
    def setPastWords(self, value : list[str]) -> None: self.past_words = value

    def incrementGameId(self) -> None: self.gameId += 1
    
    def bulkUpdate(self, data : dict) -> None:
        """
        updates the values that are provided

        Parameters
        ----------
        data: dict
            The dictionary to pull data from.
            If a key exists in `data`, 
            it will update the corresponding value internally
        valid keys:  gameId, answer, past_words
        """
        
        keys = ['gameId', 'answer', 'past_words']
        # check for each key and update if present
        for key in keys:
            command = f"if '{key}' in data.keys(): self.{key} = data['{key}']"
            exec(command)

class PlayerGameData:
    """
    a class to manage the current available game data for a user
    """
    def __init__(self, userId: int, 
                 guesses : list[str] = [], 
                 completed : bool = False, 
                 won : bool = False, 
                 answer : str = ""
                ):
        """
        Parameters
        ----------
        userId : int
            The user's discord ID
        guesses : list[str], optional
            A list of guesses made in the last game
        completed : bool, optional
            Whether or not the game had ended
        won : bool, optional
            Whether or not the user had won the game
        answer: str, optional
            The correct answer in that game
        """
        self.userId = userId
        self.guesses = guesses
        self.completed = completed
        self.won = won
        self.answer = answer
    
    def getUserId(self) -> int: return self.userId
    def getGuesses(self) -> list[str]: return self.guesses
    def isCompleted(self) -> bool: return self.completed
    def isWon(self) -> bool: return self.won
    def getAnswer(self) -> str: return self.answer

    def setGuesses(self, value: list[str]) -> None: self.guesses = value
    def setCompleted(self, value: bool) -> None: self.completed = value
    def setWon(self, value : bool) -> None: self.won = value
    def setAnswer(self, value : str) -> None: self.answer = value 
    
    def bulkUpdate(self, data : dict) -> None:
        """
        updates the values that are provided

        Parameters
        ----------
        data: dict
            The dictionary to pull data from.
            If a key exists in `data`, 
            it will update the corresponding value internally
        valid keys: guesses, completed, won, answer
        """
        
        keys = ['guesses', 'completed', 'won', 'answer']
        # check for each key and update if present
        for key in keys:
            command = f"if '{key}' in data.keys(): self.{key} = data['{key}']"
            exec(command)

class PlayerStats:
    """
    a class to manage the current stats for a user
    """
    def __init__(self, userId: int, 
                 games_played : int = 0,
                 games_won : int = 0
                ):
        """
        Parameters
        ----------
        userId : int
            The user's discord ID
        games_played : int, optional
            The number of games played in total
        games_won : int, optional
            The number of games won
        """
        self.userId = userId
        self.games_played = games_played
        self.games_won = games_won
    
    def getUserId(self) -> int: return self.userId
    def getGamesPlayed(self) -> int: return self.games_played
    def getGamesWon(self) -> int: return self.games_won

    def setGamesPlayed(self, value : int) -> None: self.games_played = value
    def setGamesWon(self, value : int) -> None: self.games_won = value

    def incrementGamesPlayed(self) -> None: self.games_played += 1
    def incrementGamesWon(self) -> None: self.games_won += 1
    
    def bulkUpdate(self, data : dict) -> None:
        """
        updates the values that are provided

        Parameters
        ----------
        data: dict
            The dictionary to pull data from.
            If a key exists in `data`, 
            it will update the corresponding value internally
        valid keys: games_played, games_won
        """
        
        keys = ['games_played', 'games_won']
        # check for each key and update if present
        for key in keys:
            command = f"if '{key}' in data.keys(): self.{key} = data['{key}']"
            exec(command)