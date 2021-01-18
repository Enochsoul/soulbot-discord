"""A discord bot with commands used to assist game play for the 13th Age RPG."""
import json
import discord

from discord.ext import commands
from soulbot_support import soulbot_db

intents = discord.Intents.default()
intents.members = True

with open('soulbot.conf', "r") as config:
    bot_config = json.load(config)
token = bot_config['discord_token']


def get_prefix(bot, message):
    """Used to load all the prefixes from the config database and 
    return the correct one from the calling server.
    """
    prefixes = soulbot_db.config_load()
    if message.guild.id in list(prefixes.keys()):
        return prefixes[message.guild.id]
    else:
        return bot_config['command_prefix']


bot = commands.Bot(command_prefix=get_prefix, intents=intents)


@bot.command(help="Changes the bot command prefix.", name='setprefix')
@commands.has_guild_permissions(manage_guild=True)
async def set_prefix(ctx, prefix: str):
    """Takes in a prefix from the user, and updates the bot config.
    """
    soulbot_db.config_insert(ctx.guild.id, prefix)
    await ctx.send(f"Prefix now set to {prefix}.")


@set_prefix.error
async def on_prefix_error(ctx, error):
    """Catching errors if the user doesn't have permission to run the setprefix command."""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f"{error}")


@bot.event
async def on_command_error(ctx, error):
    """Catching errors if user tries running a command that doesn't exist."""
    if isinstance(error, commands.errors.CommandNotFound):
        await ctx.send(f"{ctx.prefix}{ctx.invoked_with} is not a valid command.  "
                       f"See **{ctx.prefix}help** for available commands.")


@bot.event
async def on_guild_join(guild):
    soulbot_db.config_insert(guild.id, bot_config['command_prefix'])


# =========================================================
# Bot Start
# =========================================================

@bot.event
async def on_ready():
    """Bot readiness indicator on the script console."""
    print(f"{bot.user.name} has connected to Discord.")


if __name__ == "__main__":
    bot.load_extension('CogAdmin')
    bot.load_extension('DiceRoller')
    for cog in bot_config['load_cogs']:
        try:
            bot.load_extension(f'cogs.{cog}')
        except commands.ExtensionNotLoaded as cog_error:
            print(f'There was a problem loading Cog {cog}.\nException:\n{cog_error}')
        except commands.ExtensionFailed as cog_error:
            print(f'There was an unexpected error loading {cog}:\n{cog_error}')
        except Exception as cog_error:
            print(f'There was an unexpected error loading {cog}:\n{cog_error}')

    try:
        bot.run(token)
    except Exception as bot_error:
        print(f'Got the following error trying to startup the bot, '
              f'check your config and try again.\n\n{bot_error}')
