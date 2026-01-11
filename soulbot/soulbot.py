"""A discord bot with commands used to assist game play for the 13th Age RPG."""

import json
import pathlib
from datetime import timedelta
from typing import Any, Dict, Union

import arrow
import discord
from discord.ext import commands, tasks
from init_support import InitiativeTrack
from loguru import logger
from soulbot_support import NextGame, soulbot_db

# Constants
VALID_TIMEZONES = ["ET", "CT", "MT", "PT"]
CONFIG_FILE = "soulbot.conf"
ANNOUNCEMENT_CHECK_INTERVAL = 1  # minutes
ANNOUNCEMENT_THRESHOLD = 3600  # seconds (1 hour)
LOG_LOCATION = pathlib.Path("logs/soulbot.log")

# Setup Logging
logger.remove()
logger.add(LOG_LOCATION, rotation="1 MB", retention="30 days")


class SoulBot(commands.Bot):
    """Custom bot class for 13th Age RPG assistance."""

    def __init__(self, config: Dict[str, Any], guild_init: Dict | None = None):
        self.config = config
        if guild_init is None:
            self.guild_init = dict()
        else:
            self.guild_init = guild_init
        self.prefixes = soulbot_db.config_all_prefix_load()

        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        logger.info(f"Initializing SoulBot with config: {config}\nIntents: {dict(intents)}")

        super().__init__(command_prefix=self._get_prefix, intents=intents)

    def _get_prefix(self, bot: Union[commands.Bot, commands.AutoShardedBot], message: discord.Message) -> str:
        """Get the command prefix for a specific guild."""
        if message.guild:
            return self.prefixes[message.guild.id]
        else:
            return self.config["command_prefix"]


class ConfigCommands(commands.Cog):
    """Configuration commands for the bot."""

    def __init__(self, bot: SoulBot):
        self.bot = bot

    @commands.group(help="Configuration Commands.")
    @commands.has_guild_permissions(manage_guild=True)
    async def config(self, ctx: commands.Context) -> None:
        """Main configuration command group."""
        if ctx.invoked_subcommand is None:
            await ctx.send(f"Additional arguments required, see **{ctx.prefix}help config** for available options.")

    @config.command(help="Display the current guild config options.", name="display")
    async def display_config(self, ctx: commands.Context) -> None:
        try:
            if not ctx.guild:
                await ctx.send("This command can only be used in a guild.")
                return
            config = soulbot_db.config_get_guild(ctx.guild.id)

            if not config:
                await ctx.send("No configuration found for this guild.")
                return
            output = f"""Guild ID: {config.guild_id}\nPrefix: {config.prefix}\nNext Game default Start Time: {config.next_game_start}\nNext Game default interval: {config.next_game_interval}\nNext Game announce channel: {config.announce_channel}"""
            await ctx.send(f"Current configuration for {ctx.guild.name}:\n{output}")
        except (Exception, RuntimeError) as e:
            await ctx.send(f"An error occurred while displaying the configuration: {e}")

    @config.command(help="Changes the bot command prefix.", name="prefix")
    async def set_prefix(self, ctx: commands.Context, prefix: str) -> None:
        """Update the bot command prefix for this guild."""
        if not ctx.guild:
            await ctx.send("This command can only be used in a guild.")
            return

        self.bot.prefixes[ctx.guild.id] = prefix
        soulbot_db.config_prefix_update(ctx.guild.id, prefix)
        await ctx.send(f"Prefix now set to {prefix}.")

    @config.command(help="Set Next Game default start time.", name="time")
    async def next_game_time(self, ctx: commands.Context, default_time: str, default_timezone: str) -> None:
        """Set the default start time for the next game module."""
        if not ctx.guild:
            await ctx.send("This command can only be used in a guild.")
            return

        validation_result = self._validate_time_input(default_time, default_timezone)
        if validation_result["error"]:
            await ctx.send(validation_result["message"])
            return

        time_output = f"{default_time} {default_timezone.upper()}"
        soulbot_db.config_next_game_default_time_update(ctx.guild.id, time_output)
        await ctx.send(f"NextGameScheduler default game start time is now set to {time_output}.")

    @config.command(help="Set Next Game default game interval in days.", name="interval")
    async def next_game_interval(self, ctx: commands.Context, default_interval: int) -> None:
        """Set the default interval for the next game module."""
        if not ctx.guild:
            await ctx.send("This command can only be used in a guild.")
            return

        soulbot_db.config_next_game_default_interval_update(ctx.guild.id, default_interval)
        await ctx.send(f"NextGameScheduler default game interval is now set to {default_interval} days.")

    @config.command(
        help="Configure the text channel to send the Next Game announcements to. Default: general",
        name="announce",
    )
    async def next_game_announce_channel(self, ctx: commands.Context, channel_name: str) -> None:
        """Set the channel for Next Game announcements."""
        if not ctx.guild:
            await ctx.send("This command can only be used in a guild.")
            return

        valid_channels = [channel.name for channel in ctx.guild.text_channels]

        if channel_name not in valid_channels:
            await ctx.send(f"{channel_name} is not a valid text channel. Please try again.")
            return

        soulbot_db.config_next_game_announce_channel(ctx.guild.id, channel_name)
        await ctx.send(f"Next Game Scheduler announcements will be sent to {channel_name}.")

    def _validate_time_input(self, time_str: str, timezone_str: str) -> Dict[str, Any]:
        """Validate time and timezone input."""
        try:
            hour, minute = map(int, time_str.split(":"))

            if hour > 23 or minute > 59:  # Fixed: hour should be 0-23, not 0-24
                return {"error": True, "message": "Please use 24 hour time in the format: HH:MM TZ(Eg: 19:00 ET)"}

            if timezone_str.upper() not in VALID_TIMEZONES:
                return {"error": True, "message": "Please indicate your timezone: ET, CT, MT, or PT."}

            return {"error": False, "message": ""}

        except ValueError:
            return {"error": True, "message": "Please use 24 hour time in the format: HH:MM TZ(Eg: 19:00 ET)"}

    @set_prefix.error
    @next_game_time.error
    @next_game_interval.error
    async def config_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """Error handler for configuration commands."""
        if isinstance(error, commands.BadArgument):
            await ctx.send("Please use numeric values only for the game interval.")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(str(error))
        else:
            logger.error(f"Config command error: {error}")
            await ctx.send(f"Experienced the following error:\n{error}")


class GameAnnouncer:
    """Handles game announcement functionality."""

    def __init__(self, bot: SoulBot):
        self.bot = bot

    @tasks.loop(minutes=ANNOUNCEMENT_CHECK_INTERVAL)
    async def game_announce_task(self) -> None:
        """Check for upcoming games and send announcements."""
        try:
            announce_check = soulbot_db.next_game_get_all_announcing()

            for server_data in announce_check:
                await self._process_server_announcement(server_data)

        except commands.ChannelNotFound as e:
            logger.warning(str(e))
        except Exception as e:
            logger.error(f"Error in game announcement task: {e}")

    async def _process_server_announcement(self, server_data: NextGame) -> None:
        """Process announcement for a single server."""

        guild = self.bot.get_guild(server_data.guild_id)
        if not guild:
            logger.warning(f"Guild {server_data.guild_id} not found")
            return

        config = soulbot_db.config_get_guild(guild.id)
        channel = discord.utils.get(guild.text_channels, name=config.announce_channel)
        if not channel:
            error_msg = f"Announcement channel not found for guild {guild.id}"
            logger.warning(error_msg)
            raise commands.ChannelNotFound(error_msg)

        next_game_scheduled = arrow.get(server_data.next_date)
        countdown = next_game_scheduled - arrow.utcnow()

        # Check if we're within 60 minutes (3600 seconds) of the scheduled time
        total_seconds_remaining = countdown.total_seconds()

        # Trigger announcement if within 60 minutes and game hasn't passed
        if 0 <= total_seconds_remaining <= ANNOUNCEMENT_THRESHOLD:
            await self._send_announcement(channel, countdown, guild.id)

    async def _send_announcement(self, channel: discord.TextChannel, countdown: timedelta, guild_id: int) -> None:
        """Send the actual game announcement."""
        soulbot_db.next_game_announce_toggle(False, guild_id)

        # Calculate minutes remaining more accurately
        total_seconds = countdown.total_seconds()
        minutes_remaining = max(0, int(total_seconds // 60))

        if minutes_remaining > 0:
            await channel.send(
                f"@here Next game in {minutes_remaining} minutes!\nFurther announcements have been disabled."
            )
        else:
            await channel.send("@here Next game is starting now!\nFurther announcements have been disabled.")


def load_config() -> Dict[str, Any]:
    """Load bot configuration from file."""
    try:
        with open(CONFIG_FILE, "r") as config_file:
            return json.load(config_file)
    except FileNotFoundError:
        logger.error(f"Configuration file {CONFIG_FILE} not found")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file: {e}")
        raise


def setup_bot(config: Dict[str, Any]) -> SoulBot:
    """Initialize and configure the bot."""
    bot = SoulBot(config)

    # Add event handlers
    @bot.event
    async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
        """Handle command errors."""
        if isinstance(error, commands.errors.CommandNotFound):
            await ctx.send(
                f"{ctx.prefix}{ctx.invoked_with} is not a valid command. "
                f"See **{ctx.prefix}help** for available commands."
            )

    @bot.event
    async def on_guild_join(guild: discord.Guild) -> None:
        """Handle bot joining a new guild."""
        soulbot_db.config_insert_all(
            guild.id,
            config["command_prefix"],
            config["next_game_time"],
            config["next_game_interval"],
            config["announce_channel"],
        )
        bot.prefixes = soulbot_db.config_all_prefix_load()
        bot.guild_init[guild.id] = InitiativeTrack()
        logger.info(f"Joined guild: {guild.name} ({guild.id})")

    @bot.event
    async def on_guild_remove(guild: discord.Guild) -> None:
        """Handle bot being removed from a guild."""
        soulbot_db.guild_remove_all(guild.id)
        _ = bot.guild_init.pop(guild.id)
        _ = bot.prefixes.pop(guild.id)
        logger.info(f"Left guild: {guild.name} ({guild.id})")

    @bot.event
    async def on_ready() -> None:
        """Handle bot ready event."""
        if bot.user:
            logger.info(f"{bot.user.name} has connected to Discord.")

        # Start the game announcement task
        if not announcer.game_announce_task.is_running():
            announcer.game_announce_task.start()

        # Restore initiative trackers for all registered guilds if they exist.
        guild_list = bot.prefixes.keys()
        for guild in guild_list:
            init_tracker = soulbot_db.init_db_rebuild(guild)
            if init_tracker is None:
                bot.guild_init[guild] = InitiativeTrack()
            else:
                bot.guild_init[guild] = init_tracker

    return bot


def load_extensions(bot: SoulBot) -> None:
    """Load bot extensions and cogs."""
    # Load DiceRoller extension
    try:
        bot.load_extension("DiceRoller")
        logger.info("Loaded DiceRoller extension")
    except Exception as e:
        logger.error(f"Failed to load DiceRoller: {e}")

    # Load configured cogs
    for cog in bot.config.get("load_cogs", []):
        try:
            bot.load_extension(f"cogs.{cog}")
        except discord.ExtensionNotLoaded as e:
            logger.error(f"Extension not loaded for {cog}: {e}")
        except discord.ExtensionFailed as e:
            logger.error(f"Extension failed for {cog}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error loading {cog}: {e}")


# Initialize components
bot_config = load_config()
bot = setup_bot(bot_config)
announcer = GameAnnouncer(bot)

# Add cogs
bot.add_cog(ConfigCommands(bot))

if __name__ == "__main__":
    load_extensions(bot)

    try:
        bot.run(bot.config["discord_token"])
    except Exception as e:
        logger.error(f"Bot startup error: {e}")
