"""Cog containing commands for dice rolling."""
import re
import random
import os
import discord
from discord.ext import commands, tasks
from soulbot import bot_config

# Select import of appropriate die roll module based on config.
if bot_config['dice_roller'] == "random_org":
    if bot_config['random_org_key']:
        from random_org_dice import die_roll
    else:
        from default_dice import die_roll
        print('No API key for Random.org configured in soulbot.conf, using default dice roller function.')
elif bot_config['dice_roller'] == "array":
    from array_dice import die_roll, rand_arrays
else:
    from default_dice import die_roll


def deck_embed_template(image_file: str):
    """Card Draw embed template."""
    embed_template = discord.Embed(title="You drew:",
                                   color=0xff0000)
    embed_template.set_image(url=f'attachment://{image_file}')
    return embed_template


class DiceRoller(commands.Cog, name="Dice Roller"):
    """Class definition for DiceRoller Cog."""
    def __init__(self, bot):
        self.bot = bot
        if bot_config['dice_roller'] == "array":
            self.rand_arrays = rand_arrays
        self.card_list = {guild.id: [] for guild in bot.guilds}
        self.active_deck = {guild.id: "" for guild in bot.guilds}
        self.deck_list = os.listdir('./data/decks')

    @commands.command(help="Dice roller.  Expected format: NdN+N.(Ex: 2d6+2)")
    async def roll(self, ctx, *, dice_roll: str):
        plus_modifier_pattern = "[0-9]+d[0-9]+\\+[0-9]+"
        minus_modifier_pattern = "[0-9]+d[0-9]+\\-[0-9]+"
        normal_pattern = "[0-9]+d[0-9]+"
        if re.fullmatch(plus_modifier_pattern, dice_roll):
            modifier = int(dice_roll.split("+")[1])
            dice = dice_roll.split("+")[0]
            result_list, result_total = die_roll(int(dice.split("d")[0]), int(dice.split("d")[1]))
            await ctx.send(f"{ctx.author.mention} rolled **{result_total + modifier}**."
                           f" ({result_list}+{modifier})")
        elif re.fullmatch(minus_modifier_pattern, dice_roll):
            modifier = int(dice_roll.split("-")[1])
            dice = dice_roll.split("-")[0]
            result_list, result_total = die_roll(int(dice.split("d")[0]), int(dice.split("d")[1]))
            await ctx.send(f"{ctx.author.mention} rolled **{result_total - modifier}**."
                           f" ({result_list}-{modifier})")
        elif re.fullmatch(normal_pattern, dice_roll):
            dice = dice_roll.split("+")[0]
            result_list, result_total = die_roll(int(dice.split("d")[0]), int(dice.split("d")[1]))
            if int(dice.split("d")[0]) == 1:
                await ctx.send(f"{ctx.author.mention} rolled **{result_total}**.")
            else:
                await ctx.send(f"{ctx.author.mention} rolled **{result_total}**. ({result_list})")
        else:
            await ctx.send(f"Dice rolls should be in the format: NdN+N")

    @commands.group(help='Draw cards from a selected Deck')
    async def deck(self, ctx):
        """Command grouping all card deck commands.
         Returns error to the channel is command is incomplete."""
        if ctx.invoked_subcommand is None:
            await ctx.send(f"Additional arguments required, see "
                           f"**{ctx.prefix}help deck** for available options.")

    @deck.command(help="List available decks.", name='list')
    async def list_decks(self, ctx):
        decks = "\n".join(self.deck_list)
        await ctx.send(f'\nAvailable Decks:\n{decks}')

    @deck.command(help="Select a deck to draw cards from.")
    async def select(self, ctx, deck_name=None):
        if deck_name is None:
            await ctx.send(f"ERROR: That deck doesn't exist.  Please select a deck from **{ctx.prefix}deck list**.")
        else:
            try:
                self.card_list[ctx.guild.id] = os.listdir(f'./data/decks/{deck_name}')
                self.active_deck[ctx.guild.id] = deck_name
                await ctx.send(f'Active deck set to {self.active_deck[ctx.guild.id]}')
            except FileNotFoundError:
                await ctx.send(f"ERROR: That deck doesn't exist.  Please select a deck from **{ctx.prefix}deck list**.")

    @deck.command(help='Draw a card from the selected deck')
    async def draw(self, ctx):
        try:
            if len(self.card_list[ctx.guild.id]) == 0:
                await ctx.send(f'No deck selected, please select a deck with **{ctx.prefix}deck select**.')
            else:
                file_name = random.choice(self.card_list[ctx.guild.id])
                self.card_list[ctx.guild.id].remove(file_name)
                file = discord.File(f'./data/decks/{self.active_deck[ctx.guild.id]}/{file_name}')
                embed = deck_embed_template(file_name)
                await ctx.send(embed=embed, file=file)
        except KeyError:
            await ctx.send(f'No deck selected, please select a deck with **{ctx.prefix}deck select**.')

    @deck.command(help='Reset deck to full.')
    async def reset(self, ctx):
        self.card_list[ctx.guild] = os.listdir(f'./data/decks/{self.active_deck[ctx.guild.id]}')
        await ctx.send('Discards have been shuffled back into the deck.')

    @deck.command(help='Rescan folder for new decks.')
    @commands.has_guild_permissions(manage_guild=True)
    async def rescan(self, ctx):
        self.deck_list = os.listdir('./data/decks')
        await ctx.send(f'Deck list has been refreshed.  Use **{ctx.prefix}deck list** to see all available card decks.')

    if bot_config['dice_roller'] == "array":
        @tasks.loop(hours=1)
        async def array_builder(self):
            """Task loop to rebuild arrays every hour."""
            self.rand_arrays = {
                'd20': [random.randint(1, 20) for _ in range(1000)],
                'd12': [random.randint(1, 12) for _ in range(1000)],
                'd10': [random.randint(1, 10) for _ in range(1000)],
                'd8': [random.randint(1, 8) for _ in range(1000)],
                'd6': [random.randint(1, 6) for _ in range(1000)]}

    @roll.error
    async def cog_command_error(self, ctx, error):
        print(error)

    # @roll.event
    # async def on_guild_join(self, guild):
    #     self.card_list[guild.id] = []
    #     self.active_deck[guild.id] = ""


def setup(bot):
    """Discord module required setup for Cog loading."""
    bot.add_cog(DiceRoller(bot))
