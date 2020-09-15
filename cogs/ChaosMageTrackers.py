# =========================================================
# Chaos Mage Tracker
# =========================================================
import random
from discord.ext import commands


def warp_element():
    return random.choice(['Air', 'Fire', 'Water', 'Earth', 'Metal', 'Void'])


class ChaosMageTracker:
    def __init__(self):
        self.mages = {}

    def reset(self):
        self.mages = {}

    def refill(self, mage_name):
        self.mages[mage_name] = ['**```ARM\nAttack\n```**', '**```ARM\nAttack\n```**',
                                 '**```yaml\nDefense\n```**', '**```yaml\nDefense\n```**',
                                 '**```CSS\nIconic\n```**', '**```CSS\nIconic\n```**']
        random.shuffle(self.mages[mage_name])

    def draw(self, mage_name):
        random.shuffle(self.mages[mage_name])
        return self.mages[mage_name].pop()


chaos_mages = ChaosMageTracker()


class ChaosMageCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name='chaos', casesensitive=False, help="Tools for Chaos Mages.  "
                                                            "Each mage's pool is tracked separately.")
    async def chaos_main(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(f"Additional arguments required, see "
                           f"**{ctx.prefix}help chaos** for available options.")

    @chaos_main.command(help="Manually fills or refills a Chaos Mage's spell determination pool.")
    async def refill(self, ctx):
        chaos_mages.refill(ctx.author.display_name)
        await ctx.send(f"{ctx.author.mention}'s spell determination pool has been refilled.")

    @chaos_main.command(help="Draw a random spell type from your spell determination pool.")
    async def draw(self, ctx):
        if ctx.author.display_name in chaos_mages.mages:
            if len(chaos_mages.mages[ctx.author.display_name]) == 2:
                spell_type = chaos_mages.draw(ctx.author.display_name)
                chaos_mages.refill(ctx.author.display_name)
                await ctx.send(f'{ctx.author.mention}, your next spell will be:'
                               f'\n{spell_type}\n'
                               f'That was your second last spell in the pool, it has automatically been refilled.')
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
        await ctx.send(f"{ctx.author.mention}, your warp element is: **{warp_element()}**")
