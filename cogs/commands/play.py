from typing import cast
from nextcord.ext.commands import Cog
from utils.types import WordleBot, BotConfig
from cogs.services.game import GameService

class PlayCommand(Cog, name="play_command"):
    """
    A command to let users start a new game of wordle
    """
    def __init__(self, bot : WordleBot) -> None:
        self._bot = bot
        self._config : BotConfig = bot.config
        self._game_service : GameService = cast(GameService, bot.get_cog("data_service"))