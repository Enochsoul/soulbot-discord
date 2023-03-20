"""A discord bot with commands used to assist game play for the 13th Age RPG."""
import json
import discord
import arrow

from discord.ext import commands, tasks
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
    """Command to set the default start time in the next_game module.

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
    """Command to set the next_game module default interval.

            :param default_interval: Interval in days.
            :param ctx: Discord context object
            """
    soulbot_db.config_next_game_default_interval_update(ctx.guild.id, default_interval)
    await ctx.send(f'NextGameScheduler default game interval is now set to {default_interval} days.')


@config.command(help='Configure the text channel to send the Next Game announcements to.  Default: general',
                name='announce')
async def next_game_announce_channel(ctx, channel_name: str):
    """Command to set the channel Next Game announcements are sent to.

    :param ctx: Discord context object.
    :param channel_name: String name of channel.
    """
    all_channels = []
    for channel in ctx.guild.text_channels:
        all_channels.append(channel.name)
    if channel_name in all_channels:
        soulbot_db.config_next_game_announce_channel(ctx.guild.id, channel_name)
        await ctx.send(f'Next Game Scheduler announcements will be sent to {channel_name}.')
    else:
        await ctx.send(f'{channel_name} is not a valid text channel.  Please try again.')


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


@bot.event
async def on_guild_remove(guild):
    soulbot_db.guild_remove_all(guild.id)


@tasks.loop(minutes=5)
async def game_announce():
    """Discord task loop to check if the next game will start in the next 60 minutes."""
    announce_check = soulbot_db.next_game_get_all_announcing()
    for server in announce_check:
        guild = bot.get_guild(server[0])
        channel = discord.utils.get(guild.text_channels, name=soulbot_db.config_load_guild(guild.id)['announce_channel'])
        next_game_scheduled = arrow.get(server[1])
        countdown = next_game_scheduled - arrow.utcnow()
        if channel:
            if countdown.seconds < 3600 and countdown.days == 0:
                soulbot_db.next_game_announce_toggle(0, guild.id)
                minutes, _ = divmod(countdown.seconds, 60)
                await channel.send(f"@here Next game in {minutes} minutes!\n"
                                   f"Further announcements have been disabled.")

# =========================================================
# Bot Start
# =========================================================


@bot.event
async def on_ready():
    """Bot readiness indicator on the script console."""
    print(f"{bot.user.name} has connected to Discord.")
    game_announce.start()

if __name__ == "__main__":
    # bot.load_extension('CogAdmin')
    bot.load_extension('DiceRoller')
    for cog in bot_config['load_cogs']:
        try:
            print(f"Loading {cog}")
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
