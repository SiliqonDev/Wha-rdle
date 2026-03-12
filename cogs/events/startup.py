from nextcord.ext.commands import Cog
from typing import cast # use of cast is to make the typechecker happy
from cogs.services.game import GameService
from utils.types import WordleBot, Config
from utils.utils import Logger
from cogs.services.data import DataService

class StartupEvent(Cog, name="startup_events"):
    """
    An event listener to do necessary stuff on bot startup
    """
    def __init__(self, bot : WordleBot) -> None:
        self._bot : WordleBot = bot
        self._config : Config = bot.config
        
        # logger
        self._log_file_path : str | None = self._config.get('log_file_path')
        assert self._log_file_path is not None
        self._logger = Logger("Startup", self._log_file_path)
    
    @Cog.listener()
    async def on_ready(self):
        self._logger.info("Starting up!", printToConsole=True)

        # manually init services that need it
        data_service : DataService = cast(DataService, self._bot.get_cog("data_service"))
        await data_service.initService()
        game_service : GameService = cast(GameService, self._bot.get_cog("game_service"))
        await game_service.initService()

        self._logger.info(f"Started bot as {self._bot.user}", printToConsole=True)
    
def setup(bot : WordleBot) -> None:
    bot.add_cog(StartupEvent(bot))