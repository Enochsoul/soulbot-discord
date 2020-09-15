import os
import re
import time
import random
import sqlite3
from datetime import datetime, tzinfo, timedelta

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv, set_key
from tabulate import tabulate

load_dotenv()

token = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix=os.getenv('COMMAND_PREFIX'))


@bot.command(help="Changes the bot command prefix.")
@commands.has_guild_permissions(manage_guild=True)
async def setprefix(ctx, prefix: str):
    set_key('.env', 'COMMAND_PREFIX', prefix)
    bot.command_prefix = prefix
    await ctx.send(f"Prefix now set to {prefix}.")


@setprefix.error
async def on_prefix_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f"{error}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CommandNotFound):
        await ctx.send(f"{ctx.prefix}{ctx.invoked_with} is not a valid command.  "
                       f"See **{ctx.prefix}help** for available commands.")


# =========================================================
# Bot Start
# =========================================================

@bot.event
async def on_ready():
    print(f"{bot.user.name} has connected to Discord.")


if __name__ == "__main__":
    bot.run(token)
