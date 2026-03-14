import random
from typing import Literal, cast # use of cast is to make the typechecker happy
from nextcord import Colour, Embed, Interaction, TextChannel
from nextcord.ext.commands import Cog
from nextcord.ext import tasks
from utils.game_instance import GameInstance
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
    
    @tasks.loop(seconds=5)
    async def cleanup_loop(self):
        """
        Cleans up all finished games
        """
        for userId, instance in self._active_games.items():
            if instance.finished:
                del self._active_games[userId]

    async def initService(self) -> None:
        """
        Activate the game service
        """
        self._active_games : dict[int, GameInstance] = {}
        self._current_game_info : CurrentGameInfo = await self._data_service.getCurrentGameInfo()
        self.cleanup_loop.start()

        # setup done
        self._logger.debug("Started up successfully.")
    
    async def initNewGame(self, terminate_ongoing : bool = False, silent : bool = False) -> Literal["SUCCESS", "NEED_CONFIRMATION"]:
        """
        Creates a new game for users to play

        Parameters
        ----------
        terminate_ongoing : bool, optional
            Whether to terminate any ongoing games and force start a new one.
            Requests confirmation if True, else directly starts new game
        silent : bool, optional
            Whether to send an alert about the game ending, alongside final results. 
            False by default
        
        Returns
        -------
        result: Literal["SUCCESS", "NEED_CONFIRMATION"]
            "NEED_CONFIRMATION" if confirmation needed to terminate ongoing games, else "SUCCESS"
        """
        if (len(self._active_games) > 0) and (not terminate_ongoing):
            return "NEED_CONFIRMATION"
        
        # terminate all current instances
        for _, instance in self._active_games.items():
            await instance.terminate(self._bot.lang.get("game_terminated_description"))
        self._active_games.clear()

        # send out an alert
        if not silent:
            embed : Embed = await self._getGameEndEmbed()
            alerts_channel : TextChannel = self._bot.alerts_channel
            await alerts_channel.send(embed=embed)

        # set new game data
        answer : str = random.choice(await self._data_service.getPossibleAnswers())
        answer = answer.upper()
        
        self._current_game_info.setAnswer(answer)
        self._current_game_info.incrementGameId()
        self._current_game_info.resetParticipants()
    
        return "SUCCESS"

    async def startGameFor(self, userId : int, interaction : Interaction, resumed : bool = False, silent_start : bool = False) -> None:
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
            Resume the last played game (if same as current) if True, else start new
        """
        self._logger.debug(f"Attempting to start game for {userId}.")
        await interaction.followup.send(self._bot.lang.get("opening_game"))

        plr_game : PlayerGameData = await self._data_service.getPlayerGameDataFor(userId)
        plr_stats : PlayerStats = await self._data_service.getPlayerStatsFor(userId)

        # if resuming current game, account for past guesses
        starting_guesses = []
        if resumed and (userId in self._current_game_info.getParticipants()):
            self._logger.debug(f"Acknowledge resumed game for {userId}.")
            starting_guesses = plr_game.getGuesses()

        # assign instance and begin game    
        instance = GameInstance(self._bot, self._logger, interaction, 
                                plr_game, plr_stats, 
                                self._current_game_info.getGameId(), self._current_game_info.getAnswer(), 
                                starting_guesses, resumed, silent_start)
        self._active_games[userId] = instance
        self._current_game_info.addParticipant(userId)
        await instance.initGame()
        self._logger.debug(f"Game instance setup for {userId}.")
    
    async def getUserGameInstance(self, userId : int) -> GameInstance | None:
        """
        Returns the game instance associated with a user, if any

        Returns
        -------
        instance: utils.game_instance.GameInstance | None
            The instance associated with the user, if any
        """
        if userId not in self._active_games.keys(): return None
        return self._active_games[userId]
    
    async def getUserGameState(self, userId : int) -> PlayerGameState:
        """
        Returns the current game state for a specific user

        Parameters
        -------
        userId : int
            The discord ID of the user to check for
        
        Returns
        -------
        game_state: utils.types.PlayerGameState
            The current game state for the user
        """
        existing_game : bool = (userId in self._active_games.keys()) and (self._active_games[userId] is not None)
        if existing_game:
            return PlayerGameState.ONGOING # active game instance
        
        # check state against game data
        plr_game : PlayerGameData = await self._data_service.getPlayerGameDataFor(userId)

        if plr_game.getLastPlayedGameId() != self._current_game_info.getGameId():
            return PlayerGameState.NOT_STARTED
        if not plr_game.isCompleted():
            return PlayerGameState.INCOMPLETE
        elif plr_game.isCompleted():
            return PlayerGameState.COMPLETED
        return PlayerGameState.UNKNOWN # something went wrong
    
    async def _getGameEndEmbed(self) -> Embed:
        """
        Creates an embed with full user results for when a game ends

        Returns
        -------
        embed : nextcord.Embed
            The embed
        """
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
                text = self._lang.get('user_did_not_finish_game').replace('{user_id}', str(userId))
            else:
                result = self._lang.get('won') if pdata.isWon() else self._lang.get('lost')
                text = self._lang.get('user_result_text').replace('{user_id}', str(userId)).replace('{result}', result).replace('{move_count}', f'{len(pdata.getGuesses())}')
            lines += text+"\n"
        embed.add_field(name=self._lang.get('game_results_title'), value=lines, inline=False)
        embed.add_field(name="", value=f"*{self._lang.get('new_game_started')}*", inline=False)

        return embed

def setup(bot : WordleBot) -> None:
    bot.add_cog(GameService(bot))