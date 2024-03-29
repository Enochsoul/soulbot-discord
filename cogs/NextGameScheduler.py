"""Cog containing commands for controlling game schedule tracker."""
import arrow
import discord
from discord.ext import commands

from soulbot_support import soulbot_db, UTC, ET, MT, CT, PT


def next_game_embed_template(input_date):
    """Discord embed template generator for Next Game announcements.

    :return: embed object.
    :param input_date: Input date in UTC.
    """
    time_until = input_date - arrow.now(UTC)
    days = time_until.days
    hours, remainder = divmod(time_until.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    output_embed = discord.Embed(title="__**Next Scheduled Game**__",
                                 description="Time until next game: "
                                             f"{days} Days, {hours} Hours, {minutes} Minutes")
    output_embed.add_field(name="__Eastern Time__",
                           value=f"{input_date.to(ET).strftime('%d/%m/%Y %H:%M')}",
                           inline=False)
    output_embed.add_field(name="__Mountain Time__",
                           value=f"{input_date.to(MT).strftime('%d/%m/%Y %H:%M')}",
                           inline=False)
    output_embed.add_field(name="__Pacific Time__",
                           value=f"{input_date.to(PT).strftime('%d/%m/%Y %H:%M')}",
                           inline=False)
    return output_embed


class NextGameScheduler(commands.Cog, name="Next Game Scheduler"):
    """Class definition for Next Game Scheduler Cog, inherits from discord extension Cog class."""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="next", help="Prints out the date of the next game.")
    async def next_game(self, ctx):
        """Base level cog group command."""
        if ctx.invoked_subcommand is None:
            next_game_scheduled = soulbot_db.next_game_db_get(ctx.guild.id)
            if not next_game_scheduled:
                await ctx.send("The next game hasn't been scheduled yet.")
            else:
                next_game_embed = next_game_embed_template(arrow.get(next_game_scheduled[0]))
                await ctx.send(embed=next_game_embed)

    @next_game.group(help="Commands to schedule when the next game is.")
    async def schedule(self, ctx):
        """Schedule sub-command group."""
        if ctx.invoked_subcommand is None:
            await ctx.send(f"Additional arguments requires, see **{ctx.prefix}help next schedule** "
                           f"for available options.")

    @schedule.command(help="Sets the default date/time for the next game. "
                           "Same bat time, 14 days from today.")
    async def default(self, ctx):
        """Schedule command to set the default next game time/date.
        Default: 13:00MT 14 days from date command is run.
        """
        timezones = {"ET": ET, "CT": CT, "MT": MT, "PT": PT}
        default_time_tz, default_interval = soulbot_db.next_game_get_defaults(ctx.guild.id)
        def_time, def_tz = default_time_tz.split()
        def_hour, def_minute = [int(i) for i in def_time.split(":")]
        def_timezone = timezones[def_tz.upper()]
        default_date = arrow.now(def_timezone).replace(hour=def_hour,
                                                       minute=def_minute,
                                                       second=0,
                                                       microsecond=0).shift(days=default_interval)
        soulbot_db.next_game_db_add(default_date.to(UTC).int_timestamp, ctx.guild.id)
        next_game_embed = next_game_embed_template(default_date.to(UTC))
        await ctx.send(embed=next_game_embed)

    @schedule.command(name="date",
                      help="Sets the date of the next game, assumes default start "
                           "time of 1300MT/1500ET. Format=DD/MM/YYYY")
    async def set_date(self, ctx, schedule_date: str = ""):
        """Schedule command to set a specific date for the next game, at the default time.
        Default time: 13:00 MT

        :param schedule_date: Date string
        :param ctx: Discord context object
        """
        try:
            sch_day, sch_month, sch_year = [int(i) for i in schedule_date.split('/')]
            now = arrow.now()
            if not schedule_date:
                await ctx.send("Please use the format: DD/MM/YYYY(EG: 31/05/2020)")
            elif (sch_day > 31) or (sch_month > 12) or (now.year != sch_year != now.year + 1):
                await ctx.send("Please use the format: DD/MM/YYYY(EG: 31/05/2020)")
            else:
                timezones = {"ET": ET, "CT": CT, "MT": MT, "PT": PT}
                default_time_tz, _ = soulbot_db.next_game_get_defaults(ctx.guild.id)
                def_time, def_tz = default_time_tz.split()
                def_hour, def_minute = [int(i) for i in def_time.split(":")]
                def_timezone = timezones[def_tz.upper()]
                output_date = arrow.Arrow(sch_year, sch_month, sch_day, def_hour, def_minute, 0, 0, def_timezone)
                soulbot_db.next_game_db_add(output_date.to(UTC).int_timestamp, ctx.guild.id)
                next_game_embed = next_game_embed_template(output_date.to(UTC))
                await ctx.send(f"Set next game date to {sch_day}/{sch_month}/{sch_year}"
                               f" at the default time.\nUse the **{ctx.prefix}next schedule time** "
                               f"command if you want to change the time.\nAnnouncements are off.",
                               embed=next_game_embed)
        except ValueError:
            await ctx.send("Please use the format: DD/MM/YYYY(EG: 31/05/2020)")

    @schedule.command(name="time",
                      help="Changes the time of the scheduled next game, "
                           "in 24 hour time with timezone.  Format=HH:MM TZ")
    async def set_time(self, ctx, schedule_time: str, schedule_tz: str):
        """Schedule command to change the time of the currently scheduled game.

        :param schedule_time: Time string
        :param schedule_tz: Timezone string
        :param ctx: Discord context object
        """
        timezones = {"ET": ET, "CT": CT, "MT": MT, "PT": PT}
        try:
            sch_hour, sch_minute = [int(i) for i in schedule_time.split(":")]
            if (sch_hour > 24) or (sch_minute > 59):
                await ctx.send("Please use 24 hour time in the format: HH:MM TZ(Eg: 19:00 ET)")
            elif schedule_tz.upper() not in ["ET", "CT", "MT", "PT"]:
                await ctx.send("Please indicate your timezone, ET, CT, MT, or PT.")
            else:
                time_zone = timezones[schedule_tz.upper()]
                next_game_scheduled = arrow.get(soulbot_db.next_game_db_get(ctx.guild.id)[0])
                output_date = next_game_scheduled.to(time_zone).replace(hour=sch_hour,
                                                                        minute=sch_minute,
                                                                        microsecond=0,
                                                                        second=0)
                soulbot_db.next_game_db_add(output_date.to(UTC).int_timestamp, ctx.guild.id)
                next_game_embed = next_game_embed_template(output_date.to(UTC))
                await ctx.send("Next game time successfully set.\nAnnouncements are off.", embed=next_game_embed)
        except ValueError:
            await ctx.send("Please use 24 hour time in the format: HH:MM TZ(Eg: 19:00 ET)")

    @next_game.command(help="Toggles next game announcements.  Options are 'on' or 'off.")
    async def announce(self, ctx, toggle: str = ""):
        """Command to toggle the Next Game announcements in the general channel.

        :param toggle: 'On' or 'Off' string
        :param ctx: Discord context object
        """
        announce_state = soulbot_db.next_game_db_get(ctx.guild.id)[1]
        if not toggle:
            if announce_state:
                await ctx.send("Game announcements are active.")
            else:
                await ctx.send("Game announcements are not active.")
        elif toggle.lower() == "off":
            soulbot_db.next_game_announce_toggle(0, ctx.guild.id)
            await ctx.send("Disabling next game announcements.")
        elif toggle.lower() == "on":
            soulbot_db.next_game_announce_toggle(1, ctx.guild.id)
            await ctx.send("Enabling next game announcements.")
        else:
            await ctx.send("Please specify 'on' or 'off' to toggle game announcements.")

    @set_date.error
    @set_time.error
    async def next_game_error(self, ctx, error):
        """Error catching for the cog."""
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Please use 24 hour time in the format: HH:MM TZ(Eg: 19:00 ET)")
        else:
            await ctx.send(f'Experienced the following error:\n{error}')


def setup(bot):
    """Discord module required setup for Cog loading."""
    bot.add_cog(NextGameScheduler(bot))
