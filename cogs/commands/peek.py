import io
from typing import cast # shut up the typechecker
import nextcord
from nextcord import File, Interaction
from nextcord.ext.commands import Cog
from cogs.services.data import DataService
from utils.shared_functions import createResultsEmbed, getUserResultsImageBytes
from utils.types import PlayerGameData, PlayerGameState, WordleBot, Config
from cogs.services.game import GameService

class PeekCommand(Cog, name="peek_command"):
    """
    A command to allow users to see their progress in the current game
    """
    def __init__(self, bot : WordleBot) -> None:
        self._bot = bot
        self._config : Config = bot.config
        self._lang : Config = bot.lang
        self._game_service : GameService
        self._data_service : DataService
    
    @Cog.listener()
    async def on_ready(self):
        await self._bot.wait_until_ready()
        self._game_service = cast(GameService, self._bot.get_cog("game_service"))
        self._data_service = cast(DataService, self._bot.get_cog("data_service"))
    
    @nextcord.slash_command(description=f"Peek your progress in the current game", guild_ids=[948991434827128863, 1316042324727300109])
    async def testpeek(self, interaction : Interaction):
        if interaction.user is None: return
        user_id : int = interaction.user.id
        await interaction.response.defer(ephemeral=True)

        # check for associated game
        pending_game_info : tuple[bool, PlayerGameState] = await self._game_service.userHasPendingGame(user_id)
        if not pending_game_info[0]:
            await interaction.followup.send(self._bot.lang.get("no_active_game_found"), delete_after=10)
            return
        game_data : PlayerGameData = await self._data_service.getPlayerGameDataFor(user_id)

        # grab result image
        result_image_buffer : io.BytesIO = await getUserResultsImageBytes(self._bot, game_data.getGuesses(), game_data.getAnswer())
        image_file = File(fp=result_image_buffer, filename="results.webp")

        # send complete embed
        embed = createResultsEmbed(game_data.getLastPlayedGameId(), game_data.isCompleted(), game_data.isWon(), game_data.getAnswer())
        embed.set_image(url=f"attachment://results.webp")
        await interaction.followup.send(embed=embed, file=image_file, delete_after=30)
        

def setup(bot : WordleBot) -> None:
    bot.add_cog(PeekCommand(bot))