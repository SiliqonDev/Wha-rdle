import nextcord
from nextcord import Interaction, Embed, Colour
from nextcord.ext.commands import Cog
from utils.types import WordleBot, Config

class HelpCommand(Cog, name="help_command"):
    """
    A command to allow users to see a list of commands
    """
    def __init__(self, bot : WordleBot) -> None:
        self._bot = bot
        self._config : Config = bot.config
        self._lang : Config = bot.lang
    
    @Cog.listener()
    async def on_ready(self):
        await self._bot.wait_until_ready()
    
    @nextcord.slash_command(description=f"View a list of all commands", guild_ids=[948991434827128863, 1316042324727300109])
    async def testhelp(self, interaction : Interaction):
        if interaction.user is None: return
        await interaction.response.defer(ephemeral=True)

        embed = await self.constructHelpEmbed()
        await interaction.followup.send(embed=embed, delete_after=60)

    async def constructHelpEmbed(self) -> Embed:
        
        # build body string
        body_lines = self._lang.get("help_embed_body")
        print(body_lines)
        body_string = "\n"
        for line in body_lines:
            body_string += line + "\n"

        # init embed and set stuff
        embed = Embed(title=self._lang.get('help_embed_title'), description=body_string, color=Colour.light_gray())
        footer : str | None = self._lang.get('help_embed_footer')
        embed.set_footer(text=footer)

        return embed
    
def setup(bot : WordleBot) -> None:
    bot.add_cog(HelpCommand(bot))