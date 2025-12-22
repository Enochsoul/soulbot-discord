"""Cog containing commands for dice rolling."""

import os
import random

import discord
from discord.ext import commands, tasks

from dice_support import Dice, InvalidDiceFormat, InvalidRollType
from soulbot import bot_config

die_roll = Dice()


def deck_embed_template(image_file: str):
    """Card Draw embed template."""
    embed_template = discord.Embed(title="You drew:", color=0xFF0000)
    embed_template.set_image(url=f"attachment://{image_file}")
    return embed_template


class DiceRoller(discord.Cog, name='Dice Roller'):
    """Class definition for DiceRoller Cog."""

    def __init__(self, bot):
        self.bot = bot
        self.dice_roll = die_roll
        self.card_list = {guild.id: [] for guild in bot.guilds}
        self.active_deck = {guild.id: "" for guild in bot.guilds}
        self.deck_list = os.listdir("./data/decks")

    @commands.command(
        help="Dice roller.  Expected format: NdN+N.(Ex: 2d6+2)\nRoll Types: \n\td=Default\n\tad=Advantage\n\tdd=Disadvantage\n\ted=Exploding Dice\n\tdl=Drop Lowest Die\n\tdh=Drop Highest Die"
    )
    async def roll(self, ctx, *, dice_roll: str):
        try:
            rolled_result = self.dice_roll.roll(dice_roll.lower())
            await ctx.send(f"{ctx.author.mention} {rolled_result.string}")
        except (InvalidRollType, InvalidDiceFormat) as e:
            await ctx.send(str(e))

    @commands.group(help="Draw cards from a selected Deck")
    async def deck(self, ctx):
        """Command grouping all card deck commands.
        Returns error to the channel is command is incomplete."""
        if ctx.invoked_subcommand is None:
            await ctx.send(f"Additional arguments required, see **{ctx.prefix}help deck** for available options.")

    @deck.command(help="List available decks.", name="list")
    async def list_decks(self, ctx):
        decks = "\n".join(self.deck_list)
        await ctx.send(f"\nAvailable Decks:\n{decks}")

    @deck.command(help='Select a deck to draw cards from.')
    async def select(self, ctx, deck_name=None):
        if deck_name is None:
            await ctx.send(
                f"ERROR: That deck doesn't exist.  Please select a deck from **{ctx.prefix}deck list**."
            )
        else:
            try:
                self.card_list[ctx.guild.id] = os.listdir(f"./data/decks/{deck_name}")
                self.active_deck[ctx.guild.id] = deck_name
                await ctx.send(f"Active deck set to {self.active_deck[ctx.guild.id]}")
            except FileNotFoundError:
                await ctx.send(
                    f"ERROR: That deck doesn't exist.  Please select a deck from **{ctx.prefix}deck list**."
                )

    @deck.command(help="Draw a card from the selected deck")
    async def draw(self, ctx):
        try:
            if len(self.card_list[ctx.guild.id]) == 0:
                await ctx.send(f"No deck selected, please select a deck with **{ctx.prefix}deck select**.")
            else:
                file_name = random.choice(self.card_list[ctx.guild.id])
                self.card_list[ctx.guild.id].remove(file_name)
                file = discord.File(f"./data/decks/{self.active_deck[ctx.guild.id]}/{file_name}")
                embed = deck_embed_template(file_name)
                await ctx.send(embed=embed, file=file)
        except KeyError:
            await ctx.send(f"No deck selected, please select a deck with **{ctx.prefix}deck select**.")

    @deck.command(help="Reset deck to full.")
    async def reset(self, ctx):
        self.card_list[ctx.guild] = os.listdir(f"./data/decks/{self.active_deck[ctx.guild.id]}")
        await ctx.send("Discards have been shuffled back into the deck.")

    @deck.command(help="Rescan folder for new decks.")
    @commands.has_guild_permissions(manage_guild=True)
    async def rescan(self, ctx):
        self.deck_list = os.listdir("./data/decks")
        await ctx.send(f"Deck list has been refreshed.  Use **{ctx.prefix}deck list** to see all available card decks.")

    @roll.error
    async def cog_command_error(self, ctx, error):
        print(error)


def setup(bot):
    """Discord module required setup for Cog loading."""
    bot.add_cog(DiceRoller(bot))
