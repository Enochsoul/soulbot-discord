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
        self.combatant_dict: dict[str, int] = {}
        self.tracker: list[tuple[str, int]] = []
        self.tracker_active: bool = False
        self.turn: list[str] = []
        self.escalation: int = 0

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

    def _parse_mention(self, ctx, name: str) -> str:
        """Parse Discord user mentions and return display name."""
        if "!" in name and "@" in name:
            mention_user = name.replace("<", "").replace(">", "").replace("@", "").replace("!", "")
            return ctx.guild.get_member(int(mention_user)).display_name
        return name

    def _find_active_player(self, guild_tracker) -> str:
        """Find the currently active player in the tracker."""
        for sublist in guild_tracker.tracker:
            if "--->" in sublist:
                return sublist[1]
        return ""

    def _update_database(self, ctx, guild_tracker):
        """Update the database with current combatant data."""
        db_insert = [(ctx.guild.id, k, v) for k, v in guild_tracker.combatant_dict.items()]
        soulbot_db.init_db_reset(ctx.guild.id)
        soulbot_db.init_db_add(db_insert)
        soulbot_db.init_db_commit()

    def _set_active_player(self, guild_tracker, player_name: str):
        """Set the active player marker for the specified player."""
        for i, sublist in enumerate(guild_tracker.tracker):
            if player_name in sublist:
                guild_tracker.tracker[i][0] = "--->"
                guild_tracker.turn[i] = "--->"
                break

    @commands.group(case_insensitive=True, help="Rolls initiative and builds an order table.")
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
        guild_tracker = init_obj[ctx.guild.id]
        player_name = ctx.author.display_name

        if guild_tracker.tracker_active:
            await ctx.send("Initiative Tracker is locked in an active combat session.")
            return

        if player_name in guild_tracker.combatant_dict:
            await ctx.send(f"{player_name} is already in the initiative order.")
            return

        # Roll initiative and add to tracker
        initiative_roll = die_roll.roll("1d20").total
        total_initiative = initiative_roll + init_bonus

        guild_tracker.combatant_dict[player_name] = total_initiative
        guild_tracker.turn = ["    " for _ in range(len(guild_tracker.combatant_dict))]
        guild_tracker.tracker = guild_tracker.build_init_table()

        await ctx.send(f"{player_name}'s Initiative is ({initiative_roll}+{init_bonus}) {total_initiative}.")

    @init.command(help='Starts the tracker and prevents any additions.')
    async def start(self, ctx):
        guild_tracker = init_obj[ctx.guild.id]

        if len(guild_tracker.combatant_dict) == 0:
            await ctx.send(f"Please use **{ctx.prefix}init roll** to add to the order first.")
            return

        if guild_tracker.tracker_active:
            await ctx.send("Tracker is already started.")
            return

        # Start the tracker
        guild_tracker.tracker_active = True
        guild_tracker.turn[0] = "--->"
        guild_tracker.tracker = guild_tracker.build_init_table()

        # Update database
        self._update_database(ctx, guild_tracker)

        # Send response
        embed, table = guild_tracker.embed_template()
        await ctx.send(table, embed=embed)

    @init.command(help='Shows current turn order, rolls and tracker status.')
    async def show(self, ctx):
        guild_tracker = init_obj[ctx.guild.id]
        embed, table = guild_tracker.embed_template()
        await ctx.send(table, embed=embed)

    @init.command(name="next", help="Advances the initiative order.")
    async def next_turn(self, ctx):
        guild_tracker = init_obj[ctx.guild.id]

        if not guild_tracker.tracker_active:
            await ctx.send(f"Tracker not active, use **{ctx.prefix}init start** to begin.")
            return

        try:
            current_turn_index = guild_tracker.turn.index("--->")
        except ValueError:
            await ctx.send("Error: No active turn marker found.")
            return

        is_last_combatant = current_turn_index == len(guild_tracker.combatant_dict) - 1

        # Advance turn
        guild_tracker.turn.insert(0, guild_tracker.turn.pop(-1))
        guild_tracker.tracker = guild_tracker.build_init_table()

        # Handle escalation for new rounds
        if is_last_combatant:
            guild_tracker.escalation = min(guild_tracker.escalation + 1, 6)
            message = "Beginning next combat round."
        else:
            message = "Beginning next turn."

        embed, table = guild_tracker.embed_template()
        await ctx.send(f"{message}\n{table}", embed=embed)

    @init.command(help='Allows a user to delay their turn in the order.')
    async def delay(self, ctx, new_init: int):
        guild_tracker = init_obj[ctx.guild.id]
        player_name = ctx.author.display_name

        # Check if tracker is active
        if not guild_tracker.tracker_active:
            await ctx.send(f"Tracker not active, use **{ctx.prefix}init start** to begin.")
            return

        # Check if player is in the initiative order
        if player_name not in guild_tracker.combatant_dict:
            await ctx.send(f"{player_name} is not in the initiative order.")
            return

        # Get current player's initiative and validate new initiative
        current_init = guild_tracker.combatant_dict[player_name]
        if new_init > current_init:
            await ctx.send(f"New initiative ({new_init}) must be lower than original ({current_init}).")
            return

        # Find the current active player
        active_player = None
        for sublist in guild_tracker.tracker:
            if "--->" in sublist:
                active_player = sublist[1]
                break

        # Check if it's the player's turn
        if player_name != active_player:
            await ctx.send("Delay should be done on your turn.")
            return

        # Update initiative and rebuild tracker
        guild_tracker.combatant_dict[player_name] = new_init
        guild_tracker.tracker = guild_tracker.build_init_table()

        # Update database
        self._update_database(ctx, guild_tracker)

        # Send response
        embed, table = guild_tracker.embed_template()
        await ctx.send(
            f"Initiative for {player_name} has been delayed to {new_init}. "
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
        guild_tracker = init_obj[ctx.guild.id]

        # Handle Discord user mentions
        npc_name = self._parse_mention(ctx, npc_name)

        # Check if NPC is already in the order
        if npc_name in guild_tracker.combatant_dict:
            await ctx.send(f"{npc_name} is already used in the initiative order.")
            return

        # Roll initiative
        initiative_roll = die_roll.roll("1d20").total
        total_initiative = initiative_roll + init_bonus

        # Find and preserve the current active player
        active_player = self._find_active_player(guild_tracker)

        # Add NPC to combatant dictionary
        guild_tracker.combatant_dict[npc_name] = total_initiative
        guild_tracker.turn = ["    " for _ in range(len(guild_tracker.combatant_dict))]
        guild_tracker.tracker = guild_tracker.build_init_table()

        if guild_tracker.tracker_active:
            # Update database
            self._update_database(ctx, guild_tracker)

            # Restore active player marker
            self._set_active_player(guild_tracker, active_player)

            await ctx.send(
                f"Adding {npc_name} to active combat round.\n"
                f"Initiative is ({initiative_roll}+{init_bonus}) {total_initiative}."
            )
        else:
            await ctx.send(f"{npc_name}'s Initiative is ({initiative_roll}+{init_bonus}) {total_initiative}.")

    @dm_group.command(help="Allows DM to manipulate the Escalation Die.  Value can be plus or minus.  Default = 1")
    async def escalate(self, ctx, value_change: int = 1):
        guild_tracker = init_obj[ctx.guild.id]

        if not guild_tracker.tracker_active:
            await ctx.send(f"Tracker not active, use **{ctx.prefix}init start** to begin.")
            return

        # Update escalation die with bounds checking
        guild_tracker.escalation = max(0, min(6, guild_tracker.escalation + value_change))
        await ctx.send(f"Escalation die is now {guild_tracker.escalation}")

    @dm_group.command(
        help="Allows DM to remove someone(player or NPC) from the initiative order.  "
        'Specified name for NPCs is case sensitive, use "" around name if '
        "it includes spaces.  Players can be @ mentioned."
    )
    async def remove(self, ctx, name: str):
        guild_tracker = init_obj[ctx.guild.id]

        # Parse mention to get display name
        name = self._parse_mention(ctx, name)

        # Check if the name is in the initiative order
        if name not in guild_tracker.combatant_dict:
            await ctx.send(f"{name} is not in the initiative order.")
            return

        # Handle active tracker scenario
        if guild_tracker.tracker_active:
            # Find the currently active player
            active_user = self._find_active_player(guild_tracker)

            if active_user == name:
                await ctx.send(f"{name} is the active combatant, please advance the turn before removing them.")
                return

            # Remove the combatant
            del guild_tracker.combatant_dict[name]
            guild_tracker.turn = ["    " for _ in range(len(guild_tracker.combatant_dict))]
            guild_tracker.tracker = guild_tracker.build_init_table()

            # Update database
            self._update_database(ctx, guild_tracker)

            # Restore the active player marker
            self._set_active_player(guild_tracker, active_user)

            await ctx.send(f"{name} has been removed from the initiative table.")
        else:
            # Handle inactive tracker scenario
            del guild_tracker.combatant_dict[name]
            guild_tracker.turn = ["    " for _ in range(len(guild_tracker.combatant_dict))]
            guild_tracker.tracker = guild_tracker.build_init_table()
            await ctx.send(f"{name} has been removed from the initiative table.")

    @dm_group.command(
        help="Allows DM to manually update an NPC or player's init score.  "
        'Specified name for NPCs is case sensitive, use "" around the name '
        "if it includes spaces.  Players must be @ mentioned."
    )
    async def update(self, ctx, name: str, new_init: int):
        guild_tracker = init_obj[ctx.guild.id]

        # Parse mention to get display name
        name = self._parse_mention(ctx, name)

        # Check if the name is in the initiative order
        if name not in guild_tracker.combatant_dict:
            await ctx.send(f"{name} is not in the initiative order.")
            return

        # Find and preserve the current active player if tracker is active
        active_player = None
        if guild_tracker.tracker_active:
            active_player = self._find_active_player(guild_tracker)

        # Update the combatant's initiative
        guild_tracker.combatant_dict[name] = new_init
        guild_tracker.tracker = guild_tracker.build_init_table()

        # Update database if tracker is active
        if guild_tracker.tracker_active:
            self._update_database(ctx, guild_tracker)

            # Restore active player marker if there was one
            if active_player:
                self._set_active_player(guild_tracker, active_player)

        await ctx.send(f"{name}'s initiative has been manually set to {new_init}.")

    @dm_group.command(help="Allows DM to manually change who is the active combatant.")
    async def active(self, ctx, name: str):
        guild_tracker = init_obj[ctx.guild.id]

        # Parse mention to get display name
        name = self._parse_mention(ctx, name)

        # Check if tracker is active
        if not guild_tracker.tracker_active:
            await ctx.send("Initiative tracker is not active.")
            return

        # Check if the name is in the initiative order
        if name not in guild_tracker.combatant_dict:
            await ctx.send(f"{name} is not in the initiative order.")
            return

        # Reset all turn markers and set the active player
        guild_tracker.turn = ["    " for _ in range(len(guild_tracker.combatant_dict))]
        self._set_active_player(guild_tracker, name)
        guild_tracker.tracker = guild_tracker.build_init_table()

        # Send response
        embed, table = guild_tracker.embed_template()
        await ctx.send(f"{name} is now the active combatant.\n{table}", embed=embed)

    @dm_group.command(
        help="DON'T DO THIS UNLESS YOU MEAN IT. "
        "Rebuild the init tracker from the backup database.  "
        "Deactivates and resets the tracker, and resets the escalation die."
    )
    async def rebuild(self, ctx):
        guild_tracker = init_obj[ctx.guild.id]

        # Reset the tracker
        guild_tracker.reset()

        # Rebuild from database
        all_rows = soulbot_db.init_db_rebuild(ctx.guild.id)
        if all_rows:
            guild_tracker.combatant_dict = {row[0]: row[1] for row in all_rows}
            guild_tracker.turn = ["    " for _ in range(len(guild_tracker.combatant_dict))]
            guild_tracker.tracker = guild_tracker.build_init_table()

        # Generate response
        embed, table = guild_tracker.embed_template()
        await ctx.send(
            f"Initiative tracker has been reset and rebuilt from the backup database.\n{table}",
            embed=embed,
        )

    @dm_group.error
    @npc.error
    @update.error
    @rebuild.error
    async def on_dm_error(self, ctx, error):
        """Handle errors for DM-specific commands."""
        if isinstance(error, commands.MissingRole):
            await ctx.send(f"{error}")
        elif isinstance(error, commands.CommandInvokeError):
            print(f"CommandInvokeError in {ctx.command}: {error}")
            await ctx.send("Something went wrong, check the bot output.")
        elif isinstance(error, commands.MissingRequiredArgument):
            print(f"MissingRequiredArgument in {ctx.command}: {error}")
            await ctx.send(
                f"Missing required arguments, please check **{ctx.prefix}help {ctx.invoked_with}** for command syntax."
            )
        else:
            print(f"Unknown error in {ctx.command}: {error}")
            await ctx.send("An unknown error has occurred, do you know where your towel is?")

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
