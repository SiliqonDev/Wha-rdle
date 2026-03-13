from typing import cast # shut up the typechecker
import nextcord
from nextcord import Interaction
from nextcord.ext.commands import Cog
from utils.types import WordleBot, Config, PlayerGameState
from cogs.services.game import GameService

class PlayCommand(Cog, name="play_command"):
    """
    A command to let users start a new game
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
    
    @nextcord.slash_command(description=f"Starting playing a new game", guild_ids=[948991434827128863, 1316042324727300109])
    async def testplay(self, interaction : Interaction):
        if interaction.user is None: return
        userId : int = interaction.user.id

        game_state : PlayerGameState = await self._game_service.getUserGameState(userId)

        match game_state:
            case PlayerGameState.ONGOING:
                await interaction.response.send_message(self._lang.get("game_already_ongoing"), delete_after=10, ephemeral=True)
            case PlayerGameState.UNKNOWN:
                await interaction.response.send_message(self._lang.get("frontend_error"), delete_after=10, ephemeral=True)
            case PlayerGameState.INCOMPLETE:
                await interaction.response.send_message(self._lang.get("game_already_ongoing"), delete_after=10, ephemeral=True)
            case PlayerGameState.COMPLETED:
                await interaction.response.send_message(self._lang.get("game_already_completed"), delete_after=10, ephemeral=True)
            case PlayerGameState.NOT_STARTED:
                await interaction.response.defer(ephemeral=True)
                await self._game_service.startGameFor(userId, interaction, resume=False)

def setup(bot : WordleBot) -> None:
    bot.add_cog(PlayCommand(bot))