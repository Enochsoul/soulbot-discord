"""A discord bot with commands used to assist game play for the 13th Age RPG."""
import json
import discord
import arrow

from discord.ext import commands
from soulbot_support import soulbot_db, UTC, ET, MT, CT, PT

intents = discord.Intents.default()
intents.members = True

with open('soulbot.conf', "r") as config:
    bot_config = json.load(config)
token = bot_config['discord_token']


def get_prefix(bot, message):
    """Used to load all the prefixes from the config database and 
    return the correct one from the calling server.
    """
    prefixes = soulbot_db.config_all_prefix_load()
    if message.guild.id in list(prefixes.keys()):
        return prefixes[message.guild.id]
    else:
        return bot_config['command_prefix']


bot = commands.Bot(command_prefix=get_prefix, intents=intents)


@bot.group(help='Configuration Commands.')
@commands.has_guild_permissions(manage_guild=True)
async def config(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(f"Additional arguments required, "
                       f"see **{ctx.prefix}help config** for available options.")


@config.command(help="Changes the bot command prefix.", name='prefix')
async def set_prefix(ctx, prefix: str):
    """Takes in a prefix from the user, and updates the bot config.
    """
    soulbot_db.config_prefix_update(ctx.guild.id, prefix)
    await ctx.send(f"Prefix now set to {prefix}.")


@config.command(help='Set Next Game default start time.', name='time')
async def next_game_time(ctx, default_time: str, default_timezone: str):
    """Schedule command to change the time of the currently scheduled game.

            :param default_time: Time string
            :param default_timezone: Timezone string
            :param ctx: Discord context object
            """
    timezones = {"ET": ET, "CT": CT, "MT": MT, "PT": PT}
    try:
        sch_hour, sch_minute = [int(i) for i in default_time.split(":")]
        if (sch_hour > 24) or (sch_minute > 59):
            await ctx.send("Please use 24 hour time in the format: HH:MM TZ(Eg: 19:00 ET)")
        elif default_timezone.upper() not in ["ET", "CT", "MT", "PT"]:
            await ctx.send("Please indicate your timezone, ET, CT, MT, or PT.")
        else:
            time_output = default_time + " " + default_timezone.upper()
            soulbot_db.config_next_game_default_time_update(ctx.guild.id, time_output)
            await ctx.send(f'NextGameScheduler default game start time is now set to {time_output}.')
    except ValueError:
        await ctx.send("Please use 24 hour time in the format: HH:MM TZ(Eg: 19:00 ET)")


@config.command(help='Set Next Game default game interval in days.', name='interval')
async def next_game_interval(ctx, default_interval: int):
    """Schedule command to change the time of the currently scheduled game.

            :param default_interval: Interval in days.
            :param ctx: Discord context object
            """
    soulbot_db.config_next_game_default_interval_update(ctx.guild.id, default_interval)
    await ctx.send(f'NextGameScheduler default game interval is now set to {default_interval} days.')


@set_prefix.error
@next_game_time.error
@next_game_interval.error
async def config_error(ctx, error):
    """Error catching for the config commands."""
    if isinstance(error, commands.BadArgument):
        await ctx.send('Please use numeric values only for the game interval.')
    # Catching errors if the user doesn't have permission to run the setprefix command.
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send(f"{error}")
    else:
        await ctx.send(f'Experienced the following error:\n{error}')


@bot.event
async def on_command_error(ctx, error):
    """Catching errors if user tries running a command that doesn't exist."""
    if isinstance(error, commands.errors.CommandNotFound):
        await ctx.send(f"{ctx.prefix}{ctx.invoked_with} is not a valid command.  "
                       f"See **{ctx.prefix}help** for available commands.")


@bot.event
async def on_guild_join(guild):
    soulbot_db.config_insert_all(guild.id,
                                 bot_config['command_prefix'],
                                 bot_config['next_game_time'],
                                 bot_config['next_game_interval'],
                                 bot_config['announce_channel'])


# =========================================================
# Bot Start
# =========================================================

@bot.event
async def on_ready():
    """Bot readiness indicator on the script console."""
    print(f"{bot.user.name} has connected to Discord.")


if __name__ == "__main__":
    # bot.load_extension('CogAdmin')
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
