"""A discord bot with commands used to assist game play for the 13th Age RPG."""
import json

from discord.ext import commands

with open('soulbot.conf', "r") as config:
    bot_config = json.load(config)
token = bot_config['discord_token']
bot = commands.Bot(command_prefix=bot_config['command_prefix'])


@bot.command(help="Changes the bot command prefix.", name='setprefix')
@commands.has_guild_permissions(manage_guild=True)
async def set_prefix(ctx, prefix: str):
    """Takes in a prefix from the user, saves it to the running config
    and updates the bot config.
    """
    bot_config['command_prefix'] = prefix
    bot.command_prefix = prefix
    with open('soulbot.conf', 'w') as outfile:
        json.dump(bot_config, outfile)
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
