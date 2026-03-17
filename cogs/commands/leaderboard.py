from typing import cast # shut up the typechecker
import nextcord
from nextcord import Colour, Embed, Interaction
from nextcord.ext.commands import Cog
from utils.types import PlayerStats, WordleBot, Config
from cogs.services.game import GameService

class LeaderboardCommand(Cog, name="leaderboard_command"):
    """
    A command to allow users to view a leaderboard of everyones stats
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
    
    @nextcord.slash_command(description=f"View a leaderboard of everyone's stats", guild_ids=[948991434827128863, 1316042324727300109])
    async def testleaderboard(self, interaction : Interaction):
        await interaction.response.defer()

        sorted_players : list[tuple[int, PlayerStats]] = await self._game_service.getUsersSortedByStats()

        # setup full embed
        title : str | None = self._lang.get('leaderboard_embed_title')
        if title is not None:
            title = title.replace('{bot_display_name}', self._lang.get('bot_display_name'))
        embed = Embed(title=title, color=Colour.gold())
        for i in range(len(sorted_players)):
            data = sorted_players[i]
            id = data[0]
            stats : PlayerStats = data[1]
            user = self._bot.get_user(id)
            assert user is not None

            played = stats.getGamesPlayed()
            won = stats.getGamesWon()
            win_rate = f"{((won/played)*100):.2f}%" if played > 0 else self._lang.get('win_rate_not_available')
            win_streak = stats.getWinStreak()

            stats_string : str | None = self._lang.get("stats_display_format")
            if stats_string is not None:
                stats_string = stats_string.replace('{games_played}', str(played)).replace('{games_won}', str(won)).replace('{win_rate}', win_rate).replace('{win_streak}', str(win_streak))
            embed.add_field(name=f"**#{i+1}** {user.display_name}", value=str(stats_string), inline=False)  
        # there was no one
        if len(sorted_players) == 0:
            embed.add_field(name=self._lang.get("leaderboard_no_data_title"), value=f"*{self._lang.get("leaderboard_no_data_description")}*", inline=False)
        embed.add_field(name="",value="",inline=False) # spacer
        embed.set_footer(text=self._lang.get("leaderboard_embed_footer"))

        await interaction.followup.send(embed=embed)

def setup(bot : WordleBot) -> None:
    bot.add_cog(LeaderboardCommand(bot))