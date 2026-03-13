from typing import Any
from nextcord import TextChannel
from nextcord.ext import commands
from enum import Enum

class WordleBot(commands.Bot):
    """
    Wordle bot instance

    Properties
    ----------
    config : utils.types.Config
        The bot config to use
    lang : utils.types.Config
        The lang data to use
    alerts_channel : nextcord.TextChannel
        The channel to send all alerts to
    image_res_factor : int
        The factor by which to multiply all images' resolutions
    avatar_cache: dict
        A cache to store player avatar images to avoid fetching every time
    misc_data : dict
        A way to store any misc data
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config : Config
        self.lang : Config
        self.alerts_channel : TextChannel
        self.image_res_factor : int = 1
        self.avatar_cache : dict = {}
        self.misc_data : dict = {}

class Config:
    """
    a class to streamline bot configuration data access

    Parameters
    ----------
    config : dict
        The bot's config data
    """
    def __init__(self, config : dict):
        self._config = config
    
    def set(self, key : str, value : Any) -> None:
        self._config[key] = value
    def get(self, key : str) -> Any:
        if key in self._config.keys():
            return self._config[key]
        return None

class CurrentGameInfo:
    """
    a class to manage data for internal use

    Parameters
    ----------
    gameId : int, optional
        The id of the current ongoing game or last played game
    answer : str, optional
        The answer for the current ongoing game or last played game
    participants: list[int], optional
        A list of user IDs of users that have played this game
    past_words : list[str], optional
        A record of past game answers
    """
    def __init__(self,
                 gameId : int = 0,
                 answer : str = "",
                 participants : list[int] = [],
                 past_words : list[str] = []
                ):
        self._gameId = gameId
        self._answer = answer
        self._participants = participants
        self._past_words = past_words

    def getGameId(self) -> int: return self._gameId
    def getAnswer(self) -> str: return self._answer
    def getParticipants(self) -> list[int]: return self._participants
    def getPastWords(self) -> list[str]: return self._past_words

    def setGameId(self, value : int) -> None: self._gameId = value
    def setAnswer(self, value : str) -> None: self._answer = value
    def setParticipants(self, value : list[int]) -> None: self._participants = value
    def resetParticipants(self) -> None: self._participants = []
    def setPastWords(self, value : list[str]) -> None: self._past_words = value

    def incrementGameId(self) -> None: self._gameId = max(0, self._gameId+1)
    def addParticipant(self, userId : int) -> None:
        if self.hasParticipant(userId): return
        self._participants.append(userId)
    def hasParticipant(self, userId : int) -> bool: return userId in self._participants
    
    def bulkUpdate(self, data : dict) -> None:
        """
        updates the values that are provided

        Parameters
        ----------
        data: dict
            The dictionary to pull data from.
            If a key exists in `data`, 
            it will update the corresponding value internally
        valid keys:  gameId, answer, participants, past_words
        """
        
        keys = ['gameId', 'answer', 'participants', 'past_words']
        # check for each key and update if present
        for key in keys:
            command = f"if '{key}' in data.keys(): self._{key} = data['{key}']"
            exec(command)

class PlayerGameData:
    """
    a class to manage the current available game data for a user

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
    def __init__(self, userId: int, 
                 last_played_game_id : int = -1,
                 guesses : list[str] = [], 
                 completed : bool = False, 
                 won : bool = False, 
                 answer : str = ""
                ):
        self._userId = userId
        self._last_played_game_id = last_played_game_id
        self._guesses = guesses
        self._completed = completed
        self._won = won
        self._answer = answer
    
    def getLastPlayedGameId(self) -> int: return self._last_played_game_id
    def getUserId(self) -> int: return self._userId
    def getGuesses(self) -> list[str]: return self._guesses
    def isCompleted(self) -> bool: return self._completed
    def isWon(self) -> bool: return self._won
    def getAnswer(self) -> str: return self._answer

    def setLastPlayedGameId(self, value : int) -> None: self._last_played_game_id = value
    def setGuesses(self, value: list[str]) -> None: self._guesses = value
    def setCompleted(self, value: bool) -> None: self._completed = value
    def setWon(self, value : bool) -> None: self._won = value
    def setAnswer(self, value : str) -> None: self._answer = value 
    
    def bulkUpdate(self, data : dict) -> None:
        """
        updates the values that are provided

        Parameters
        ----------
        data: dict
            The dictionary to pull data from.
            If a key exists in `data`, 
            it will update the corresponding value internally
        valid keys: last_played_game_id, guesses, completed, won, answer
        """
        
        keys = ['last_played_game_id', 'guesses', 'completed', 'won', 'answer']
        # check for each key and update if present
        for key in keys:
            command = f"if '{key}' in data.keys(): self._{key} = data['{key}']"
            exec(command)

class PlayerStats:
    """
    A class to store and manage the current stats of a user
    
    Parameters
    ----------
    userId : int
        The user's discord ID
    games_played : int, optional
        The number of games played in total
    games_won : int, optional
        The number of games won
    win_streak : int, optional
        The current win streak
    """
    def __init__(self, 
                 userId: int, 
                 games_played : int = 0,
                 games_won : int = 0,
                 win_streak : int = 0
                ):
        self._userId = userId
        self._games_played = games_played
        self._games_won = games_won
        self._win_streak = win_streak
    
    def getUserId(self) -> int: return self._userId
    def getGamesPlayed(self) -> int: return self._games_played
    def getGamesWon(self) -> int: return self._games_won
    def getWinStreak(self) -> int: return self._win_streak
    
    def setGamesPlayed(self, value : int) -> None: self._games_played = value
    def setGamesWon(self, value : int) -> None: self._games_won = value
    def setWinStreak(self, value : int) -> None: self._win_streak = value
    def resetWinStreak(self) -> None: self._win_streak = 0
    
    def incrementGamesPlayed(self) -> None: self._games_played = max(0, self._games_played + 1)
    def incrementGamesWon(self) -> None: self._games_won = max(0, self._games_won + 1)
    def incrementWinstreak(self) -> None: self._win_streak = max(0, self._win_streak + 1)
    
    def bulkUpdate(self, data : dict) -> None:
        """
        updates the values that are provided

        Parameters
        ----------
        data: dict
            The dictionary to pull data from.
            If a key exists in `data`, 
            it will update the corresponding value internally
        valid keys: games_played, games_won, win_streak
        """
        
        keys = ['games_played', 'games_won', 'win_streak']
        # check for each key and update if present
        for key in keys:
            command = f"if '{key}' in data.keys(): self._{key} = data['{key}']"
            exec(command)

class PlayerGameState(Enum):
    UNKNOWN = "UNKNOWN"
    NOT_STARTED = "NOT_STARTED" # hasnt started current game
    ONGOING = "ONGOING" # is playing current game
    INCOMPLETE = "INCOMPLETE" # started current game but didnt finish
    COMPLETED = "COMPLETED" # already played current game