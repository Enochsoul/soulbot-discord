"""Cog containing commands for dice rolling."""

import os
import random
from typing import Dict, List, Optional

import discord
from discord.ext import commands

from dice_support import Dice, InvalidDiceFormat, InvalidRollType

die_roll: Dice = Dice()


def deck_embed_template(image_file: str) -> discord.Embed:
    """Card Draw embed template."""
    embed_template = discord.Embed(title="You drew:", color=0xFF0000)
    embed_template.set_image(url=f"attachment://{image_file}")
    return embed_template


class DiceRoller(discord.Cog, name="Dice Roller"):
    """Class definition for DiceRoller Cog."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.dice_roll = die_roll
        self.card_list: Dict[int, List[str]] = {guild.id: [] for guild in bot.guilds}
        self.active_deck: Dict[int, str] = {guild.id: "" for guild in bot.guilds}
        self.deck_list: List[str] = os.listdir("./data/decks")

    @commands.command(
        help="Dice roller.  Expected format: NdN+N.(Ex: 2d6+2)\nRoll Types: \n\td=Default\n\tad=Advantage\n\tdd=Disadvantage\n\ted=Exploding Dice\n\tdl=Drop Lowest Die\n\tdh=Drop Highest Die"
    )
    async def roll(self, ctx: commands.Context, dice_roll: str) -> None:
        try:
            rolled_result = self.dice_roll.roll(dice_roll.lower())
            await ctx.send(f"{ctx.author.mention} {rolled_result.string}")
        except (InvalidRollType, InvalidDiceFormat) as e:
            await ctx.send(str(e))

    @commands.group(help="Draw cards from a selected Deck")
    async def deck(self, ctx: commands.Context) -> None:
        """Command grouping all card deck commands.
        Returns error to the channel is command is incomplete."""
        if ctx.invoked_subcommand is None:
            await ctx.send(f"Additional arguments required, see **{ctx.prefix}help deck** for available options.")

    @deck.command(help="List available decks.", name="list")
    async def list_decks(self, ctx: commands.Context) -> None:
        decks: str = "\n".join(self.deck_list)
        await ctx.send(f"\nAvailable Decks:\n{decks}")

    @deck.command(help="Select a deck to draw cards from.")
    async def select(self, ctx: commands.Context, deck_name: Optional[str] = None) -> None:
        if deck_name is None:
            await ctx.send(f"ERROR: That deck doesn't exist.  Please select a deck from **{ctx.prefix}deck list**.")
        else:
            try:
                self.card_list[ctx.guild.id] = os.listdir(f"./data/decks/{deck_name}")
                self.active_deck[ctx.guild.id] = deck_name
                await ctx.send(f"Active deck set to {self.active_deck[ctx.guild.id]}")
            except FileNotFoundError:
                await ctx.send(f"ERROR: That deck doesn't exist.  Please select a deck from **{ctx.prefix}deck list**.")

    @deck.command(help="Draw a card from the selected deck")
    async def draw(self, ctx: commands.Context) -> None:
        try:
            if len(self.card_list[ctx.guild.id]) == 0:
                await ctx.send(f"No deck selected, please select a deck with **{ctx.prefix}deck select**.")
            else:
                file_name: str = random.choice(self.card_list[ctx.guild.id])
                self.card_list[ctx.guild.id].remove(file_name)
                file: discord.File = discord.File(f"./data/decks/{self.active_deck[ctx.guild.id]}/{file_name}")
                embed: discord.Embed = deck_embed_template(file_name)
                await ctx.send(embed=embed, file=file)
        except KeyError:
            await ctx.send(f"No deck selected, please select a deck with **{ctx.prefix}deck select**.")

    @deck.command(help="Reset deck to full.")
    async def reset(self, ctx: commands.Context) -> None:
        self.card_list[ctx.guild.id] = os.listdir(f"./data/decks/{self.active_deck[ctx.guild.id]}")
        await ctx.send("Discards have been shuffled back into the deck.")

    @deck.command(help="Rescan folder for new decks.")
    @commands.has_guild_permissions(manage_guild=True)
    async def rescan(self, ctx: commands.Context) -> None:
        self.deck_list = os.listdir("./data/decks")
        await ctx.send(f"Deck list has been refreshed.  Use **{ctx.prefix}deck list** to see all available card decks.")

    @roll.error
    async def cog_command_error(self, ctx: discord.ApplicationContext, error: Exception) -> None:
        print(error)


def setup(bot: commands.Bot) -> None:
    """Discord module required setup for Cog loading."""
    bot.add_cog(DiceRoller(bot))
