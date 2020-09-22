"""Cog containing commands for dice rolling."""
import re
import random
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


class DiceRoller(commands.Cog, name="Dice Roller"):
    """Class definition for DiceRoller Cog."""
    def __init__(self, bot):
        self.bot = bot
        if bot_config['dice_roller'] == "array":
            self.rand_arrays = rand_arrays

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


def setup(bot):
    """Discord module required setup for Cog loading."""
    bot.add_cog(DiceRoller(bot))
