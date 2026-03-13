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
        """
        Allowes a user to start playing a game. Resumes past game if incomplete and matches with current live game
        """
        if interaction.user is None: return
        userId : int = interaction.user.id
        await interaction.response.defer(ephemeral=True)

        game_state : PlayerGameState = await self._game_service.getUserGameState(userId)
        match game_state:
            case PlayerGameState.ONGOING:
                await interaction.followup.send(self._lang.get("game_already_ongoing"), delete_after=10)
            case PlayerGameState.UNKNOWN:
                await interaction.followup.send(self._lang.get("frontend_error"), delete_after=10)
            case PlayerGameState.INCOMPLETE:
                # resume past game for user
                await self._game_service.startGameFor(userId, interaction, resumed=True, silent_start=False)
            case PlayerGameState.COMPLETED:
                await interaction.followup.send(self._lang.get("game_already_completed"), delete_after=10)
            case PlayerGameState.NOT_STARTED:
                # start new game for user
                await self._game_service.startGameFor(userId, interaction, resumed=False, silent_start=False)

def setup(bot : WordleBot) -> None:
    bot.add_cog(PlayCommand(bot))