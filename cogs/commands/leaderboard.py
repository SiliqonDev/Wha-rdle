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
        embed = Embed(title=f"{self._bot.lang.get('bot_display_name')} Leaderboard", color=Colour.gold())
        for i in range(len(sorted_players)):
            data = sorted_players[i]
            id = data[0]
            stats : PlayerStats = data[1]
            user = self._bot.get_user(id)
            assert user is not None

            played = stats.getGamesPlayed()
            won = stats.getGamesWon()
            win_rate = f"{(played/won)*100}%" if won > 0 else "N/A"
            streak = stats.getWinStreak()
            embed.add_field(name=f"**#{i+1}** {user.display_name}",
                             value=f"{played} Played **/** {won} Won **/** {win_rate} WR **/** {streak} Streak", inline=False)  
        # there was no one
        if len(sorted_players) == 0:
            embed.add_field(name="No data available.", value="*No like seriously, there isn't any.*", inline=False)
        embed.add_field(name="",value="",inline=False) # spacer
        embed.set_footer(text="you guys are really bad at this huh")

        await interaction.followup.send(embed=embed)

def setup(bot : WordleBot) -> None:
    bot.add_cog(LeaderboardCommand(bot))