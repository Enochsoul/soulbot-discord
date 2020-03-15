import json
import os
import random
import re
import discord
from discord.ext import commands
from dotenv import load_dotenv, set_key
from tabulate import tabulate

load_dotenv()

token = os.getenv('DISCORD_TOKEN')
command_prefix = os.getenv('COMMAND_PREFIX')

client = discord.Client()

bot = commands.Bot(command_prefix=command_prefix)


@bot.command(help="Changes the bot command prefix.  Default=!")
@commands.has_guild_permissions(manage_guild=True)
async def setprefix(ctx, prefix: str):
    set_key('.env', 'COMMAND_PREFIX', prefix)
    await ctx.send(f"Prefix now set to {prefix}.")


@setprefix.error
async def on_message_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f"{error}")


# =========================================================
# Initiative Tracker
# =========================================================

init_dict = {}
init_tracker = []
init_active = False
init_turn = 0
multiplier = 0
escalation = 0


@bot.group(help="Rolls initiative and builds an order table.")
async def init(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(f"Additional arguments required, see **{ctx.prefix}help init** for available options.")


@init.command(help="Clears the Initiative tracker, and starts a new order.")
async def reset(ctx):
    global init_dict
    global init_turn
    global init_active
    global init_tracker
    global multiplier
    init_active = False
    init_tracker = []
    init_dict = {}
    init_turn = 0
    multiplier = 0
    await ctx.send("Initiative Tracker is reset and active.")


@init.command(help="Rolls your initiative plus the supplied bonus and adds you to the order.")
async def roll(ctx, init_bonus: int):
    global init_active
    global init_dict
    if init_active is True:
        await ctx.send("Initiative Tracker is locked in an active combat session.")
    elif ctx.author.display_name in init_dict:
        await ctx.send(f"{ctx.author.display_name} is already in the initiative order.")
    else:
        initiative = die_roll(1, 20)[1]
        init_dict[ctx.author.display_name] = initiative + init_bonus
        await ctx.send(
            f"{ctx.author.display_name}'s Initiative is ({initiative}+{init_bonus}) {init_dict[ctx.author.display_name]}.")


@init.command(help="Starts the tracker and prevents any additions.")
async def start(ctx):
    global init_active
    global init_dict
    global init_turn
    global init_tracker
    global multiplier
    global escalation
    if len(init_dict) == 0:
        await ctx.send(f"Please use **{ctx.prefix}init roll** to add to the order first.")
    elif init_active is True:
        await ctx.send("Tracker is already started.")
    else:
        init_tracker = init_table(init_dict)
        init_active = True
        init_tracker[init_turn][0] = "--->"
        embed = init_embed_template(init_tracker)
        await ctx.send(embed=embed)


@init.command(help="Shows current turn order, rolls and tracker status.")
async def show(ctx):
    global init_turn
    global init_active
    global init_tracker
    global multiplier
    global escalation
    if init_active is False:
        init_tracker = init_table(init_dict)
        embed = init_embed_template(init_tracker)
        await ctx.send(embed=embed)
    else:
        embed = init_embed_template(init_tracker)
        await ctx.send(embed=embed)


@init.command(help="Advances the initiative order.")
async def next(ctx):
    global init_turn
    global init_active
    global multiplier
    global escalation
    if init_active:
        if init_turn >= (multiplier * len(init_tracker)):
            init_turn += 1
            if init_turn % len(init_tracker) == 0:
                multiplier += 1
                escalation += 1
                if escalation > 6:
                    escalation = 6
            init_tracker[-1][0] = "    "
            init_tracker[init_turn - (multiplier * len(init_tracker))][0] = "--->"
            init_tracker[init_turn - ((multiplier * len(init_tracker)) + 1)][0] = "    "
            embed = init_embed_template(init_tracker)
            await ctx.send("Beginning next turn.", embed=embed)
    else:
        await ctx.send(f"Tracker not active, use **{ctx.prefix}init start** to begin.")


@init.command(help="Allows a user to delay their turn in the order.")
async def delay(ctx, new_init: int):
    global init_active
    global init_tracker
    global init_dict
    if init_active is False:
        await ctx.send(f"Tracker not active, use **{ctx.prefix}init start** to begin.")
    elif ctx.author.display_name not in init_dict:
        await ctx.send(f"{ctx.author.display_name} is not in the initiative order.")
    elif new_init > init_dict[ctx.author.display_name]:
        await ctx.send(
            f"New initiative({new_init}) must be lower than original({init_dict[ctx.author.display_name]}).")
    else:
        init_dict[ctx.author.display_name] = new_init
        init_tracker = init_table(init_dict)
        init_tracker[init_turn - (multiplier * len(init_tracker))][0] = "--->"
        await ctx.send(
            f"Initiative for {ctx.author.display_name} has been delayed to {init_dict[ctx.author.display_name]}.")


@init.group(help="Commands for the DM.")
@commands.has_role("DM" or "GM")
async def dm(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(f"Additional arguments required, see **{ctx.prefix}help init dm** for available options.")


@dm.command(help="Add NPCs/Monsters to the initiative order.")
async def npc(ctx, npc_name: str, init_bonus: int):
    global init_active
    global init_dict
    if init_active is True:
        await ctx.send("Initiative Tracker is locked in an active turn.")
    elif npc_name in init_dict:
        await ctx.send(f"{npc_name} is already used in the initative order.")
    else:
        initiative = die_roll(1, 20)[1]
        init_dict[npc_name] = initiative + init_bonus
        await ctx.send(f"{npc_name}'s Initiative is ({initiative}+{init_bonus}) {init_dict[npc_name]}.")


@dm.command(help="Allows DM to manipulate the Escalation Die.  Value can be plus or minus.")
async def escalate(ctx, value_change: int):
    global escalation
    if init_active is True:
        escalation = escalation + value_change
        if escalation > 6:
            escalation = 6
        await ctx.send(f"Escalation die is now {escalation}")
    else:
        await ctx.send(f"Tracker not active, use **{ctx.prefix}init start** to begin.")


@dm.command(help="Allows DM to delay NPC/Monster turns.")
async def delay(ctx, npc_name: str, new_init: int):
    global init_active
    global init_tracker
    global init_dict
    if init_active is False:
        await ctx.send(f"Tracker not active, use **{ctx.prefix}init start** to begin.")
    elif npc_name not in init_dict:
        await ctx.send(f"{npc_name} is not in the initiative order.")
    elif new_init > init_dict[npc_name]:
        await ctx.send(
            f"New initiative({new_init}) must be lower than original({init_dict[npc_name]}).")
    else:
        init_dict[npc_name] = new_init
        init_tracker = init_table(init_dict)
        init_tracker[init_turn - (multiplier * len(init_tracker))][0] = "--->"
        await ctx.send(
            f"Initiative for {npc_name} has been delayed to {init_dict[npc_name]}.")


@dm.command(help="Allows DM to remove someone(player or NPC) from the initiative order.")
async def remove(ctx, name: str):
    global init_active
    global init_tracker
    global init_dict
    if name not in init_dict:
        await ctx.send(f"{name} is not in the initiative order.")
    else:
        del init_dict[name]
        init_tracker = init_table(init_dict)
        init_tracker[init_turn - (multiplier * len(init_tracker))][0] = "--->"
        await ctx.send(
            f"{name} has been removed from the initiative table.")


def init_table(init_dictionary):
    table = []
    init_sorted = {k: v for k, v in sorted(init_dictionary.items(), key=lambda item: item[1], reverse=True)}
    for k in init_sorted:
        table.append(["    ", k, init_sorted[k]])
    return table


def init_embed_template(tracker):
    tab_tracker = tabulate(tracker, headers=["Active", "Player", "Initiative"], tablefmt="fancy_grid")
    embed_template = discord.Embed(title=f"Initiative Order:", description=f'```{tab_tracker}```', color=0xff0000)
    embed_template.add_field(name="Tracker Active", value=f"{init_active}")
    embed_template.add_field(name="Combat Round", value=f"{multiplier + 1}\n")
    embed_template.add_field(name="Escalation Die", value=f"{escalation}")
    return embed_template


@dm.error
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send(f"{error}")


@roll.error
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandInvokeError):
        await ctx.send("Tracker is not started.")


# =========================================================
# XP Tracker
# =========================================================

player_xp = {}


@bot.group(help="DM tool to track XP for players.")
async def xp(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(f"Missing arguments, please see **{command_prefix}help xp** for usage.")


@xp.command(help="Assigns XP to a player.  Use player name all to give to all players.")
@commands.has_role("DM" or "GM")
async def award(ctx, player: str, xp_award: int):
    global player_xp
    guild_id = str(ctx.guild.id)
    if player == "all":
        for k in player_xp[guild_id]:
            player_xp[guild_id][k] += xp_award
        await ctx.send(f"Gave all players {xp_award}XP.")
    elif player.startswith("<@!"):
        player_id = int(player.strip("<>@!"))
        player_info = ctx.guild.get_member(player_id)
        player_name = player_info.display_name
        if player_name in player_xp[guild_id].keys():
            player_xp[guild_id][player_name] += xp_award
            await ctx.send(f"Gave {player_name} {xp_award}XP. Total XP: {player_xp[guild_id][player_name]}")
        else:
            player_xp[guild_id].update({player_name: xp_award})
            await ctx.send(f"Gave {player_name} {xp_award}XP. Total XP: {player_xp[guild_id][player_name]}")
    else:
        ctx.send(f"Please @ mention players to award them XP.")
    file_update(player_xp)


@xp.command(help="Initializes new XP Tracker.")
@commands.has_role("DM" or "GM")
async def initialize(ctx):
    keys = player_xp.keys()
    guild_id = str(ctx.guild.id)
    if guild_id not in keys:
        player_xp[guild_id] = ""
        file_update(player_xp)
        await ctx.send(f"XP Tracker initialized for {ctx.guild.name}.")
    else:
        await ctx.send(f"XP Tracker already initialised.")


@xp.command(help="Show XP tracker")
async def show(ctx):
    global player_xp
    guild_id = str(ctx.guild.id)
    embed = discord.Embed(title=f"XP Table:",
                          description=f'```{tabulate(xp_table(player_xp, guild_id), headers=["Player", "XP"], tablefmt="fancy_grid")}```',
                          color=0xff0000)
    await ctx.send(embed=embed)


@xp.error
@award.error
async def on_command_error(ctx, error):
    if isinstance(error, (commands.MissingRole, commands.MissingRequiredArgument)):
        await ctx.send(f"{error}")


def xp_table(xp_list, guild_id):
    table = [(k, v) for (k, v) in xp_list[guild_id].items() if v > 0]
    return table


def file_update(player_dict):
    filename = "player_xp.json"
    with open("./data/" + filename, "+w") as file:
        json.dump(player_dict, file)


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
        result = die_roll(int(dice.split("d")[0]), int(dice.split("d")[1]))
        result_total = result[1]
        result_list = result[0]
        await ctx.send(f"{ctx.author.mention} rolled **{result_total + modifier}**. ({result_list}+{modifier})")
    elif minus_match_with_modifier:
        modifier = int(dice_roll.split("-")[1])
        dice = dice_roll.split("-")[0]
        result = die_roll(int(dice.split("d")[0]), int(dice.split("d")[1]))
        result_total = result[1]
        result_list = result[0]
        await ctx.send(f"{ctx.author.mention} rolled **{result_total - modifier}**. ({result_list}-{modifier})")
    elif match_without_modifier:
        dice = dice_roll.split("+")[0]
        result = die_roll(int(dice.split("d")[0]), int(dice.split("d")[1]))
        result_total = result[1]
        result_list = result[0]
        if int(dice.split("d")[0]) == 1:
            await ctx.send(f"{ctx.author.mention} rolled **{result_total}**.")
        else:
            await ctx.send(f"{ctx.author.mention} rolled **{result_total}**. ({result_list})")
    else:
        await ctx.send(f"Dice rolls should be in the format: NdN+N")


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


# =========================================================
# Bot Start
# =========================================================
@bot.event
async def on_ready():
    print(f"{bot.user.name} has connected to Discord.")
    xp_filename = "player_xp.json"
    global player_xp
    with os.scandir(path="data/") as data_dir:
        xp_file = [entry.name for entry in data_dir if entry.name == xp_filename]
    if len(xp_file) == 0:
        with open("./data/" + xp_filename, "+w") as file:
            print("Loading new XP File.")
            json.dump(player_xp, file)
    else:
        with open("./data/" + xp_file[0]) as player_data:
            print("Loading data.")
            if os.stat("./data/" + xp_filename).st_size > 0:
                player_xp = json.load(player_data)


bot.run(token)
