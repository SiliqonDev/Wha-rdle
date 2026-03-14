from typing import cast # shut up the typechecker
import nextcord
from nextcord import Interaction, SlashOption
from nextcord.ext.commands import Cog
from cogs.services.data import DataService
from utils.game_instance import GameInstance
from utils.types import PlayerGameState, WordleBot, Config
from cogs.services.game import GameService

class GuessCommand(Cog, name="guess_command"):
    """
    A command to let users make guesses in their ongoing games
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
    
    @nextcord.slash_command(description=f"Make a guess in your current game", guild_ids=[948991434827128863, 1316042324727300109])
    async def testguess(self, interaction : Interaction, guess : str = SlashOption("guess", description="Your guess word", required=True)):
        if interaction.user is None: return
        userId : int = interaction.user.id
        await interaction.response.defer(ephemeral=True)

        game_instance : GameInstance | None = await self._game_service.getUserGameInstance(userId)
        game_state : PlayerGameState = await self._game_service.getUserGameState(userId)
        
        # no game associated with user
        if game_instance is None:
            if game_state != PlayerGameState.INCOMPLETE:
                await interaction.followup.send(self._bot.lang.get("no_active_game_found"))
            else:
                # resume past game for user
                await self._game_service.startGameFor(userId, interaction, resumed=True, silent_start=True)

                game_instance : GameInstance | None = await self._game_service.getUserGameInstance(userId)
                assert game_instance is not None
                await game_instance.processGuess(interaction, guess, await self._data_service.getAllowedGuesses())
            return
        
        # game is still starting up or is paused
        if not game_instance.ongoing:
            await interaction.followup.send(self._bot.lang.get("cannot_make_guess"))
            return
        
        # user finished the game
        if game_instance._completed:
            await interaction.followup.send(self._bot.lang.get("game_already_finished"))
            return
        
        # everything seems good
        await game_instance.processGuess(interaction, guess, await self._data_service.getAllowedGuesses())

def setup(bot : WordleBot) -> None:
    bot.add_cog(GuessCommand(bot))