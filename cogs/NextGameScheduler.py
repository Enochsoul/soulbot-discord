# =========================================================
# Next Game
# =========================================================
import discord
from datetime import timedelta, datetime
from discord.ext import commands, tasks
from SQL_io import soulbot_db, GMT, ET, MT, CT, PT


def next_game_embed_template(input_date):
    time_until = input_date - datetime.now(MT)
    days = time_until.days
    hours, remainder = divmod(time_until.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    output_embed = discord.Embed(title=f"__**Next Scheduled Game**__",
                                 description=f"Time until next game: "
                                             f"{days} Days, {hours} Hours, {minutes} Minutes")
    output_embed.add_field(name="__Eastern Time__",
                           value=f"{input_date.astimezone(ET).strftime('%d/%m/%Y %H:%M')}",
                           inline=False)
    output_embed.add_field(name="__Mountain Time__",
                           value=f"{input_date.astimezone(MT).strftime('%d/%m/%Y %H:%M')}",
                           inline=False)
    output_embed.add_field(name="__Pacific Time__",
                           value=f"{input_date.astimezone(PT).strftime('%d/%m/%Y %H:%M')}",
                           inline=False)
    return output_embed


class NextGameScheduler(commands.Cog, name="Next Game Scheduler"):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="next", help="Prints out the date of the next game.")
    async def next_game(self, ctx):
        if ctx.invoked_subcommand is None:
            ng = soulbot_db.next_game_db_get()
            if not ng:
                await ctx.send("The next game hasn't been scheduled yet.")
            else:
                output_date = ng[0].replace(tzinfo=GMT)
                next_game_embed = next_game_embed_template(output_date.astimezone(MT))
                await ctx.send(embed=next_game_embed)

    @next_game.group(help="Commands to schedule when the next game is.")
    async def schedule(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(f"Additional arguments requires, see **{ctx.prefix}help next schedule** "
                           f"for available options.")

    @schedule.command(help="Sets the default date/time for the next game. "
                           "Same bat time, 14 days from today.")
    async def default(self, ctx):
        # Default time is 1PM Mountain time, every 2 weeks.  Change days and hours to update default.
        t = datetime.now().replace(hour=13, minute=0, second=0, microsecond=0)
        d = timedelta(days=14)
        default_date = t + d
        output_date = default_date.astimezone(GMT)
        soulbot_db.next_game_db_add(output_date)
        next_game_embed = next_game_embed_template(default_date.astimezone(MT))
        self.game_announce.start()
        await ctx.send(embed=next_game_embed)

    @schedule.command(name="date",
                      help="Sets the date of the next game, assumes default start "
                           "time of 1300MT/1500ET. Format=DD/MM/YYYY")
    async def set_date(self, ctx, schedule_date: str = ""):
        sch_day, sch_month, sch_year = [int(i) for i in schedule_date.split('/')]
        now = datetime.now()
        if not schedule_date:
            await ctx.send("Please use the format: DD/MM/YYYY(EG: 05/31/2020)")
        elif (sch_day > 31) or (sch_month > 12) or (sch_year != now.year):
            await ctx.send("Please use the format: DD/MM/YYYY(EG: 05/31/2020)")
        else:
            output_date = datetime(2020, sch_month, sch_day, 19, 0, 0, 0, tzinfo=GMT)
            soulbot_db.next_game_db_add(output_date)
            next_game_embed = next_game_embed_template(output_date.astimezone(MT))
            self.game_announce.start()
            await ctx.send(f"Set next game date to {sch_day}/{sch_month}/{sch_year}"
                           f" at the default time.\nUse the **{ctx.prefix}next schedule time** "
                           f"command if you want to change the time.",
                           embed=next_game_embed)

    @schedule.command(name="time",
                      help="Sets the time of the next game, in 24 hour time with timezone. "
                           "Format=HH:MM TZ")
    async def set_time(self, ctx, schedule_time: str, schedule_tz: str):
        sch_hour, sch_minute = [int(i) for i in schedule_time.split(":")]
        if (sch_hour > 24) or (sch_minute > 59):
            await ctx.send("Please use 24 hour time in the format: HH:MM TZ(Eg: 19:00 ET)")
        elif schedule_tz.upper() not in ["ET", "CT", "MT", "PT"]:
            await ctx.send("Please indicate your timezone, ET, CT, MT, or PT.")
        else:
            if schedule_tz.upper() == "ET":
                time_zone = ET
            elif schedule_tz.upper() == "CT":
                time_zone = CT
            elif schedule_tz.upper() == "MT":
                time_zone = MT
            elif schedule_tz.upper() == "PT":
                time_zone = PT
            ng = soulbot_db.next_game_db_get()
            output_date = ng[0].replace(hour=sch_hour, minute=sch_minute, microsecond=0, second=0,
                                        tzinfo=time_zone).astimezone(GMT)
            soulbot_db.next_game_db_add(output_date)
            next_game_embed = next_game_embed_template(output_date.astimezone(MT))
            self.game_announce.start()
            await ctx.send(f"Next game time successfully set.", embed=next_game_embed)

    @next_game.command(help="Toggles next game announcements.  Options are 'on' or 'off.")
    async def announce(self, ctx, toggle: str = ""):
        if not toggle:
            if self.game_announce.next_iteration is not None:
                await ctx.send("Game announcements are active.")
            else:
                await ctx.send("Game announcements are not active.")
        elif toggle.lower() == "off":
            self.game_announce.stop()
            self.game_announce.cancel()
            await ctx.send("Disabling next game announcements.")
        elif toggle.lower() == "on":
            self.game_announce.start()
            await ctx.send("Enabling next game announcements.")
        else:
            await ctx.send("Please specify 'on' or 'off' to toggle game announcements.")

    @tasks.loop(minutes=15)
    async def game_announce(self):
        ng = soulbot_db.next_game_db_get()
        countdown = ng[0].replace(tzinfo=GMT) - datetime.now(GMT)
        for channel in self.bot.get_all_channels():
            if channel.name == "general":
                general_channel = self.bot.get_channel(channel.id)
                break
        if countdown.seconds < 3600 and countdown.days == 0:
            minutes, seconds = divmod(countdown.seconds, 60)
            self.game_announce.stop()
            await general_channel.send(f"@here Next game in {minutes} minutes!\n"
                                       f"Further announcements have been disabled.")

    @set_date.error
    @set_time.error
    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send("Please use 24 hour time in the format: HH:MM TZ(Eg: 19:00 ET)")
        elif isinstance(error, commands.CommandInvokeError):
            await ctx.send("Please use the format: DD/MM/YYYY(EG: 05/31/2020)")
        else:
            await ctx.send(f'Experienced the following error:\n{error}')


def setup(bot):
    bot.add_cog(NextGameScheduler(bot))
