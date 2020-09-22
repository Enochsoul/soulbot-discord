"""Cog for tracking Initiative and attack rolls."""
import discord
from discord.ext import commands
from tabulate import tabulate
from soulbot_support import soulbot_db
from DiceRoller import die_roll


class InitiativeTrack:
    """Class definition for the Initiative tracking object."""
    def __init__(self):
        self.combatant_dict = {}
        self.tracker = []
        self.tracker_active = False
        self.turn = []
        self.escalation = 0

    def reset(self):
        """Resets all tracking values to defaults."""
        self.combatant_dict = {}
        self.tracker = []
        self.tracker_active = False
        self.turn = []
        self.escalation = 0

    def build_init_table(self):
        """Takes combatant dictionary, sorts it by key value,
        then builds the initiative activity table.
        """
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
        """Initiative tracker embed generator."""
        tab_tracker = tabulate(self.tracker,
                               headers=["Active", "Player", "Initiative"],
                               tablefmt="fancy_grid")
        embed_template = discord.Embed(title="Initiative Order:",
                                       description=f'```{tab_tracker}```',
                                       color=0xff0000)
        embed_template.add_field(name="Tracker Active",
                                 value=f"{self.tracker_active}")
        embed_template.add_field(name="Escalation Die",
                                 value=f"{self.escalation}")
        return embed_template


init_obj = InitiativeTrack()


class InitiativeTracker(commands.Cog, name="Initiative Tracker"):
    """Class definition for Initiative Tracker Cog."""
    def __init__(self, bot):
        self.bot = bot

    @commands.group(case_insensitive=True, help="Rolls initiative and builds an order table.")
    async def init(self, ctx):
        """Base init command group."""
        if ctx.invoked_subcommand is None:
            await ctx.send(f"Additional arguments required, "
                           f"see **{ctx.prefix}help init** for available options.")

    @init.command(help="Clears the Initiative tracker, and starts a new order.")
    async def reset(self, ctx):
        init_obj.reset()
        soulbot_db.init_db_reset()
        await ctx.send("Initiative Tracker is reset and active.")

    @init.command(name='roll', help="Rolls your initiative plus the supplied "
                                    "bonus and adds you to the order.")
    async def init_roll(self, ctx, init_bonus: int = 0):
        if init_obj.tracker_active is True:
            await ctx.send("Initiative Tracker is locked in an active combat session.")
        elif ctx.author.display_name in init_obj.combatant_dict:
            await ctx.send(f"{ctx.author.display_name} is already in the initiative order.")
        else:
            initiative = die_roll(1, 20)[1]
            init_obj.combatant_dict[ctx.author.display_name] = initiative + init_bonus
            init_obj.turn = ['    ' for _ in range(1, len(init_obj.combatant_dict) + 1)]
            init_obj.tracker = init_obj.build_init_table()
            await ctx.send(
                f"{ctx.author.display_name}'s Initiative is ({initiative}+{init_bonus})"
                f" {init_obj.combatant_dict[ctx.author.display_name]}.")

    @init.command(help="Starts the tracker and prevents any additions.")
    async def start(self, ctx):
        if len(init_obj.combatant_dict) == 0:
            await ctx.send(f"Please use **{ctx.prefix}init roll** to add to the order first.")
        elif init_obj.tracker_active is True:
            await ctx.send("Tracker is already started.")
        else:
            init_obj.tracker_active = True
            init_obj.turn[0] = '--->'
            init_obj.tracker = init_obj.build_init_table()
            db_insert = [(k, v) for k, v in init_obj.combatant_dict.items()]
            soulbot_db.init_db_reset()
            soulbot_db.init_db_add(db_insert)
            embed = init_obj.embed_template()
            await ctx.send(embed=embed)

    @init.command(help="Shows current turn order, rolls and tracker status.")
    async def show(self, ctx):
        embed = init_obj.embed_template()
        await ctx.send(embed=embed)

    @init.command(name='next', help="Advances the initiative order.")
    async def next_turn(self, ctx):
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
    async def delay(self, ctx, new_init: int):
        player_turn = ""
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
            await ctx.send("Delay should be done on your turn.")
        else:
            init_obj.combatant_dict[ctx.author.display_name] = new_init
            init_obj.tracker = init_obj.build_init_table()
            db_insert = [(k, v) for k, v in init_obj.combatant_dict.items()]
            soulbot_db.init_db_add(db_insert)
            embed = init_obj.embed_template()
            await ctx.send(
                f"Initiative for {ctx.author.display_name} has been delayed to "
                f"{init_obj.combatant_dict[ctx.author.display_name]}. "
                f"Initiative order has been recalculated.", embed=embed)

    @init.group(case_insensitive=True, help="Commands for the DM.", name="dm")
    @commands.has_role("DM" or "GM")
    async def dm_group(self, ctx):
        """DM Sub-group."""
        if ctx.invoked_subcommand is None:
            await ctx.send(f"Additional arguments required, see "
                           f"**{ctx.prefix}help init dm** for available options.")

    @dm_group.command(help="Add NPCs/Monsters to the initiative order, "
                           "before or during active combat.")
    async def npc(self, ctx, npc_name: str, init_bonus: int = 0):
        player_turn = ""
        if "!" and "@" in npc_name:
            mention_user = npc_name.replace("<", "").replace(">", "").replace("@", "").replace("!", "")
            npc_name = ctx.guild.get_member(int(mention_user)).display_name
        for sublist in init_obj.tracker:
            if '--->' in sublist:
                player_turn = init_obj.tracker[init_obj.tracker.index(sublist)][1]
        if init_obj.tracker_active:
            initiative = die_roll(1, 20)[1]
            init_obj.combatant_dict[npc_name] = initiative + init_bonus
            init_obj.turn = ['    ' for _ in range(1, len(init_obj.combatant_dict) + 1)]
            init_obj.tracker = init_obj.build_init_table()
            db_insert = [(k, v) for k, v in init_obj.combatant_dict.items()]
            soulbot_db.init_db_add(db_insert)
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
            init_obj.turn = ['    ' for _ in range(1, len(init_obj.combatant_dict) + 1)]
            init_obj.tracker = init_obj.build_init_table()
            await ctx.send(f"{npc_name}'s Initiative is ({initiative}+{init_bonus}) "
                           f"{init_obj.combatant_dict[npc_name]}.")

    @dm_group.command(help="Allows DM to manipulate the Escalation Die.  "
                           "Value can be plus or minus.")
    async def escalate(self, ctx, value_change: int):
        if init_obj.tracker_active is True:
            init_obj.escalation = init_obj.escalation + value_change
            if init_obj.escalation > 6:
                init_obj.escalation = 6
            await ctx.send(f"Escalation die is now {init_obj.escalation}")
        else:
            await ctx.send(f"Tracker not active, use **{ctx.prefix}init start** to begin.")

    @dm_group.command(help='Allows DM to remove someone(player or NPC) from the initiative order.  '
                           'Specified name for NPCs is case sensitive, use "" around name if '
                           'it includes spaces.  Players can be @ mentioned.')
    async def remove(self, ctx, name: str):
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
                init_obj.turn = ['    ' for _ in range(1, len(init_obj.combatant_dict) + 1)]
                init_obj.tracker = init_obj.build_init_table()
                db_insert = [(k, v) for k, v in init_obj.combatant_dict.items()]
                soulbot_db.init_db_reset()
                soulbot_db.init_db_add(db_insert)
                for sublist in init_obj.tracker:
                    if active_user in sublist:
                        init_obj.tracker[init_obj.tracker.index(sublist)][0] = '--->'
                        init_obj.turn[init_obj.tracker.index(sublist)] = '--->'
                await ctx.send(
                    f"{name} has been removed from the initiative table.")
        else:
            del init_obj.combatant_dict[name]
            init_obj.turn = ['    ' for _ in range(1, len(init_obj.combatant_dict) + 1)]
            init_obj.tracker = init_obj.build_init_table()
            await ctx.send(
                f"{name} has been removed from the initiative table.")

    @dm_group.command(help='Allows DM to manually update an NPC or player\'s init score.  '
                           'Specified name for NPCs is case sensitive, use "" around the name '
                           'if it includes spaces.  Players must be @ mentioned.')
    async def update(self, ctx, name: str, new_init: int):
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
            soulbot_db.init_db_add(db_insert)
            await ctx.send(f"{name}'s initiative has been manually set to {new_init}.")

    @dm_group.command(help='Allows DM to manually change who is the active combatant.')
    async def active(self, ctx, name: str):
        if "!" and "@" in name:
            mention_user = name.replace("<", "").replace(">", "").replace("@", "").replace("!", "")
            name = ctx.guild.get_member(int(mention_user)).display_name
        if not init_obj.tracker_active:
            await ctx.send("Initiative tracker is not active.")
        else:
            init_obj.turn = ['    ' for _ in range(1, len(init_obj.combatant_dict) + 1)]
            for sublist in init_obj.tracker:
                if name in sublist:
                    init_obj.turn[init_obj.tracker.index(sublist)] = '--->'
                    init_obj.tracker = init_obj.build_init_table()
            embed = init_obj.embed_template()
            await ctx.send(f"{name} is now the active combatant.", embed=embed)

    @dm_group.command(
        help="DON'T DO THIS UNLESS YOU MEAN IT. "
             "Rebuild the init tracker from the backup database.  "
             "Deactivates and resets the tracker, and resets the escalation die.")
    async def rebuild(self, ctx):
        init_obj.reset()
        all_rows = soulbot_db.init_db_rebuild()
        init_obj.combatant_dict = {_[0]: _[1] for _ in all_rows}
        init_obj.turn = ['    ' for _ in range(1, len(init_obj.combatant_dict) + 1)]
        init_obj.tracker = init_obj.build_init_table()
        embed = init_obj.embed_template()
        await ctx.send("Initiative tracker has been reset and rebuilt from the backup database.",
                       embed=embed)

    @dm_group.error
    @npc.error
    @update.error
    @rebuild.error
    async def on_dm_error(self, ctx, error):
        if isinstance(error, commands.MissingRole):
            await ctx.send(f"{error}")
        elif isinstance(error, commands.errors.CommandInvokeError):
            print(error)
            await ctx.send("Something went wrong, check the bot output.")
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            print(error)
            await ctx.send(f"Missing required arguments, please check **{ctx.prefix}help "
                           f"{ctx.invoked_with}** for command syntax.")
        else:
            print(error)
            await ctx.send('A unknown error has occurred, do you know where your towel is?')

    @commands.command(help="Rolls 1d20 + supplied player bonus(Stat + Level) "
                           "to attack, command automatically includes "
                           "escalation die(if any). Default bonus = 0")
    async def attack(self, ctx, bonus: int = 0):
        crit = ":x:"
        crit_range_plus2 = ":x:"
        crit_range_plus4 = ":x:"
        attack_roll = die_roll(1, 20)
        attack_natural = attack_roll[1]
        attack_modified = attack_natural + bonus + init_obj.escalation
        if attack_natural == 20:
            crit = ":white_check_mark:"
        if attack_natural >= 18:
            crit_range_plus2 = ":white_check_mark:"
        if attack_natural >= 16:
            crit_range_plus4 = ":white_check_mark:"
        math = f"|| ({attack_natural} + {bonus} + {init_obj.escalation} = {attack_modified}) ||"
        attack_embed = discord.Embed(title="__**Attack Result**__",
                                     description=f"{attack_modified}\n{math}",
                                     color=0x0000ff)
        attack_embed.add_field(name="Natural Roll",
                               value=f"{attack_natural}",
                               inline=False)
        attack_embed.add_field(name="Natural Crit",
                               value=f"{crit}",
                               inline=True)
        attack_embed.add_field(name="+2 Crit Range",
                               value=f"{crit_range_plus2}",
                               inline=True)
        attack_embed.add_field(name="+4 Crit Range",
                               value=f"{crit_range_plus4}",
                               inline=True)
        attack_embed.add_field(name="Escalation",
                               value=f"{init_obj.escalation}")
        await ctx.send(f"{ctx.author.mention} rolled to attack.",
                       embed=attack_embed)

    @commands.command(help="Rolls 1d20 + supplied NPC bonus to attack, "
                           "excludes escalation die. Default bonus = 0",
                      name="attacknpc")
    async def attack_npc(self, ctx, bonus: int = 0):
        crit = ":x:"
        crit_range_plus2 = ":x:"
        crit_range_plus4 = ":x:"
        attack_roll = die_roll(1, 20)
        attack_natural = attack_roll[1]
        attack_modified = attack_natural + bonus
        if attack_natural == 20:
            crit = ":white_check_mark:"
        if attack_natural >= 18:
            crit_range_plus2 = ":white_check_mark:"
        if attack_natural >= 16:
            crit_range_plus4 = ":white_check_mark:"
        math = f"|| ({attack_natural} + {bonus} = {attack_modified}) ||"
        attack_embed = discord.Embed(title="__**Attack Result**__",
                                     description=f"{attack_modified}\n{math}",
                                     color=0x0000ff)
        attack_embed.add_field(name="Natural Roll",
                               value=f"{attack_natural}",
                               inline=False)
        attack_embed.add_field(name="Natural Crit",
                               value=f"{crit}", inline=True)
        attack_embed.add_field(name="+2 Crit Range",
                               value=f"{crit_range_plus2}",
                               inline=True)
        attack_embed.add_field(name="+4 Crit Range",
                               value=f"{crit_range_plus4}",
                               inline=True)
        attack_embed.add_field(name="Escalation",
                               value="N/A")
        await ctx.send(f"{ctx.author.mention} rolled an **NPC attack**.",
                       embed=attack_embed)

    @attack.error
    @attack_npc.error
    @init_roll.error
    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            print(error)
            await ctx.send("Tracker is not started.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f'Invalid attack bonus, please check **{ctx.prefix}help '
                           f'{ctx.invoked_with}** for command syntax.')
        else:
            await ctx.send(f'Error Encountered:\n{error}')


def setup(bot):
    """Discord module required setup for Cog loading."""
    bot.add_cog(InitiativeTracker(bot))
