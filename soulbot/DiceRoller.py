"""Cog containing commands for dice rolling."""

import os
import random
from typing import Dict, List, Optional

import dice_support
import discord
import loguru
from discord.ext import commands


def deck_embed_template(image_file: str) -> discord.Embed:
    """Card Draw embed template."""
    embed_template = discord.Embed(title="You drew:", color=0xFF0000)
    embed_template.set_image(url=f"attachment://{image_file}")
    return embed_template


class DiceRoller(discord.Cog, name="Dice Roller"):
    """Class definition for DiceRoller Cog."""

    def __init__(
        self, bot: commands.Bot, dice_roller: dice_support.Dice
    ) -> None:
        self.bot = bot
        self.dice_roll = dice_roller
        self.card_list: Dict[int, List[str]] = {
            guild.id: [] for guild in bot.guilds
        }
        self.active_deck: Dict[int, str] = {
            guild.id: "" for guild in bot.guilds
        }
        self.deck_list: List[str] = os.listdir("./data/decks")
        loguru.logger.info("DiceRoller cog initialized")

    @commands.command(
        help="Dice roller.  Expected format: NdN+N.(Ex: 2d6+2)\nRoll Types: \n\td=Default\n\tad=Advantage\n\tdd=Disadvantage\n\ted=Exploding Dice\n\tdl=Drop Lowest Die\n\tdh=Drop Highest Die"
    )
    async def roll(self, ctx: commands.Context, dice_roll: str) -> None:
        try:
            rolled_result = self.dice_roll.roll(dice_roll.lower())
            loguru.logger.info(
                f"User {ctx.author} rolled {dice_roll}: {rolled_result.string}"
            )
            await ctx.send(f"{ctx.author.mention} {rolled_result.string}")
        except (
            dice_support.InvalidRollType,
            dice_support.InvalidDiceFormat,
        ) as e:
            loguru.logger.warning(
                f"Invalid dice roll by {ctx.author}: {dice_roll} - {e}"
            )
            await ctx.send(str(e))

    @commands.group(help="Draw cards from a selected Deck")
    async def deck(self, ctx: commands.Context) -> None:
        """Command grouping all card deck commands.
        Returns error to the channel is command is incomplete."""
        if ctx.invoked_subcommand is None:
            await ctx.send(
                f"Additional arguments required, see **{ctx.prefix}help deck** for available options."
            )

    @deck.command(help="List available decks.", name="list")
    async def list_decks(self, ctx: commands.Context) -> None:
        decks: str = "\n".join(self.deck_list)
        loguru.logger.info(f"User {ctx.author} requested deck list")
        await ctx.send(f"\nAvailable Decks:\n{decks}")

    @deck.command(help="Select a deck to draw cards from.")
    async def select(
        self, ctx: commands.Context, deck_name: Optional[str] = None
    ) -> None:
        if deck_name is None:
            await ctx.send(
                f"ERROR: That deck doesn't exist.  Please select a deck from **{ctx.prefix}deck list**."
            )
        else:
            try:
                self.card_list[ctx.guild.id] = os.listdir(
                    f"./data/decks/{deck_name}"
                )
                self.active_deck[ctx.guild.id] = deck_name
                loguru.logger.info(
                    f"User {ctx.author} in guild {ctx.guild.name} selected deck: {deck_name}"
                )
                await ctx.send(
                    f"Active deck set to {self.active_deck[ctx.guild.id]}"
                )
            except FileNotFoundError:
                loguru.logger.warning(
                    f"User {ctx.author} tried to select non-existent deck: {deck_name}"
                )
                await ctx.send(
                    f"ERROR: That deck doesn't exist.  Please select a deck from **{ctx.prefix}deck list**."
                )

    @deck.command(help="Draw a card from the selected deck")
    async def draw(self, ctx: commands.Context) -> None:
        try:
            if len(self.card_list[ctx.guild.id]) == 0:
                await ctx.send(
                    f"No deck selected, please select a deck with **{ctx.prefix}deck select**."
                )
            else:
                file_name: str = random.choice(self.card_list[ctx.guild.id])
                self.card_list[ctx.guild.id].remove(file_name)
                file: discord.File = discord.File(
                    f"./data/decks/{self.active_deck[ctx.guild.id]}/{file_name}"
                )
                embed: discord.Embed = deck_embed_template(file_name)
                loguru.logger.info(
                    f"User {ctx.author} drew card {file_name} from deck {self.active_deck[ctx.guild.id]}"
                )
                await ctx.send(embed=embed, file=file)
        except KeyError:
            loguru.logger.warning(
                f"User {ctx.author} tried to draw from unselected deck"
            )
            await ctx.send(
                f"No deck selected, please select a deck with **{ctx.prefix}deck select**."
            )

    @deck.command(help="Reset deck to full.")
    async def reset(self, ctx: commands.Context) -> None:
        self.card_list[ctx.guild.id] = os.listdir(
            f"./data/decks/{self.active_deck[ctx.guild.id]}"
        )
        loguru.logger.info(
            f"User {ctx.author} reset deck {self.active_deck[ctx.guild.id]}"
        )
        await ctx.send("Discards have been shuffled back into the deck.")

    @deck.command(help="Rescan folder for new decks.")
    @commands.has_guild_permissions(manage_guild=True)
    async def rescan(self, ctx: commands.Context) -> None:
        self.deck_list = os.listdir("./data/decks")
        loguru.logger.info(f"User {ctx.author} rescanned deck folder")
        await ctx.send(
            f"Deck list has been refreshed.  Use **{ctx.prefix}deck list** to see all available card decks."
        )

    @roll.error
    async def on_cog_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        loguru.logger.error(f"DiceRoller command error: {error}")
        print(error)


def setup(bot: commands.Bot) -> None:
    """Discord module required setup for Cog loading."""
    loguru.logger.info("Loading DiceRoller cog")
    bot.add_cog(DiceRoller(bot, dice_support.Dice()))
