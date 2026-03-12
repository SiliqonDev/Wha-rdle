from typing import Any
from nextcord import TextChannel
from nextcord.ext import commands
from enum import Enum

class WordleBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config : Config
        self.lang : Config
        self.alerts_channel : TextChannel

class Config:
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
    def get(self, key : str) -> Any:
        if key in self.config.keys():
            return self.config[key]
        return None

class CurrentGameInfo:
    """
    a class to manage data for internal use
    """
    def __init__(self,
                 gameId : int = 0,
                 answer : str = "",
                 participants : list[int] = [],
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
        self.participants = participants
        self.past_words = past_words

    def getGameId(self) -> int: return self.gameId
    def getAnswer(self) -> str: return self.answer
    def getParticipants(self) -> list[int]: return self.participants
    def getPastWords(self) -> list[str]: return self.past_words

    def setGameId(self, value : int) -> None: self.gameId = value
    def setAnswer(self, value : str) -> None: self.answer = value
    def setParticipants(self, value : list[int]) -> None: self.participants = value
    def setPastWords(self, value : list[str]) -> None: self.past_words = value

    def incrementGameId(self) -> None: self.gameId += 1
    def addParticipant(self, userId) -> None:
        self.participants.append(userId)
    
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
            command = f"if '{key}' in data.keys(): self.{key} = data['{key}']"
            exec(command)

class PlayerGameData:
    """
    a class to manage the current available game data for a user
    """
    def __init__(self, userId: int, 
                 last_played_game_id : int = -1,
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
        self.last_played_game_id = last_played_game_id
        self.guesses = guesses
        self.completed = completed
        self.won = won
        self.answer = answer
    
    def getLastPlayedGameId(self) -> int: return self.last_played_game_id
    def getUserId(self) -> int: return self.userId
    def getGuesses(self) -> list[str]: return self.guesses
    def isCompleted(self) -> bool: return self.completed
    def isWon(self) -> bool: return self.won
    def getAnswer(self) -> str: return self.answer

    def setLastPlayedGameId(self, value : int) -> None: self.last_played_game_id = value
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
        valid keys: last_played_game_id, guesses, completed, won, answer
        """
        
        keys = ['last_played_game_id', 'guesses', 'completed', 'won', 'answer']
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
                 games_won : int = 0,
                 win_streak : int = 0
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
        win_streak : int, optional
            The current win streak
        """
        self.userId = userId
        self.games_played = games_played
        self.games_won = games_won
        self.win_streak = win_streak
    
    def getUserId(self) -> int: return self.userId
    def getGamesPlayed(self) -> int: return self.games_played
    def getGamesWon(self) -> int: return self.games_won
    def getWinStreak(self) -> int: return self.win_streak
    
    def setGamesPlayed(self, value : int) -> None: self.games_played = value
    def setGamesWon(self, value : int) -> None: self.games_won = value
    def setWinStreak(self, value : int) -> None: self.win_streak = value

    def incrementGamesPlayed(self) -> None: self.games_played += 1
    def incrementGamesWon(self) -> None: self.games_won += 1
    def incrementWinstreak(self) -> None: self.win_streak += 1
    def resetWinStreak(self) -> None: self.win_streak = 0
    
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
            command = f"if '{key}' in data.keys(): self.{key} = data['{key}']"
            exec(command)

class PlayerGameState(Enum):
    UNKNOWN = "UNKNOWN"
    NOT_STARTED = "NOT_STARTED"
    ONGOING = "ONGOING"
    INCOMPLETE = "INCOMPLETE"
    COMPLETED = "COMPLETED"