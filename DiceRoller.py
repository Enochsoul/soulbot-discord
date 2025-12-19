"""Cog containing commands for dice rolling."""

import os
import random
import re
from dataclasses import dataclass
from itertools import chain
from typing import List

import discord
import numpy as np
from discord.ext import commands, tasks
from scipy.stats import truncnorm

from soulbot import bot_config


class InvalidDiceFormat(Exception):
    pass


class InvalidRollType(Exception):
    pass


@dataclass
class RollResult:
    """Data class to represent dice roll results."""

    rolls: List[str]
    total: int
    roll_type: str
    modifier: int | None


class Dice:
    """A comprehensive dice rolling system with support for various roll types."""

    def __init__(self) -> None:
        # Regex patterns for different roll formats
        self.normal_pattern = re.compile(
            r"^(?P<dice_count>[0-9]+)(?P<roll_type>\D{1,2})(?P<dice_size>[0-9]+)(?P<modifier>[+-][0-9]+)*$"
        )
        self.multi_dice_pattern = re.compile(r"^(?:\d+\D+\d+[-+]?\d*/?)+$")

    def roll(self, roll_string: str) -> str:
        """Main entry point for rolling dice."""
        return self._output_formatter(self._parse_and_roll(roll_string))

    def _parse_and_roll(self, roll_string: str) -> RollResult:
        """Parse the roll string and execute the appropriate roll."""
        # Try to match different patterns
        normal_match = self.normal_pattern.match(roll_string)
        multi_match = self.multi_dice_pattern.match(roll_string)

        if normal_match:
            return self._handle_normal_roll(normal_match)
        elif multi_match:
            return self._handle_multi_roll(multi_match)
        else:
            raise InvalidDiceFormat(
                "Error: Dice rolls should be in the format 'XdY' or 'XdY+Z' or 'XdY-Z'"
            )

    def _handle_normal_roll(self, match) -> RollResult:
        """Handle a normal dice roll (e.g., 3d6, 1ad20)."""
        count, roll_type, size, modifier = match.groups()
        modifier = int(modifier) if modifier else 0
        dice_rolls = self._generate_dice_rolls(int(count), int(size))
        return self._apply_roll_type(int(size), dice_rolls, roll_type, modifier)

    def _handle_multi_roll(self, match) -> RollResult:
        """Handle multiple dice rolls separated by '/' (e.g., 1d6/1d8/2d4)."""
        rolls = match.string.split("/")
        roll_results = []

        for roll in rolls:
            if not self.normal_pattern.match(roll):
                raise InvalidDiceFormat("Error: Unrecognized dice format.")
            roll_results.append(self._parse_and_roll(roll))

        # Combine results
        combined_rolls = list(chain(*[result.rolls for result in roll_results]))
        combined_totals = sum([result.total for result in roll_results])
        combined_types = "/".join([result.roll_type for result in roll_results])
        combined_modifiers = sum([result.modifier for result in roll_results])

        return RollResult(
            combined_rolls, combined_totals, combined_types, combined_modifiers
        )

    def _generate_dice_rolls(self, count: int, size: int) -> List[int]:
        """Generate dice rolls using numpy/scipy for multi-die or random for single die."""
        if count == 1:
            return self._roll_single_die(size)
        else:
            return self._roll_multiple_dice(count, size)

    @staticmethod
    def _roll_single_die(die_size: int) -> List[int]:
        """Roll a single die using standard random."""
        return [random.randint(1, die_size)]

    @staticmethod
    def _roll_multiple_dice(die_count: int, die_size: int) -> List[int]:
        """Roll multiple dice using numpy and scipy for better distribution."""
        mean = np.mean(range(1, die_size + 1))
        std = np.std(range(1, die_size + 1))
        a, b = (1 - mean) / std, ((die_size + 1) - mean) / std

        return (
            truncnorm.rvs(a, b, loc=mean, scale=std, size=die_count)
            .astype(int)
            .tolist()
        )

    def _apply_roll_type(
        self,
        die_size: int,
        roll_result: List[int],
        roll_type: str,
        modifier: int | None,
    ) -> RollResult:
        """Apply special roll type effects (advantage, disadvantage, exploding, etc.)."""
        match roll_type:
            case "d":  # Normal roll
                bold_result = [
                    f"**{roll}**" if roll == die_size else str(roll)
                    for roll in roll_result
                ]
                return RollResult(bold_result, sum(roll_result), "normal", modifier)

            case "dd":  # Disadvantage roll
                if len(roll_result) != 1:
                    raise InvalidDiceFormat(
                        "Error: Disadvantage roll must only be a single die."
                    )
                roll_result.extend(self._roll_single_die(die_size))
                bold_result = [
                    f"**{roll}**" if roll == die_size else str(roll)
                    for roll in roll_result
                ]
                return RollResult(
                    bold_result, min(roll_result), "disadvantage", modifier
                )

            case "ad":  # Advantage roll
                if len(roll_result) != 1:
                    raise InvalidDiceFormat(
                        "Error: Advantage roll must only be a single die."
                    )
                roll_result.extend(self._roll_single_die(die_size))
                bold_result = [
                    f"**{roll}**" if roll == die_size else str(roll)
                    for roll in roll_result
                ]
                return RollResult(bold_result, max(roll_result), "advantage", modifier)

            case "ed":  # Exploding roll
                explode_count = roll_result.count(die_size)
                while explode_count > 0:
                    explode_count -= 1
                    exploded = self._roll_single_die(die_size)
                    roll_result.extend(exploded)
                    explode_count += exploded.count(die_size)

                bold_result = [
                    f"**{roll}**" if roll == die_size else str(roll)
                    for roll in roll_result
                ]
                return RollResult(bold_result, sum(roll_result), "exploding", modifier)

            case "ex":  # 10X System (placeholder for future implementation)
                bold_result = [
                    f"**{roll}**" if roll == die_size else str(roll)
                    for roll in roll_result
                ]
                return RollResult(bold_result, sum(roll_result), "10x_system", modifier)

            case _:  # Invalid type
                raise InvalidRollType(f"Error: Invalid roll type: {roll_type}")

    @staticmethod
    def _output_formatter(roll_result: RollResult) -> str:
        if roll_result.modifier:
            string_modifier = (
                f"+{roll_result.modifier}"
                if roll_result.modifier > 0
                else f"{roll_result.modifier}"
            )
            if len(roll_result.rolls) == 1:
                return f"rolled **{roll_result.total + roll_result.modifier}**. ({roll_result.total}{string_modifier})"
            elif len(roll_result.rolls) > 1:
                string_out = "+".join(roll_result.rolls) + string_modifier
                return f"rolled **{roll_result.total + roll_result.modifier}**. ({string_out})"
            else:
                return "rolled the impossible, please try again."
        else:
            string_out = "+".join(roll_result.rolls)
            return f"rolled **{roll_result.total}**. ({string_out})"


# Select import of appropriate die roll module based on config.
if bot_config['dice_roller'] == 'random_org':
    if bot_config['random_org_key']:
        from random_org_dice import die_roll
    else:
        from default_dice import die_roll

        print(
            'No API key for Random.org configured in soulbot.conf, using default dice roller function.'
        )
elif bot_config['dice_roller'] == 'array':
    from array_dice import die_roll, rand_arrays
else:
    from default_dice import die_roll


def deck_embed_template(image_file: str):
    """Card Draw embed template."""
    embed_template = discord.Embed(title='You drew:', color=0xFF0000)
    embed_template.set_image(url=f'attachment://{image_file}')
    return embed_template


class DiceRoller(discord.Cog, name='Dice Roller'):
    """Class definition for DiceRoller Cog."""

    def __init__(self, bot):
        self.bot = bot
        if bot_config['dice_roller'] == 'array':
            self.rand_arrays = rand_arrays
        self.card_list = {guild.id: [] for guild in bot.guilds}
        self.active_deck = {guild.id: '' for guild in bot.guilds}
        self.deck_list = os.listdir('./data/decks')

    @commands.command(help='Dice roller.  Expected format: NdN+N.(Ex: 2d6+2)')
    async def roll(self, ctx, *, dice_roll: str):
        plus_mod_re = re.compile(
            r'^(?P<dice_count>[0-9]+)([dD])(?P<dice_size>[0-9]+)\s?\+\s?(?P<modifier>[0-9]+)$'
        )
        minus_mod_re = re.compile(
            r'^(?P<dice_count>[0-9]+)([dD])(?P<dice_size>[0-9]+)\s?-\s?(?P<modifier>[0-9]+)$'
        )
        normal_re = re.compile(r'^(?P<dice_count>[0-9]+)([dD])(?P<dice_size>[0-9]+)$')
        plus_match = plus_mod_re.match(dice_roll)
        minus_match = minus_mod_re.match(dice_roll)
        normal_match = normal_re.match(dice_roll)
        if plus_match:
            result_list, result_total = die_roll(
                int(plus_match.groupdict()['dice_count']), int(plus_match.groupdict()['dice_size'])
            )
            await ctx.send(
                f'{ctx.author.mention} rolled **{result_total + int(plus_match.groupdict()["modifier"])}**.'
                f' ({result_list}+{plus_match.groupdict()["modifier"]})'
            )
        elif minus_match:
            result_list, result_total = die_roll(
                int(minus_match.groupdict()['dice_count']),
                int(minus_match.groupdict()['dice_size']),
            )
            await ctx.send(
                f'{ctx.author.mention} rolled **{result_total - int(minus_match.groupdict()["modifier"])}**.'
                f' ({result_list}-{minus_match.groupdict()["modifier"]})'
            )
        elif normal_match:
            result_list, result_total = die_roll(
                int(normal_match.groupdict()['dice_count']),
                int(normal_match.groupdict()['dice_size']),
            )
            if int(normal_match.groupdict()['dice_count']) == 1:
                await ctx.send(f'{ctx.author.mention} rolled **{result_total}**.')
            else:
                await ctx.send(f'{ctx.author.mention} rolled **{result_total}**. ({result_list})')
        else:
            await ctx.send('Dice rolls should be in the format: NdN+N')

    @commands.group(help='Draw cards from a selected Deck')
    async def deck(self, ctx):
        """Command grouping all card deck commands.
        Returns error to the channel is command is incomplete."""
        if ctx.invoked_subcommand is None:
            await ctx.send(
                f'Additional arguments required, see '
                f'**{ctx.prefix}help deck** for available options.'
            )

    @deck.command(help='List available decks.', name='list')
    async def list_decks(self, ctx):
        decks = '\n'.join(self.deck_list)
        await ctx.send(f'\nAvailable Decks:\n{decks}')

    @deck.command(help='Select a deck to draw cards from.')
    async def select(self, ctx, deck_name=None):
        if deck_name is None:
            await ctx.send(
                f"ERROR: That deck doesn't exist.  Please select a deck from **{ctx.prefix}deck list**."
            )
        else:
            try:
                self.card_list[ctx.guild.id] = os.listdir(f'./data/decks/{deck_name}')
                self.active_deck[ctx.guild.id] = deck_name
                await ctx.send(f'Active deck set to {self.active_deck[ctx.guild.id]}')
            except FileNotFoundError:
                await ctx.send(
                    f"ERROR: That deck doesn't exist.  Please select a deck from **{ctx.prefix}deck list**."
                )

    @deck.command(help='Draw a card from the selected deck')
    async def draw(self, ctx):
        try:
            if len(self.card_list[ctx.guild.id]) == 0:
                await ctx.send(
                    f'No deck selected, please select a deck with **{ctx.prefix}deck select**.'
                )
            else:
                file_name = random.choice(self.card_list[ctx.guild.id])
                self.card_list[ctx.guild.id].remove(file_name)
                file = discord.File(f'./data/decks/{self.active_deck[ctx.guild.id]}/{file_name}')
                embed = deck_embed_template(file_name)
                await ctx.send(embed=embed, file=file)
        except KeyError:
            await ctx.send(
                f'No deck selected, please select a deck with **{ctx.prefix}deck select**.'
            )

    @deck.command(help='Reset deck to full.')
    async def reset(self, ctx):
        self.card_list[ctx.guild] = os.listdir(f'./data/decks/{self.active_deck[ctx.guild.id]}')
        await ctx.send('Discards have been shuffled back into the deck.')

    @deck.command(help='Rescan folder for new decks.')
    @commands.has_guild_permissions(manage_guild=True)
    async def rescan(self, ctx):
        self.deck_list = os.listdir('./data/decks')
        await ctx.send(
            f'Deck list has been refreshed.  Use **{ctx.prefix}deck list** to see all available card decks.'
        )

    if bot_config['dice_roller'] == 'array':

        @tasks.loop(hours=1)
        async def array_builder(self):
            """Task loop to rebuild arrays every hour."""
            self.rand_arrays = {
                'd20': [random.randint(1, 20) for _ in range(1000)],
                'd12': [random.randint(1, 12) for _ in range(1000)],
                'd10': [random.randint(1, 10) for _ in range(1000)],
                'd8': [random.randint(1, 8) for _ in range(1000)],
                'd6': [random.randint(1, 6) for _ in range(1000)],
            }

    @roll.error
    async def cog_command_error(self, ctx, error):
        print(error)


def setup(bot):
    """Discord module required setup for Cog loading."""
    bot.add_cog(DiceRoller(bot))
