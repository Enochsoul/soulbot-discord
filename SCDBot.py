import os
import random
import re
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv, set_key
from tabulate import tabulate
import sqlite3
from datetime import datetime, tzinfo, timedelta
import time

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
async def on_message_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f"{error}")


# =========================================================
# Initiative Tracker
# =========================================================
class InitiativeTrack:
    def __init__(self):
        self.combatant_dict = {}
        self.tracker = []
        self.tracker_active = False
        self.turn = []
        self.escalation = 0

    def reset(self):
        self.combatant_dict = {}
        self.tracker = []
        self.tracker_active = False
        self.turn = []
        self.escalation = 0

    def build_init_table(self):
        # The combatant dict isn't sorted, create a sorted dict here.
        init_sorted = {k: v for k, v in sorted(self.combatant_dict.items(),
                                               key=lambda i: i[1],
                                               reverse=True)}
        # Create a list of lists from the sorted dict.
        table = [[k, init_sorted[k]] for k in init_sorted]
        # Insert the turn markers to the 0th index of each sub-list.
        for item in table:
            item.insert(0, self.turn[table.index(item)])
        return table

    def embed_template(self):
        tab_tracker = tabulate(self.tracker,
                               headers=["Active", "Player", "Initiative"],
                               tablefmt="fancy_grid")
        embed_template = discord.Embed(title=f"Initiative Order:",
                                       description=f'```{tab_tracker}```',
                                       color=0xff0000)
        embed_template.add_field(name="Tracker Active",
                                 value=f"{self.tracker_active}")
        embed_template.add_field(name="Escalation Die",
                                 value=f"{self.escalation}")
        return embed_template


@bot.group(case_insensitive=True, help="Rolls initiative and builds an order table.")
async def init(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(f"Additional arguments required, "
                       f"see **{ctx.prefix}help init** for available options.")


@init.command(help="Clears the Initiative tracker, and starts a new order.")
async def reset(ctx):
    init_obj.reset()
    c.execute('''DELETE FROM initiative''')
    bot_db.commit()
    await ctx.send("Initiative Tracker is reset and active.")


@init.command(name='roll', help="Rolls your initiative plus the supplied "
                                "bonus and adds you to the order.")
async def init_roll(ctx, init_bonus: int = 0):
    if init_obj.tracker_active is True:
        await ctx.send("Initiative Tracker is locked in an active combat session.")
    elif ctx.author.display_name in init_obj.combatant_dict:
        await ctx.send(f"{ctx.author.display_name} is already in the initiative order.")
    else:
        initiative = die_roll(1, 20)[1]
        init_obj.combatant_dict[ctx.author.display_name] = initiative + init_bonus
        init_obj.turn = ['    ' for i in range(1, len(init_obj.combatant_dict) + 1)]
        init_obj.tracker = init_obj.build_init_table()
        await ctx.send(
            f"{ctx.author.display_name}'s Initiative is ({initiative}+{init_bonus})"
            f" {init_obj.combatant_dict[ctx.author.display_name]}.")


@init.command(help="Starts the tracker and prevents any additions.")
async def start(ctx):
    if len(init_obj.combatant_dict) == 0:
        await ctx.send(f"Please use **{ctx.prefix}init roll** to add to the order first.")
    elif init_obj.tracker_active is True:
        await ctx.send("Tracker is already started.")
    else:
        init_obj.tracker_active = True
        init_obj.turn[0] = '--->'
        init_obj.tracker = init_obj.build_init_table()
        db_insert = [(k, v) for k, v in init_obj.combatant_dict.items()]
        c.execute('''DELETE FROM initiative''')
        c.executemany('''INSERT OR REPLACE INTO initiative(name, init) VALUES(?,?)''', db_insert)
        bot_db.commit()
        embed = init_obj.embed_template()
        await ctx.send(embed=embed)


@init.command(help="Shows current turn order, rolls and tracker status.")
async def show(ctx):
    embed = init_obj.embed_template()
    await ctx.send(embed=embed)


@init.command(name='next', help="Advances the initiative order.")
async def next_turn(ctx):
    if init_obj.tracker_active:
        if init_obj.turn.index('--->') < len(init_obj.combatant_dict) - 1:
            init_obj.turn.insert(0, init_obj.turn.pop(-1))
            init_obj.tracker = init_obj.build_init_table()
            embed = init_obj.embed_template()
            await ctx.send("Beginning next turn.", embed=embed)
        elif init_obj.turn.index('--->') == len(init_obj.combatant_dict) - 1:
            init_obj.turn.insert(0, init_obj.turn.pop(-1))
            init_obj.tracker = init_obj.build_init_table()
            init_obj.escalation += 1
            if init_obj.escalation > 6:
                init_obj.escalation = 6
            embed = init_obj.embed_template()
            await ctx.send("Beginning next combat round.", embed=embed)
    else:
        await ctx.send(f"Tracker not active, use **{ctx.prefix}init start** to begin.")


@init.command(help="Allows a user to delay their turn in the order.")
async def delay(ctx, new_init: int):
    for sublist in init_obj.tracker:
        if '--->' in sublist:
            player_turn = init_obj.tracker[init_obj.tracker.index(sublist)][1]
    if init_obj.tracker_active is False:
        await ctx.send(f"Tracker not active, use **{ctx.prefix}init start** to begin.")
    elif ctx.author.display_name not in init_obj.combatant_dict:
        await ctx.send(f"{ctx.author.display_name} is not in the initiative order.")
    elif new_init > init_obj.combatant_dict[ctx.author.display_name]:
        await ctx.send(
            f"New initiative({new_init}) must be lower than original"
            f"({init_obj.combatant_dict[ctx.author.display_name]}).")
    elif ctx.author.display_name != player_turn:
        await ctx.send(f"Delay should be done on your turn.")
    else:
        init_obj.combatant_dict[ctx.author.display_name] = new_init
        init_obj.tracker = init_obj.build_init_table()
        db_insert = [(k, v) for k, v in init_obj.combatant_dict.items()]
        c.executemany('''INSERT OR REPLACE INTO initiative(name, init) VALUES(?,?)''', db_insert)
        bot_db.commit()
        embed = init_obj.embed_template()
        await ctx.send(
            f"Initiative for {ctx.author.display_name} has been delayed to "
            f"{init_obj.combatant_dict[ctx.author.display_name]}. "
            f"Initiative order has been recalculated.", embed=embed)


@init.group(case_insensitive=True, help="Commands for the DM.")
@commands.has_role("DM" or "GM")
async def dm(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(f"Additional arguments required, see "
                       f"**{ctx.prefix}help init dm** for available options.")


@dm.command(help="Add NPCs/Monsters to the initiative order, before or during active combat.")
async def npc(ctx, npc_name: str, init_bonus: int = 0):
    for sublist in init_obj.tracker:
        if '--->' in sublist:
            player_turn = init_obj.tracker[init_obj.tracker.index(sublist)][1]
    if init_obj.tracker_active:
        initiative = die_roll(1, 20)[1]
        init_obj.combatant_dict[npc_name] = initiative + init_bonus
        init_obj.turn = ['    ' for i in range(1, len(init_obj.combatant_dict) + 1)]
        init_obj.tracker = init_obj.build_init_table()
        db_insert = [(k, v) for k, v in init_obj.combatant_dict.items()]
        c.executemany('''INSERT OR REPLACE INTO initiative(name, init) VALUES(?,?)''', db_insert)
        bot_db.commit()
        for sublist in init_obj.tracker:
            if player_turn in sublist:
                init_obj.tracker[init_obj.tracker.index(sublist)][0] = '--->'
                init_obj.turn[init_obj.tracker.index(sublist)] = '--->'
        await ctx.send(f"Adding {npc_name} to active combat round.\n"
                       f"Initiative is ({initiative}+{init_bonus}) "
                       f"{init_obj.combatant_dict[npc_name]}.")
    elif npc_name in init_obj.combatant_dict:
        await ctx.send(f"{npc_name} is already used in the initiative order.")
    else:
        initiative = die_roll(1, 20)[1]
        init_obj.combatant_dict[npc_name] = initiative + init_bonus
        init_obj.turn = ['    ' for i in range(1, len(init_obj.combatant_dict) + 1)]
        init_obj.tracker = init_obj.build_init_table()
        await ctx.send(f"{npc_name}'s Initiative is ({initiative}+{init_bonus}) "
                       f"{init_obj.combatant_dict[npc_name]}.")


@dm.command(help="Allows DM to manipulate the Escalation Die.  Value can be plus or minus.")
async def escalate(ctx, value_change: int):
    if init_obj.tracker_active is True:
        init_obj.escalation = init_obj.escalation + value_change
        if init_obj.escalation > 6:
            init_obj.escalation = 6
        await ctx.send(f"Escalation die is now {init_obj.escalation}")
    else:
        await ctx.send(f"Tracker not active, use **{ctx.prefix}init start** to begin.")


@dm.command(name='delay', help="Allows DM to delay NPC/Monster turns.")
async def dm_delay(ctx, npc_name: str, new_init: int):
    for sublist in init_obj.tracker:
        if '--->' in sublist:
            npc_turn = init_obj.tracker[init_obj.tracker.index(sublist)][1]
            break
        else:
            npc_turn = ''
    if init_obj.tracker_active is False:
        await ctx.send(f"Tracker not active, use **{ctx.prefix}init start** to begin.")
    elif npc_name not in init_obj.combatant_dict:
        await ctx.send(f"{npc_name} is not in the initiative order.")
    elif npc_name != npc_turn:
        await ctx.send(f"Delay should be done on the NPCs turn.")
    else:
        init_obj.combatant_dict[npc_name] = new_init
        init_obj.tracker = init_obj.build_init_table()
        db_insert = [(k, v) for k, v in init_obj.combatant_dict.items()]
        c.executemany('''INSERT OR REPLACE INTO initiative(name, init) VALUES(?,?)''', db_insert)
        bot_db.commit()
        embed = init_obj.embed_template()
        await ctx.send(
            f"Initiative for {npc_name} has been delayed to {init_obj.combatant_dict[npc_name]}. "
            f"Initiative order has been recalculated", embed=embed)


@dm.command(help='Allows DM to remove someone(player or NPC) from the initiative order.  '
                 'Specified name for NPCs is case sensitive, use "" around name if '
                 'it includes spaces.  Players can be @ mentioned.')
async def remove(ctx, name: str):
    if "!" and "@" in name:
        mention_user = name.replace("<", "").replace(">", "").replace("@", "").replace("!", "")
        name = ctx.guild.get_member(int(mention_user)).display_name
    if name not in init_obj.combatant_dict:
        await ctx.send(f"{name} is not in the initiative order.")
    elif init_obj.tracker_active:
        for sublist in init_obj.tracker:
            if '--->' in sublist:
                active_user = init_obj.tracker[init_obj.tracker.index(sublist)][1]
        if active_user == name:
            await ctx.send(f"{name} is the active combatant, "
                           f"please advance the turn before removing them.")
        else:
            del init_obj.combatant_dict[name]
            init_obj.turn = ['    ' for i in range(1, len(init_obj.combatant_dict) + 1)]
            init_obj.tracker = init_obj.build_init_table()
            db_insert = [(k, v) for k, v in init_obj.combatant_dict.items()]
            c.execute('''DELETE from initiative''')
            c.executemany('''INSERT OR REPLACE INTO initiative(name, init) VALUES(?,?)''',
                          db_insert)
            bot_db.commit()
            for sublist in init_obj.tracker:
                if active_user in sublist:
                    init_obj.tracker[init_obj.tracker.index(sublist)][0] = '--->'
                    init_obj.turn[init_obj.tracker.index(sublist)] = '--->'
            await ctx.send(
                f"{name} has been removed from the initiative table.")
    else:
        del init_obj.combatant_dict[name]
        init_obj.turn = ['    ' for i in range(1, len(init_obj.combatant_dict) + 1)]
        init_obj.tracker = init_obj.build_init_table()
        await ctx.send(
            f"{name} has been removed from the initiative table.")


@dm.command(help='Allows DM to manually update an NPC or player\'s init score.  '
                 'Specified name for NPCs is case sensitive, use "" around the name '
                 'if it includes spaces.  Players must be @ mentioned.')
async def update(ctx, name: str, new_init: int):
    if "!" and "@" in name:
        mention_user = name.replace("<", "").replace(">", "").replace("@", "").replace("!", "")
        name = ctx.guild.get_member(int(mention_user)).display_name
    if name not in init_obj.combatant_dict:
        await ctx.send(f"{name} is not in the initiative order.")
    elif init_obj.tracker_active is False:
        init_obj.combatant_dict[name] = new_init
        init_obj.tracker = init_obj.build_init_table()
        await ctx.send(f"{name}'s initiative has been manually set to {new_init}.")
    else:
        init_obj.combatant_dict[name] = new_init
        init_obj.tracker = init_obj.build_init_table()
        db_insert = [(k, v) for k, v in init_obj.combatant_dict.items()]
        c.executemany('''INSERT OR REPLACE INTO initiative(name, init) VALUES(?,?)''', db_insert)
        bot_db.commit()
        await ctx.send(f"{name}'s initiative has been manually set to {new_init}.")


@dm.command(help='Allows DM to manually change who is the active combatant.')
async def active(ctx, name: str):
    if "!" and "@" in name:
        mention_user = name.replace("<", "").replace(">", "").replace("@", "").replace("!", "")
        name = ctx.guild.get_member(int(mention_user)).display_name
    if not init_obj.tracker_active:
        await ctx.send(f"Initiative tracker is not active.")
    else:
        init_obj.turn = ['    ' for i in range(1, len(init_obj.combatant_dict) + 1)]
        for sublist in init_obj.tracker:
            if name in sublist:
                init_obj.turn[init_obj.tracker.index(sublist)] = '--->'
                init_obj.tracker = init_obj.build_init_table()
        embed = init_obj.embed_template()
        await ctx.send(f"{name} is now the active combatant.", embed=embed)


@dm.command(
    help="DON'T DO THIS UNLESS YOU MEAN IT. Rebuild the init tracker from the backup database.  "
         "Deactivates and resets the tracker, and resets the escalation die.")
async def rebuild(ctx):
    init_obj.reset()
    c.execute('''SELECT name, init FROM initiative''')
    all_rows = c.fetchall()
    init_obj.combatant_dict = {i[0]: i[1] for i in all_rows}
    init_obj.turn = ['    ' for i in range(1, len(init_obj.combatant_dict) + 1)]
    init_obj.tracker = init_obj.build_init_table()
    embed = init_obj.embed_template()
    await ctx.send(f"Initiative tracker has been reset and rebuilt from the backup database.",
                   embed=embed)


@dm.error
@npc.error
@update.error
@rebuild.error
async def on_dm_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send(f"{error}")
    elif isinstance(error, commands.errors.CommandInvokeError):
        print(error)
        await ctx.send(f"Something went wrong, check the bot output.")
    elif isinstance(error, commands.errors.MissingRequiredArgument):
        print(error)
        await ctx.send(f"Missing required arguments, please check help for command syntax.")


@init_roll.error
async def on_roll_error(ctx, error):
    if isinstance(error, commands.CommandInvokeError):
        print(error)
        await ctx.send("Tracker is not started.")


# =========================================================
# Dice roller
# =========================================================

@bot.command(help="Dice roller.  Expected format: NdN+N.(Ex: 2d6+2)")
async def roll(ctx, *, dice_roll: str):
    plus_modifier_pattern = "[0-9]+d[0-9]+\\+[0-9]+"
    minus_modifier_pattern = "[0-9]+d[0-9]+\\-[0-9]+"
    normal_pattern = "[0-9]+d[0-9]+"
    plus_match_with_modifier = bool(re.fullmatch(plus_modifier_pattern, dice_roll))
    minus_match_with_modifier = bool(re.fullmatch(minus_modifier_pattern, dice_roll))
    match_without_modifier = bool(re.fullmatch(normal_pattern, dice_roll))
    if plus_match_with_modifier:
        modifier = int(dice_roll.split("+")[1])
        dice = dice_roll.split("+")[0]
        result_list, result_total = die_roll(int(dice.split("d")[0]), int(dice.split("d")[1]))
        await ctx.send(f"{ctx.author.mention} rolled **{result_total + modifier}**."
                       f" ({result_list}+{modifier})")
    elif minus_match_with_modifier:
        modifier = int(dice_roll.split("-")[1])
        dice = dice_roll.split("-")[0]
        result_list, result_total = die_roll(int(dice.split("d")[0]), int(dice.split("d")[1]))
        await ctx.send(f"{ctx.author.mention} rolled **{result_total - modifier}**."
                       f" ({result_list}-{modifier})")
    elif match_without_modifier:
        dice = dice_roll.split("+")[0]
        result_list, result_total = die_roll(int(dice.split("d")[0]), int(dice.split("d")[1]))
        if int(dice.split("d")[0]) == 1:
            await ctx.send(f"{ctx.author.mention} rolled **{result_total}**.")
        else:
            await ctx.send(f"{ctx.author.mention} rolled **{result_total}**. ({result_list})")
    else:
        await ctx.send(f"Dice rolls should be in the format: NdN+N")


@bot.command(help="Rolls 1d20 + supplied player bonus(Stat + Level) "
                  "to attack, command automatically includes "
                  "escalation die(if any). Default bonus = 0")
async def attack(ctx, bonus: int = 0):
    crit = ":x:"
    vuln_crit = ":x:"
    attack_roll = die_roll(1, 20)
    attack_natural = attack_roll[1]
    attack_modified = attack_natural + bonus + init_obj.escalation
    if attack_natural == 20:
        crit = ":white_check_mark:"
    if attack_natural >= 18:
        vuln_crit = ":white_check_mark:"
    math = f"|| ({attack_natural} + {bonus} + {init_obj.escalation} = {attack_modified}) ||"
    attack_embed = discord.Embed(title=f"__**Attack Result**__",
                                 description=f"{attack_modified}\n{math}",
                                 color=0x0000ff)
    attack_embed.add_field(name="Natural Roll",
                           value=f"{attack_natural}",
                           inline=False)
    attack_embed.add_field(name="Natural Crit",
                           value=f"{crit}",
                           inline=True)
    attack_embed.add_field(name="Element Crit",
                           value=f"{vuln_crit}",
                           inline=True)
    attack_embed.add_field(name="Escalation",
                           value=f"{init_obj.escalation}",
                           inline=True)
    await ctx.send(f"{ctx.author.mention} rolled to attack.",
                   embed=attack_embed)


@bot.command(help="Roll 1d20 + supplied NPC bonus to attack, "
                  "excludes escalation die. Default bonus = 0")
async def attacknpc(ctx, bonus: int = 0):
    crit = ":x:"
    vuln_crit = ":x:"
    attack_roll = die_roll(1, 20)
    attack_natural = attack_roll[1]
    attack_modified = attack_natural + bonus
    if attack_natural == 20:
        crit = ":white_check_mark:"
    if attack_natural >= 18:
        vuln_crit = ":white_check_mark:"
    math = f"|| ({attack_natural} + {bonus} = {attack_modified}) ||"
    attack_embed = discord.Embed(title=f"__**Attack Result**__",
                                 description=f"{attack_modified}\n{math}",
                                 color=0x0000ff)
    attack_embed.add_field(name="Natural Roll",
                           value=f"{attack_natural}",
                           inline=False)
    attack_embed.add_field(name="Natural Crit",
                           value=f"{crit}", inline=True)
    attack_embed.add_field(name="Element Crit",
                           value=f"{vuln_crit}",
                           inline=True)
    attack_embed.add_field(name="Escalation",
                           value=f"N/A",
                           inline=True)
    await ctx.send(f"{ctx.author.mention} rolled an **NPC attack**.",
                   embed=attack_embed)


# =========================================================
# Quotes
# =========================================================

@bot.group(help="Display a random quote submitted to the database, or one containing .")
async def quote(ctx):
    if ctx.invoked_subcommand is None:
        c.execute('''SELECT * FROM quotes''')
        count = len(c.fetchall())
        if count > 0:
            c.execute('''SELECT quote FROM quotes ORDER BY RANDOM() LIMIT 1''')
            quote_text = c.fetchone()[0]
            await ctx.send(f'QUOTE: "{quote_text}"')
        else:
            await ctx.send(f"No quotes in the database.")


@quote.group(name="addquote", help="Add a quote to the database.")
async def add_quote(ctx, *, quote_text: str):
    c.execute('''INSERT INTO quotes(quote) VALUES(?)''', (quote_text,))
    bot_db.commit()
    await ctx.send(f'Added "{str(quote_text)}" to quotes database.')


@quote.group(name='search', help='Search for a quote containing a specific term.')
async def quote_search(ctx, *, search_term: str):
    c.execute('''SELECT quote FROM quotes where quote LIKE ?''', ("%" + str(search_term) + "%",))
    quote_text = c.fetchall()
    if len(quote_text) > 0:
        random_index = random.randint(0, len(quote_text) - 1)
        await ctx.send(f'QUOTE: "{quote_text[random_index][0]}"')
    else:
        await ctx.send(f'No quote found with the term "{search_term}"')


# =========================================================
# Next Game
# =========================================================

@bot.group(name="next", help="Prints out the date of the next game.")
async def nextgame(ctx):
    if ctx.invoked_subcommand is None:
        c.execute('''SELECT next_date FROM next_game where id=?''', (1,))
        ng = c.fetchone()
        if not ng:
            await ctx.send("The next game hasn't been scheduled yet.")
        else:
            output_date = ng[0].replace(tzinfo=GMT)
            nextgame_embed = nextgame_embed_template(output_date.astimezone(MT))
            await ctx.send(embed=nextgame_embed)


@nextgame.group(help="Commands to schedule when the next game is.")
async def schedule(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(f"Additional arguments requires, see **{ctx.prefix}help next schedule** "
                       f"for available options.")


@schedule.command(help="Sets the default date/time for the next game. "
                       "Same bat time, 14 days from today.")
async def default(ctx):
    # Default time is 1PM Mountain time, every 2 weeks.  Change days and hours to update default.
    t = datetime.now().replace(hour=13, minute=0, second=0, microsecond=0)
    d = timedelta(days=14)
    default_date = t + d
    output_date = default_date.astimezone(GMT)
    c.execute(
        '''INSERT OR REPLACE INTO next_game(id, created_date, next_date) VALUES(?,?,?)''',
        (1, datetime.today(), output_date.replace(tzinfo=None)))
    bot_db.commit()
    nextgame_embed = nextgame_embed_template(default_date.astimezone(MT))
    await ctx.send(embed=nextgame_embed)


@schedule.command(name="date",
                  help="Sets the date of the next game, assumes default start "
                       "time of 1300MT/1500ET. Format=DD/MM/YYYY")
async def setdate(ctx, schedule_date: str = ""):
    sch_day, sch_month, sch_year = [int(i) for i in schedule_date.split('/')]
    now = datetime.now()
    if not schedule_date:
        await ctx.send("Please use the format: DD/MM/YYYY(EG: 05/31/2020)")
    elif (sch_day > 31) or (sch_month > 12) or (sch_year != now.year):
        await ctx.send("Please use the format: DD/MM/YYYY(EG: 05/31/2020)")
    else:
        output_date = datetime(2020, sch_month, sch_day, 19, 0, 0, 0, tzinfo=GMT)
        c.execute(
            '''INSERT OR REPLACE INTO next_game(id, created_date, next_date) VALUES(?,?,?)''',
            (1, datetime.today(), output_date.replace(tzinfo=None)))
        bot_db.commit()
        nextgame_embed = nextgame_embed_template(output_date.astimezone(MT))
        await ctx.send(f"Set next game date to {sch_day}/{sch_month}/{sch_year}"
                       f" at the default time.\nUse the **{ctx.prefix}next schedule time** "
                       f"command if you want to change the time.",
                       embed=nextgame_embed)


@schedule.command(name="time",
                  help="Sets the time of the next game, in 24 hour time with timezone. "
                       "Format=HH:MM TZ")
async def settime(ctx, schedule_time: str, schedule_tz: str):
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
        c.execute('''SELECT next_date FROM next_game WHERE id=?''', (1,))
        ng = c.fetchone()
        output_date = ng[0].replace(hour=sch_hour, minute=sch_minute, microsecond=0, second=0,
                                    tzinfo=time_zone).astimezone(GMT)
        c.execute(
            '''INSERT OR REPLACE INTO next_game(id, created_date, next_date) VALUES(?,?,?)''',
            (1, datetime.today(),
             output_date.replace(tzinfo=None)))
        bot_db.commit()
        nextgame_embed = nextgame_embed_template(output_date.astimezone(MT))
        await ctx.send(f"Next game time successfully set.", embed=nextgame_embed)


@nextgame.command(help="Toggles next game announcements.  Options are 'on' or 'off.")
async def announce(ctx, toggle: str = ""):
    if not toggle:
        if game_announce.next_iteration is not None:
            await ctx.send("Game announcements are active.")
        else:
            await ctx.send("Game announcements are not active.")
    elif toggle.lower() == "off":
        game_announce.stop()
        game_announce.cancel()
        await ctx.send("Disabling next game announcements.")
    elif toggle.lower() == "on":
        game_announce.start()
        await ctx.send("Enabling next game announcements.")
    else:
        await ctx.send("Please specify 'on' or 'off' to toggle game announcements.")


def nextgame_embed_template(input_date):
    time_until = input_date - datetime.now(MT)
    days = time_until.days
    hours, remainder = divmod(time_until.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
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


@tasks.loop(minutes=15)
async def game_announce():
    c.execute('''SELECT next_date FROM next_game WHERE id=?''', (1,))
    ng = c.fetchone()
    countdown = ng[0].replace(tzinfo=GMT) - datetime.now(GMT)
    for channel in bot.get_all_channels():
        if channel.name == "general":
            general_channel = bot.get_channel(channel.id)
            break
    if countdown.seconds < 3600 and countdown.days == 0:
        minutes, seconds = divmod(countdown.seconds, 60)
        game_announce.stop()
        await general_channel.send(f"@here Next game in {minutes} minutes!\n"
                                   f"Further announcements have been disabled.")


@settime.error
async def on_settime_error(ctx, error):
    if isinstance(error, commands.CommandInvokeError):
        await ctx.send("Please use 24 hour time in the format: HH:MM TZ(Eg: 19:00 ET)")


@setdate.error
async def on_setdate_error(ctx, error):
    if isinstance(error, commands.CommandInvokeError):
        await ctx.send("Please use the format: DD/MM/YYYY(EG: 05/31/2020)")


# =========================================================
# Common Functions
# =========================================================


def die_roll(die_count, die_size):
    count = die_count
    result = []
    while count > 0:
        result.append(random.randint(1, die_size))
        count -= 1
    total = sum(result)
    bold_item = [f"**{item}**" if item == die_size else str(item) for item in result]
    result_list = "+".join(bold_item)
    return result_list, total


class Zone(tzinfo):
    def __init__(self, offset, isdst, name):
        self.offset = offset
        self.isdst = isdst
        self.name = name

    def utcoffset(self, dt):
        return timedelta(hours=self.offset) + self.dst(dt)

    def dst(self, dt):
        return timedelta(hours=1) if self.isdst else timedelta(0)

    def tzname(self, dt):
        return self.name


daylight_check = bool(time.daylight)

GMT = Zone(0, False, 'GMT')
ET = Zone(-5, daylight_check, 'ET')
CT = Zone(-6, daylight_check, 'CT')
MT = Zone(-7, daylight_check, 'MT')
PT = Zone(-8, daylight_check, 'PT')


# =========================================================
# Bot Start
# =========================================================

@bot.event
async def on_ready():
    print(f"{bot.user.name} has connected to Discord.")


if __name__ == "__main__":
    init_obj = InitiativeTrack()
    bot_db = sqlite3.connect('data/discordbot.sql',
                             detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    c = bot_db.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS next_game
              (id INTEGER PRIMARY KEY, created_date timestamp, next_date timestamp)''')
    c.execute('''CREATE TABLE IF NOT EXISTS quotes
              (id INTEGER PRIMARY KEY, quote TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS initiative
              (name TEXT UNIQUE PRIMARY KEY, init INTEGER)''')
    bot_db.commit()
    bot.run(token)
