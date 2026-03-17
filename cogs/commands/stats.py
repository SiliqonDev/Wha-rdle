from typing import cast # shut up the typechecker
import nextcord
from nextcord import Embed, Interaction
from nextcord.ext.commands import Cog
from cogs.services.data import DataService
from utils.types import PlayerStats, WordleBot, Config

class StatsCommand(Cog, name="stats_command"):
    """
    A command to allow users to see their current stats
    """
    def __init__(self, bot : WordleBot) -> None:
        self._bot = bot
        self._config : Config = bot.config
        self._lang : Config = bot.lang
        self._data_service : DataService
    
    @Cog.listener()
    async def on_ready(self):
        await self._bot.wait_until_ready()
        self._data_service = cast(DataService, self._bot.get_cog("data_service"))
    
    @nextcord.slash_command(description=f"Create and start a new game for users", guild_ids=[948991434827128863, 1316042324727300109])
    async def teststats(self, interaction : Interaction):
        if interaction.user is None: return
        user_id = interaction.user.id
        await interaction.response.defer(ephemeral=True)

        stats : PlayerStats = await self._data_service.getPlayerStatsFor(user_id)
        played = stats.getGamesPlayed()
        won = stats.getGamesWon()
        win_rate = f"{((won/played)*100):.2f}%" if played > 0 else "N/A"
        win_streak = stats.getWinStreak()

        embed = Embed(title="Your stats")
        stats_string : str | None = self._lang.get("stats_display_format")
        if stats_string is not None:
                stats_string = stats_string.replace('{games_played}', str(played)).replace('{games_won}', str(won)).replace('{win_rate}', win_rate).replace('{win_streak}', str(win_streak))
        embed.add_field(name=str(stats_string), value="", inline=False)
        await interaction.followup.send(embed=embed, delete_after=30)  

def setup(bot : WordleBot) -> None:
    bot.add_cog(StatsCommand(bot))