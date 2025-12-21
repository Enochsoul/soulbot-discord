"""Cog for tracking Initiative and attack rolls."""

import discord
from discord.ext import commands
from tabulate import tabulate

from DiceRoller import die_roll
from soulbot import bot as init_bot
from soulbot_support import soulbot_db


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
        self.__init__()

    def build_init_table(self):
        """Takes combatant dictionary, sorts it by key value,
        then builds the initiative activity table.
        """
        # Sort combatants by initiative value in descending order
        sorted_combatants = sorted(self.combatant_dict.items(), key=lambda x: x[1], reverse=True)

        # Build table with turn markers
        table = []
        for i, (name, initiative) in enumerate(sorted_combatants):
            turn_marker = self.turn[i] if i < len(self.turn) else "    "
            table.append([turn_marker, name, initiative])

        return table

    def embed_template(self):
        """Initiative tracker embed generator."""
        init_table = tabulate(
            self.tracker,
            headers=["Active", "Player", "Initiative"],
            tablefmt="fancy_grid",
        )
        embed = discord.Embed(colour=discord.Colour.red())
        embed.add_field(name="Tracker Active", value=str(self.tracker_active))
        embed.add_field(name="Escalation Die", value=str(self.escalation))
        return embed, f"```{init_table}```"


init_obj = {}
guild_list = soulbot_db.config_all_prefix_load()
for k in guild_list:
    init_obj[k] = InitiativeTrack()


@init_bot.event
async def on_guild_join(guild):
    global init_obj
    init_obj[guild.id] = InitiativeTrack()


class InitiativeTracker(discord.Cog, name='Initiative Tracker'):
    """Class definition for Initiative Tracker Cog."""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(case_insensitive=True, help='Rolls initiative and builds an order table.')
    async def init(self, ctx):
        """Base init command group."""
        if ctx.invoked_subcommand is None:
            await ctx.send(f"Additional arguments required, see **{ctx.prefix}help init** for available options.")

    @init.command(help='Clears the Initiative tracker, and starts a new order.')
    async def reset(self, ctx):
        init_obj[ctx.guild.id].reset()
        soulbot_db.init_db_reset(ctx.guild.id)
        soulbot_db.init_db_commit()
        await ctx.send('Initiative Tracker is reset and active.')

    @init.command(
        name="roll",
        help="Rolls your initiative plus the supplied bonus and adds you to the order.",
    )
    async def init_roll(self, ctx, init_bonus: int = 0):
        if init_obj[ctx.guild.id].tracker_active is True:
            await ctx.send('Initiative Tracker is locked in an active combat session.')
        elif ctx.author.display_name in init_obj[ctx.guild.id].combatant_dict:
            await ctx.send(f'{ctx.author.display_name} is already in the initiative order.')
        else:
            initiative = die_roll.roll("1d20").total
            init_obj[ctx.guild.id].combatant_dict[ctx.author.display_name] = initiative + init_bonus
            init_obj[ctx.guild.id].turn = ["    " for _ in range(1, len(init_obj[ctx.guild.id].combatant_dict) + 1)]
            init_obj[ctx.guild.id].tracker = init_obj[ctx.guild.id].build_init_table()
            await ctx.send(
                f"{ctx.author.display_name}'s Initiative is ({initiative}+{init_bonus})"
                f" {init_obj[ctx.guild.id].combatant_dict[ctx.author.display_name]}."
            )

    @init.command(help='Starts the tracker and prevents any additions.')
    async def start(self, ctx):
        if len(init_obj[ctx.guild.id].combatant_dict) == 0:
            await ctx.send(f'Please use **{ctx.prefix}init roll** to add to the order first.')
        elif init_obj[ctx.guild.id].tracker_active is True:
            await ctx.send('Tracker is already started.')
        else:
            init_obj[ctx.guild.id].tracker_active = True
            init_obj[ctx.guild.id].turn[0] = "--->"
            init_obj[ctx.guild.id].tracker = init_obj[ctx.guild.id].build_init_table()
            db_insert = [
                (ctx.guild.id, k, v) for k, v in init_obj[ctx.guild.id].combatant_dict.items()
            ]
            soulbot_db.init_db_reset(ctx.guild.id)
            soulbot_db.init_db_add(db_insert)
            soulbot_db.init_db_commit()
            embed, table = init_obj[ctx.guild.id].embed_template()
            await ctx.send(table, embed=embed)

    @init.command(help='Shows current turn order, rolls and tracker status.')
    async def show(self, ctx):
        embed, table = init_obj[ctx.guild.id].embed_template()
        await ctx.send(table, embed=embed)

    @init.command(name="next", help="Advances the initiative order.")
    async def next_turn(self, ctx):
        if init_obj[ctx.guild.id].tracker_active:
            if init_obj[ctx.guild.id].turn.index("--->") < len(init_obj[ctx.guild.id].combatant_dict) - 1:
                init_obj[ctx.guild.id].turn.insert(0, init_obj[ctx.guild.id].turn.pop(-1))
                init_obj[ctx.guild.id].tracker = init_obj[ctx.guild.id].build_init_table()
                embed, table = init_obj[ctx.guild.id].embed_template()
                await ctx.send(f"Beginning next turn.\n{table}", embed=embed)
            elif init_obj[ctx.guild.id].turn.index("--->") == len(init_obj[ctx.guild.id].combatant_dict) - 1:
                init_obj[ctx.guild.id].turn.insert(0, init_obj[ctx.guild.id].turn.pop(-1))
                init_obj[ctx.guild.id].tracker = init_obj[ctx.guild.id].build_init_table()
                init_obj[ctx.guild.id].escalation += 1
                if init_obj[ctx.guild.id].escalation > 6:
                    init_obj[ctx.guild.id].escalation = 6
                embed, table = init_obj[ctx.guild.id].embed_template()
                await ctx.send(f'Beginning next combat round.\n{table}', embed=embed)
        else:
            await ctx.send(f'Tracker not active, use **{ctx.prefix}init start** to begin.')

    @init.command(help='Allows a user to delay their turn in the order.')
    async def delay(self, ctx, new_init: int):
        player_turn = ''
        for sublist in init_obj[ctx.guild.id].tracker:
            if "--->" in sublist:
                player_turn = init_obj[ctx.guild.id].tracker[init_obj[ctx.guild.id].tracker.index(sublist)][1]
        if init_obj[ctx.guild.id].tracker_active is False:
            await ctx.send(f'Tracker not active, use **{ctx.prefix}init start** to begin.')
        elif ctx.author.display_name not in init_obj[ctx.guild.id].combatant_dict:
            await ctx.send(f'{ctx.author.display_name} is not in the initiative order.')
        elif new_init > init_obj[ctx.guild.id].combatant_dict[ctx.author.display_name]:
            await ctx.send(
                f"New initiative({new_init}) must be lower than original"
                f"({init_obj[ctx.guild.id].combatant_dict[ctx.author.display_name]})."
            )
        elif ctx.author.display_name != player_turn:
            await ctx.send('Delay should be done on your turn.')
        else:
            init_obj[ctx.guild.id].combatant_dict[ctx.author.display_name] = new_init
            init_obj[ctx.guild.id].tracker = init_obj[ctx.guild.id].build_init_table()
            db_insert = [
                (ctx.guild.id, k, v) for k, v in init_obj[ctx.guild.id].combatant_dict.items()
            ]
            soulbot_db.init_db_reset(ctx.guild.id)
            soulbot_db.init_db_add(db_insert)
            soulbot_db.init_db_commit()
            embed, table = init_obj[ctx.guild.id].embed_template()
            await ctx.send(
                f"Initiative for {ctx.author.display_name} has been delayed to "
                f"{init_obj[ctx.guild.id].combatant_dict[ctx.author.display_name]}. "
                f"Initiative order has been recalculated.\n{table}",
                embed=embed,
            )

    @init.group(case_insensitive=True, help="Commands for the DM.", name="dm")
    @commands.has_role("DM" or "GM")
    async def dm_group(self, ctx):
        """DM Sub-group."""
        if ctx.invoked_subcommand is None:
            await ctx.send(f"Additional arguments required, see **{ctx.prefix}help init dm** for available options.")

    @dm_group.command(help="Add NPCs/Monsters to the initiative order, before or during active combat.")
    async def npc(self, ctx, npc_name: str, init_bonus: int = 0):
        player_turn = ''
        if '!' and '@' in npc_name:
            mention_user = (
                npc_name.replace('<', '').replace('>', '').replace('@', '').replace('!', '')
            )
            npc_name = ctx.guild.get_member(int(mention_user)).display_name
        for sublist in init_obj[ctx.guild.id].tracker:
            if "--->" in sublist:
                player_turn = init_obj[ctx.guild.id].tracker[init_obj[ctx.guild.id].tracker.index(sublist)][1]
        if init_obj[ctx.guild.id].tracker_active:
            initiative = die_roll.roll("1d20").total
            init_obj[ctx.guild.id].combatant_dict[npc_name] = initiative + init_bonus
            init_obj[ctx.guild.id].turn = ["    " for _ in range(1, len(init_obj[ctx.guild.id].combatant_dict) + 1)]
            init_obj[ctx.guild.id].tracker = init_obj[ctx.guild.id].build_init_table()
            db_insert = [
                (ctx.guild.id, k, v) for k, v in init_obj[ctx.guild.id].combatant_dict.items()
            ]
            soulbot_db.init_db_reset(ctx.guild.id)
            soulbot_db.init_db_add(db_insert)
            soulbot_db.init_db_commit()
            for sublist in init_obj[ctx.guild.id].tracker:
                if player_turn in sublist:
                    init_obj[ctx.guild.id].tracker[init_obj[ctx.guild.id].tracker.index(sublist)][0] = "--->"
                    init_obj[ctx.guild.id].turn[init_obj[ctx.guild.id].tracker.index(sublist)] = "--->"
            await ctx.send(
                f"Adding {npc_name} to active combat round.\n"
                f"Initiative is ({initiative}+{init_bonus}) "
                f"{init_obj[ctx.guild.id].combatant_dict[npc_name]}."
            )
        elif npc_name in init_obj[ctx.guild.id].combatant_dict:
            await ctx.send(f'{npc_name} is already used in the initiative order.')
        else:
            initiative = die_roll.roll("1d20").total
            init_obj[ctx.guild.id].combatant_dict[npc_name] = initiative + init_bonus
            init_obj[ctx.guild.id].turn = ["    " for _ in range(1, len(init_obj[ctx.guild.id].combatant_dict) + 1)]
            init_obj[ctx.guild.id].tracker = init_obj[ctx.guild.id].build_init_table()
            await ctx.send(
                f"{npc_name}'s Initiative is ({initiative}+{init_bonus}) "
                f"{init_obj[ctx.guild.id].combatant_dict[npc_name]}."
            )

    @dm_group.command(help="Allows DM to manipulate the Escalation Die.  Value can be plus or minus.  Default = 1")
    async def escalate(self, ctx, value_change: int = 1):
        if init_obj[ctx.guild.id].tracker_active is True:
            init_obj[ctx.guild.id].escalation = init_obj[ctx.guild.id].escalation + value_change
            if init_obj[ctx.guild.id].escalation > 6:
                init_obj[ctx.guild.id].escalation = 6
            elif init_obj[ctx.guild.id].escalation < 0:
                init_obj[ctx.guild.id].escalation = 0
            await ctx.send(f'Escalation die is now {init_obj[ctx.guild.id].escalation}')
        else:
            await ctx.send(f'Tracker not active, use **{ctx.prefix}init start** to begin.')

    @dm_group.command(
        help="Allows DM to remove someone(player or NPC) from the initiative order.  "
        'Specified name for NPCs is case sensitive, use "" around name if '
        "it includes spaces.  Players can be @ mentioned."
    )
    async def remove(self, ctx, name: str):
        if '!' and '@' in name:
            mention_user = name.replace('<', '').replace('>', '').replace('@', '').replace('!', '')
            name = ctx.guild.get_member(int(mention_user)).display_name
        if name not in init_obj[ctx.guild.id].combatant_dict:
            await ctx.send(f'{name} is not in the initiative order.')
        elif init_obj[ctx.guild.id].tracker_active:
            for sublist in init_obj[ctx.guild.id].tracker:
                if "--->" in sublist:
                    active_user = init_obj[ctx.guild.id].tracker[init_obj[ctx.guild.id].tracker.index(sublist)][1]
            if active_user == name:
                await ctx.send(f"{name} is the active combatant, please advance the turn before removing them.")
            else:
                del init_obj[ctx.guild.id].combatant_dict[name]
                init_obj[ctx.guild.id].turn = ["    " for _ in range(1, len(init_obj[ctx.guild.id].combatant_dict) + 1)]
                init_obj[ctx.guild.id].tracker = init_obj[ctx.guild.id].build_init_table()
                db_insert = [
                    (ctx.guild.id, k, v) for k, v in init_obj[ctx.guild.id].combatant_dict.items()
                ]
                soulbot_db.init_db_reset(ctx.guild.id)
                soulbot_db.init_db_add(db_insert)
                soulbot_db.init_db_commit()
                for sublist in init_obj[ctx.guild.id].tracker:
                    if active_user in sublist:
                        init_obj[ctx.guild.id].tracker[init_obj[ctx.guild.id].tracker.index(sublist)][0] = "--->"
                        init_obj[ctx.guild.id].turn[init_obj[ctx.guild.id].tracker.index(sublist)] = "--->"
                await ctx.send(f"{name} has been removed from the initiative table.")
        else:
            del init_obj[ctx.guild.id].combatant_dict[name]
            init_obj[ctx.guild.id].turn = ["    " for _ in range(1, len(init_obj[ctx.guild.id].combatant_dict) + 1)]
            init_obj[ctx.guild.id].tracker = init_obj[ctx.guild.id].build_init_table()
            await ctx.send(f"{name} has been removed from the initiative table.")

    @dm_group.command(
        help="Allows DM to manually update an NPC or player's init score.  "
        'Specified name for NPCs is case sensitive, use "" around the name '
        "if it includes spaces.  Players must be @ mentioned."
    )
    async def update(self, ctx, name: str, new_init: int):
        if '!' and '@' in name:
            mention_user = name.replace('<', '').replace('>', '').replace('@', '').replace('!', '')
            name = ctx.guild.get_member(int(mention_user)).display_name
        if name not in init_obj[ctx.guild.id].combatant_dict:
            await ctx.send(f'{name} is not in the initiative order.')
        elif init_obj[ctx.guild.id].tracker_active is False:
            init_obj[ctx.guild.id].combatant_dict[name] = new_init
            init_obj[ctx.guild.id].tracker = init_obj[ctx.guild.id].build_init_table()
            await ctx.send(f"{name}'s initiative has been manually set to {new_init}.")
        else:
            init_obj[ctx.guild.id].combatant_dict[name] = new_init
            init_obj[ctx.guild.id].tracker = init_obj[ctx.guild.id].build_init_table()
            db_insert = [
                (ctx.guild.id, k, v) for k, v in init_obj[ctx.guild.id].combatant_dict.items()
            ]
            soulbot_db.init_db_reset(ctx.guild.id)
            soulbot_db.init_db_add(db_insert)
            soulbot_db.init_db_commit()
            await ctx.send(f"{name}'s initiative has been manually set to {new_init}.")

    @dm_group.command(help="Allows DM to manually change who is the active combatant.")
    async def active(self, ctx, name: str):
        if '!' and '@' in name:
            mention_user = name.replace('<', '').replace('>', '').replace('@', '').replace('!', '')
            name = ctx.guild.get_member(int(mention_user)).display_name
        if not init_obj[ctx.guild.id].tracker_active:
            await ctx.send('Initiative tracker is not active.')
        else:
            init_obj[ctx.guild.id].turn = ["    " for _ in range(1, len(init_obj[ctx.guild.id].combatant_dict) + 1)]
            for sublist in init_obj[ctx.guild.id].tracker:
                if name in sublist:
                    init_obj[ctx.guild.id].turn[init_obj[ctx.guild.id].tracker.index(sublist)] = "--->"
                    init_obj[ctx.guild.id].tracker = init_obj[ctx.guild.id].build_init_table()
            embed, table = init_obj[ctx.guild.id].embed_template()
            await ctx.send(f'{name} is now the active combatant.\n{table}', embed=embed)

    @dm_group.command(
        help="DON'T DO THIS UNLESS YOU MEAN IT. "
        "Rebuild the init tracker from the backup database.  "
        "Deactivates and resets the tracker, and resets the escalation die."
    )
    async def rebuild(self, ctx):
        init_obj[ctx.guild.id].reset()
        all_rows = soulbot_db.init_db_rebuild(ctx.guild.id)
        init_obj[ctx.guild.id].combatant_dict = {_[0]: _[1] for _ in all_rows}
        init_obj[ctx.guild.id].turn = ["    " for _ in range(1, len(init_obj[ctx.guild.id].combatant_dict) + 1)]
        init_obj[ctx.guild.id].tracker = init_obj[ctx.guild.id].build_init_table()
        embed, table = init_obj[ctx.guild.id].embed_template()
        await ctx.send(
            f"Initiative tracker has been reset and rebuilt from the backup database.\n{table}",
            embed=embed,
        )

    @dm_group.error
    @npc.error
    @update.error
    @rebuild.error
    async def on_dm_error(self, ctx, error):
        if isinstance(error, commands.MissingRole):
            await ctx.send(f'{error}')
        elif isinstance(error, commands.errors.CommandInvokeError):
            print(error)
            await ctx.send('Something went wrong, check the bot output.')
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            print(error)
            await ctx.send(
                f"Missing required arguments, please check **{ctx.prefix}help {ctx.invoked_with}** for command syntax."
            )
        else:
            print(error)
            await ctx.send("A unknown error has occurred, do you know where your towel is?")

    @commands.command(
        help="Rolls 1d20 + supplied player bonus(Stat + Level) "
        "to attack, command automatically includes "
        "escalation die(if any). Default bonus = 0"
    )
    async def attack(self, ctx, bonus: int = 0, roll_type: str = "d"):
        """Roll an attack with the specified bonus and roll type."""
        # Valid roll types mapping
        valid_roll_types = {"d": "1d20", "ad": "1ad20", "dd": "1dd20"}

        # Validate roll type
        if roll_type not in valid_roll_types:
            await ctx.send(f"Invalid roll type: {roll_type}. Valid types are: {', '.join(valid_roll_types.keys())}")
            return

        # Roll the dice
        attack_natural = die_roll.roll(valid_roll_types[roll_type]).total
        escalation = init_obj[ctx.guild.id].escalation
        attack_modified = attack_natural + bonus + escalation

        # Determine crit status
        crit_indicators = {
            "natural": ":white_check_mark:" if attack_natural == 20 else ":x:",
            "plus2": ":white_check_mark:" if attack_natural >= 18 else ":x:",
            "plus4": ":white_check_mark:" if attack_natural >= 16 else ":x:",
        }

        # Create calculation breakdown
        math_breakdown = f"|| ({attack_natural} + {bonus} + {escalation} = {attack_modified}) ||"

        # Create embed
        attack_embed = discord.Embed(
            title="__**Attack Result**__",
            description=f"{attack_modified}\n{math_breakdown}",
            color=0x0000FF,
        )
        attack_embed.add_field(name="Natural Roll", value=f"{attack_natural}", inline=False)
        attack_embed.add_field(name="Natural Crit", value=crit_indicators["natural"], inline=True)
        attack_embed.add_field(name="+2 Crit Range", value=crit_indicators["plus2"], inline=True)
        attack_embed.add_field(name="+4 Crit Range", value=crit_indicators["plus4"], inline=True)
        attack_embed.add_field(name="Escalation", value=f"{escalation}")

        await ctx.send(f"{ctx.author.mention} rolled to attack.", embed=attack_embed)

    @commands.command(
        help="Rolls 1d20 + supplied NPC bonus to attack, excludes escalation die. Default bonus = 0",
        name="attacknpc",
    )
    async def attack_npc(self, ctx, bonus: int = 0, roll_type: str = "d"):
        # Valid roll types mapping
        valid_roll_types = {"d": "1d20", "ad": "1ad20", "dd": "1dd20"}

        # Validate roll type
        if roll_type not in valid_roll_types:
            await ctx.send(f"Invalid roll type: {roll_type}. Valid types are: {', '.join(valid_roll_types.keys())}")
            return

        # Roll the dice
        attack_natural = die_roll.roll(valid_roll_types[roll_type]).total
        attack_modified = attack_natural + bonus

        # Determine crit status
        crit_indicators = {
            "natural": ":white_check_mark:" if attack_natural == 20 else ":x:",
            "plus2": ":white_check_mark:" if attack_natural >= 18 else ":x:",
            "plus4": ":white_check_mark:" if attack_natural >= 16 else ":x:",
        }

        # Create calculation breakdown
        math_breakdown = f"|| ({attack_natural} + {bonus} = {attack_modified}) ||"

        # Create embed
        attack_embed = discord.Embed(
            title="__**Attack Result**__",
            description=f"{attack_modified}\n{math_breakdown}",
            color=0x0000FF,
        )
        attack_embed.add_field(name="Natural Roll", value=f"{attack_natural}", inline=False)
        attack_embed.add_field(name="Natural Crit", value=crit_indicators["natural"], inline=True)
        attack_embed.add_field(name="+2 Crit Range", value=crit_indicators["plus2"], inline=True)
        attack_embed.add_field(name="+4 Crit Range", value=crit_indicators["plus4"], inline=True)
        attack_embed.add_field(name="Escalation", value="N/A")

        await ctx.send(f"{ctx.author.mention} rolled an **NPC attack**.", embed=attack_embed)

    @attack.error
    @attack_npc.error
    @init_roll.error
    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            print(error)
            await ctx.send('An error occurred with the last command.')
        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                f"Invalid attack bonus, please check **{ctx.prefix}help {ctx.invoked_with}** for command syntax."
            )
        else:
            await ctx.send(f"Error Encountered:\n{error}")


def setup(bot):
    """Discord module required setup for Cog loading."""
    bot.add_cog(InitiativeTracker(bot))
