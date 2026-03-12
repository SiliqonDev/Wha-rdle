from typing import Literal, cast # shut up the typechecker
import nextcord
from nextcord import Interaction, SlashOption
from nextcord.ext.commands import Cog
from utils.types import WordleBot, Config
from cogs.services.game import GameService

class NewCommand(Cog, name="new_command"):
    """
    A command to allow admins to create and start new games for users
    """
    def __init__(self, bot : WordleBot) -> None:
        self._bot = bot
        self._config : Config = bot.config
        self._lang : Config = bot.lang
        self._game_service : GameService
    
    @Cog.listener()
    async def on_ready(self):
        await self._bot.wait_until_ready()
        self._game_service = cast(GameService, self._bot.get_cog("game_service"))
    
    @nextcord.slash_command(description=f"Create and start a new game for users", guild_ids=[948991434827128863, 1316042324727300109])
    async def testnew(self, interaction : Interaction, confirm : bool = SlashOption("override_ongoing", "Whether to terminate any ongoing games and force start a new game", default=False)):
        reply : Literal["SUCCESS", "NEED_CONFIRMATION"] = await self._game_service.initNewGame()
        if reply == "NEED_CONFIRMATION" and not confirm:
            await interaction.response.send_message(self._lang.get('confirm_override_on_new'))
            return
        await interaction.response.send_message(self._lang.get('new_game_started'), delete_after=10)

def setup(bot : WordleBot) -> None:
    bot.add_cog(NewCommand(bot))