"""Cog for tracking Initiative and attack rolls."""

import discord
from discord.ext import commands
from loguru import logger

import init_support
from soulbot import bot as init_bot
from soulbot_support import soulbot_db

init_obj: dict[int, init_support.InitiativeTrack] = {}
guild_list = soulbot_db.config_all_prefix_load()
for k in guild_list:
    init_obj[k] = init_support.InitiativeTrack()


@init_bot.event
async def on_guild_join(guild: discord.Guild) -> None:
    global init_obj
    init_obj[guild.id] = init_support.InitiativeTrack()
    logger.info(f"Created initiative tracker for new guild: {guild.name} ({guild.id})")


class InitiativeTracker(discord.Cog, name="Initiative Tracker"):
    """Class definition for Initiative Tracker Cog."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        logger.info("InitiativeTracker cog initialized")

    def _parse_mention(self, ctx: commands.Context, name: str) -> str:
        """Parse Discord user mentions and return display name."""
        if "!" in name and "@" in name:
            mention_user = name.replace("<", "").replace(">", "").replace("@", "").replace("!", "")
            return ctx.guild.get_member(int(mention_user)).display_name
        return name

    def _find_active_player(self, guild_tracker: init_support.InitiativeTrack) -> str:
        """Find the currently active player in the tracker."""
        for sublist in guild_tracker.tracker:
            if "--->" in sublist:
                return sublist[1]
        return ""

    def _update_database(self, ctx: commands.Context, guild_tracker: init_support.InitiativeTrack) -> None:
        """Update the database with current combatant data."""
        db_insert = [(ctx.guild.id, k, v) for k, v in guild_tracker.combatant_dict.items()]
        soulbot_db.init_db_reset(ctx.guild.id)
        soulbot_db.init_db_add(db_insert)
        soulbot_db.init_db_commit()
        logger.debug(f"Updated initiative database for guild {ctx.guild.name}")

    def _set_active_player(self, guild_tracker: init_support.InitiativeTrack, player_name: str) -> None:
        """Set the active player marker for the specified player."""
        for i, sublist in enumerate(guild_tracker.tracker):
            if player_name in sublist:
                guild_tracker.tracker[i][0] = "--->"
                guild_tracker.turn[i] = "--->"
                break

    @commands.group(case_insensitive=True, help="Rolls initiative and builds an order table.")
    async def init(self, ctx: commands.Context) -> None:
        """Base init command group."""
        if ctx.invoked_subcommand is None:
            await ctx.send(f"Additional arguments required, see **{ctx.prefix}help init** for available options.")

    @init.command(help="Clears the Initiative tracker, and starts a new order.")
    async def reset(self, ctx: commands.Context) -> None:
        init_obj[ctx.guild.id].reset()
        soulbot_db.init_db_reset(ctx.guild.id)
        soulbot_db.init_db_commit()
        logger.info(f"User {ctx.author} reset initiative tracker in guild {ctx.guild.name}")
        await ctx.send("Initiative Tracker is reset and active.")

    @init.command(
        name="roll",
        help="Rolls your initiative plus the supplied bonus and adds you to the order.",
    )
    async def init_roll(self, ctx: commands.Context, init_bonus: int = 0) -> None:
        guild_tracker = init_obj[ctx.guild.id]
        player_name = ctx.author.display_name

        message = init_support.handle_init_roll_logic(guild_tracker, player_name, init_bonus)
        logger.info(f"User {ctx.author} rolled initiative with bonus {init_bonus}")
        await ctx.send(message)

    @init.command(help="Starts the tracker and prevents any additions.")
    async def start(self, ctx: commands.Context) -> None:
        guild_tracker = init_obj[ctx.guild.id]

        message, embed = init_support.handle_start_logic(guild_tracker, ctx, self._update_database)
        logger.info(f"User {ctx.author} started initiative tracker in guild {ctx.guild.name}")
        if embed is None:
            await ctx.send(message)
        else:
            await ctx.send(message, embed=embed)

    @init.command(help="Shows current turn order, rolls and tracker status.")
    async def show(self, ctx: commands.Context) -> None:
        guild_tracker = init_obj[ctx.guild.id]
        embed, table = guild_tracker.embed_template()
        logger.debug(f"User {ctx.author} viewed initiative tracker")
        await ctx.send(table, embed=embed)

    @init.command(name="next", help="Advances the initiative order.")
    async def next_turn(self, ctx: commands.Context) -> None:
        guild_tracker = init_obj[ctx.guild.id]

        message, embed = init_support.handle_next_turn_logic(guild_tracker, ctx)
        logger.info(f"User {ctx.author} advanced initiative turn")
        if embed is None:
            await ctx.send(message)
        else:
            await ctx.send(message, embed=embed)

    @init.command(help="Allows a user to delay their turn in the order.")
    async def delay(self, ctx: commands.Context, new_init: int) -> None:
        guild_tracker = init_obj[ctx.guild.id]
        player_name = ctx.author.display_name

        message, embed = init_support.handle_delay_logic(
            guild_tracker, player_name, new_init, ctx, self._update_database
        )
        logger.info(f"User {ctx.author} delayed turn to initiative {new_init}")
        if embed is None:
            await ctx.send(message)
        else:
            await ctx.send(message, embed=embed)

    @init.group(case_insensitive=True, help="Commands for the DM.", name="dm")
    @commands.has_role("DM" or "GM")
    async def dm_group(self, ctx: commands.Context) -> None:
        """DM Sub-group."""
        if ctx.invoked_subcommand is None:
            await ctx.send(f"Additional arguments required, see **{ctx.prefix}help init dm** for available options.")

    @dm_group.command(help="Add NPCs/Monsters to the initiative order, before or during active combat.")
    async def npc(self, ctx: commands.Context, npc_name: str, init_bonus: int = 0) -> None:
        guild_tracker = init_obj[ctx.guild.id]

        message, error = init_support.handle_npc_logic(
            guild_tracker,
            npc_name,
            init_bonus,
            ctx,
            self._parse_mention,
            self._find_active_player,
            self._update_database,
            self._set_active_player,
        )
        logger.info(f"DM {ctx.author} added NPC {npc_name} with bonus {init_bonus}")
        await ctx.send(message)

    @dm_group.command(help="Allows DM to manipulate the Escalation Die.  Value can be plus or minus.  Default = 1")
    async def escalate(self, ctx: commands.Context, value_change: int = 1) -> None:
        guild_tracker = init_obj[ctx.guild.id]

        if not guild_tracker.tracker_active:
            await ctx.send(f"Tracker not active, use **{ctx.prefix}init start** to begin.")
            return

        # Update escalation die with bounds checking
        old_value = guild_tracker.escalation
        guild_tracker.escalation = max(0, min(6, guild_tracker.escalation + value_change))
        logger.info(f"DM {ctx.author} changed escalation die from {old_value} to {guild_tracker.escalation}")
        await ctx.send(f"Escalation die is now {guild_tracker.escalation}")

    @dm_group.command(
        help="Allows DM to remove someone(player or NPC) from the initiative order.  "
        'Specified name for NPCs is case sensitive, use "" around name if '
        "it includes spaces.  Players can be @ mentioned."
    )
    async def remove(self, ctx: commands.Context, name: str) -> None:
        guild_tracker = init_obj[ctx.guild.id]

        message, error = init_support.handle_remove_logic(
            guild_tracker,
            name,
            ctx,
            self._parse_mention,
            self._find_active_player,
            self._update_database,
            self._set_active_player,
        )
        logger.info(f"DM {ctx.author} removed {name} from initiative")
        await ctx.send(message)

    @dm_group.command(
        help="Allows DM to manually update an NPC or player's init score.  "
        'Specified name for NPCs is case sensitive, use "" around the name '
        "if it includes spaces.  Players must be @ mentioned."
    )
    async def update(self, ctx: commands.Context, name: str, new_init: int) -> None:
        guild_tracker = init_obj[ctx.guild.id]

        message, error = init_support.handle_update_logic(
            guild_tracker,
            name,
            new_init,
            ctx,
            self._parse_mention,
            self._find_active_player,
            self._update_database,
            self._set_active_player,
        )
        logger.info(f"DM {ctx.author} updated {name} to initiative {new_init}")
        await ctx.send(message)

    @dm_group.command(help="Allows DM to manually change who is the active combatant.")
    async def active(self, ctx: commands.Context, name: str) -> None:
        guild_tracker = init_obj[ctx.guild.id]

        message, embed = init_support.handle_active_logic(
            guild_tracker, name, ctx, self._parse_mention, self._set_active_player
        )
        logger.info(f"DM {ctx.author} set {name} as active combatant")
        if embed is None:
            await ctx.send(message)
        else:
            await ctx.send(message, embed=embed)

    @dm_group.command(
        help="DON'T DO THIS UNLESS YOU MEAN IT. "
        "Rebuild the init tracker from the backup database.  "
        "Deactivates and resets the tracker, and resets the escalation die."
    )
    async def rebuild(self, ctx: commands.Context) -> None:
        guild_tracker = init_obj[ctx.guild.id]

        message, embed = init_support.handle_rebuild_logic(guild_tracker, ctx)
        logger.warning(f"DM {ctx.author} rebuilt initiative tracker from database")
        await ctx.send(message, embed=embed)

    @dm_group.error
    @npc.error
    @update.error
    @rebuild.error
    async def on_dm_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """Handle errors for DM-specific commands."""
        if isinstance(error, commands.MissingRole):
            logger.warning(f"User {ctx.author} tried to use DM command without role: {ctx.command}")
            await ctx.send(f"{error}")
        elif isinstance(error, commands.CommandInvokeError):
            logger.error(f"CommandInvokeError in {ctx.command}: {error}")
            print(f"CommandInvokeError in {ctx.command}: {error}")
            await ctx.send("Something went wrong, check the bot output.")
        elif isinstance(error, commands.MissingRequiredArgument):
            logger.warning(f"MissingRequiredArgument in {ctx.command}: {error}")
            print(f"MissingRequiredArgument in {ctx.command}: {error}")
            await ctx.send(
                f"Missing required arguments, please check **{ctx.prefix}help {ctx.invoked_with}** for command syntax."
            )
        else:
            logger.error(f"Unknown error in {ctx.command}: {error}")
            print(f"Unknown error in {ctx.command}: {error}")
            await ctx.send("An unknown error has occurred, do you know where your towel is?")

    @commands.command(
        help="Rolls 1d20 + supplied player bonus(Stat + Level) "
        "to attack, command automatically includes "
        "escalation die(if any). Default bonus = 0"
    )
    async def attack(self, ctx: commands.Context, bonus: int = 0, roll_type: str = "d") -> None:
        """Roll an attack with the specified bonus and roll type."""
        message, embed = init_support.handle_attack_logic(ctx, bonus, roll_type, init_obj)
        logger.info(f"User {ctx.author} rolled attack with bonus {bonus}, roll type {roll_type}")
        if embed:
            await ctx.send(message, embed=embed)
        else:
            await ctx.send(message)

    @commands.command(
        help="Rolls 1d20 + supplied NPC bonus to attack, excludes escalation die. Default bonus = 0",
        name="attacknpc",
    )
    async def attack_npc(self, ctx: commands.Context, bonus: int = 0, roll_type: str = "d") -> None:
        message, embed = init_support.handle_attack_npc_logic(ctx, bonus, roll_type)
        logger.info(f"User {ctx.author} rolled NPC attack with bonus {bonus}, roll type {roll_type}")
        if embed:
            await ctx.send(message, embed=embed)
        else:
            await ctx.send(message)

    @attack.error
    @attack_npc.error
    @init_roll.error
    async def cog_command_error(self, ctx: discord.ApplicationContext, error: Exception) -> None:
        if isinstance(error, commands.MissingRequiredArgument):
            logger.warning(f"Missing required argument in {ctx.command}: {error}")
            await ctx.send(f"Missing required argument. Use `{ctx.prefix}help {ctx.command}` for usage.")
        elif isinstance(error, commands.CommandInvokeError):
            logger.error(f"Command invoke error in {ctx.command}: {error}")
            await ctx.send("An error occurred with the last command.")
        elif isinstance(error, commands.BadArgument):
            logger.warning(f"Bad argument in {ctx.command}: {error}")
            await ctx.send(
                f"Invalid attack bonus, please check **{ctx.prefix}help {ctx.invoked_with}** for command syntax."
            )
        else:
            logger.error(f"Unknown command error in {ctx.command}: {error}")
            await ctx.send(f"Error Encountered:\n{error}")


def setup(bot: commands.Bot) -> None:
    """Discord module required setup for Cog loading."""
    logger.info("Loading InitiativeTracker cog")
    bot.add_cog(InitiativeTracker(bot))
