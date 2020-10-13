""" Cog containing commands for assisting Chaos Mages."""
import random
from discord.ext import commands


def warp_element():
    """Returns random element for use inC Chaos spells."""
    return random.choice(['Air', 'Fire', 'Water', 'Earth', 'Metal', 'Void'])


def iconic_type():
    """Returns one of 12 different Icons."""
    return random.choice(['Priestess', 'Crusader', 'Archmage', 'High Druid', 'Elf Queen', 'Diabolist',
                          'Dwarf King', 'Great Gold Wyrm', 'The Three', 'Prince of Shadows',
                          'Lich King', 'Orc Lord'])


class ChaosMageTracker:
    """Class containing the items being tracked and their manipulation."""
    def __init__(self):
        self.mages = {}

    def reset(self):
        """Resets the dictionary for the enacting person to blank."""
        self.mages = {}

    def refill(self, mage_name):
        """Refills the dictionary of an enacting person with the max number of entries."""
        self.mages[mage_name] = ['**```ARM\nAttack\n```**', '**```ARM\nAttack\n```**',
                                 '**```yaml\nDefense\n```**', '**```yaml\nDefense\n```**',
                                 f'**```CSS\nIconic\nIcon: {iconic_type()}\n```**',
                                 f'**```CSS\nIconic\nIcon: {iconic_type()}\n```**']
        random.shuffle(self.mages[mage_name])

    def draw(self, mage_name):
        """draw: Pops a value from the dictionary of an enacting person."""
        random.shuffle(self.mages[mage_name])
        return self.mages[mage_name].pop()


chaos_mages = ChaosMageTracker()


class ChaosMageCommands(commands.Cog, name="Chaos Mage Commands"):
    """Class definition for the Discord Cog controlling the Chaos Mage commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(name='chaos', casesensitive=False,
                    help="Tools for Chaos Mages.  Each mage's pool is tracked separately.")
    async def chaos_main(self, ctx):
        """Command grouping all Chaos Mage commands.
        Returns error to the channel is command is incomplete."""
        if ctx.invoked_subcommand is None:
            await ctx.send(f"Additional arguments required, see "
                           f"**{ctx.prefix}help chaos** for available options.")

    @chaos_main.command(help="Manually fills or refills a Chaos Mage's spell determination pool.")
    async def refill(self, ctx):
        """Command to refill the enacting user's pool."""
        chaos_mages.refill(ctx.author.display_name)
        await ctx.send(f"{ctx.author.mention}'s spell determination pool has been refilled.")

    @chaos_main.command(help="Draw a random spell type from your spell determination pool.")
    async def draw(self, ctx):
        """Command to draw a spell type of the enacting user's pool."""
        if ctx.author.display_name in chaos_mages.mages:
            if len(chaos_mages.mages[ctx.author.display_name]) == 2:
                spell_type = chaos_mages.draw(ctx.author.display_name)
                chaos_mages.refill(ctx.author.display_name)
                await ctx.send(f'{ctx.author.mention}, your next spell will be:'
                               f'\n{spell_type}\n'
                               f'That was your second last spell in the pool, '
                               f'it has automatically been refilled.')
            else:
                await ctx.send(f'{ctx.author.mention}, your next spell will be:'
                               f'\n{chaos_mages.draw(ctx.author.display_name)}')
        else:
            chaos_mages.refill(ctx.author.display_name)
            await ctx.send(f"{ctx.author.mention}'s pool was empty and has been filled. "
                           f"Your next spell will be:"
                           f'\n{chaos_mages.draw(ctx.author.display_name)}')

    @chaos_main.command(help='Determine warp element if you have the Warp Talents.')
    async def warp(self, ctx):
        """Command calls warp_element function to return random element."""
        await ctx.send(f"{ctx.author.mention}, your warp element is: **{warp_element()}**")


def setup(bot):
    """Discord module required setup for Cog loading."""
    bot.add_cog(ChaosMageCommands(bot))
