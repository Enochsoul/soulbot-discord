"""Support functions for Initiative Tracker async function capabilities."""

import discord

from DiceRoller import die_roll
from soulbot_support import soulbot_db


def handle_init_roll_logic(guild_tracker, player_name, init_bonus):
    """Handle the core logic for initiative rolling."""
    if guild_tracker.tracker_active:
        return "Initiative Tracker is locked in an active combat session."

    if player_name in guild_tracker.combatant_dict:
        return f"{player_name} is already in the initiative order."

    # Roll initiative and add to tracker
    initiative_roll = die_roll.roll("1d20").total
    total_initiative = initiative_roll + init_bonus

    guild_tracker.combatant_dict[player_name] = total_initiative
    guild_tracker.turn = ["    " for _ in range(len(guild_tracker.combatant_dict))]
    guild_tracker.tracker = guild_tracker.build_init_table()

    return f"{player_name}'s Initiative is ({initiative_roll}+{init_bonus}) {total_initiative}."


def handle_start_logic(guild_tracker, ctx, update_database_func):
    """Handle the core logic for starting the tracker."""
    if len(guild_tracker.combatant_dict) == 0:
        return f"Please use **{ctx.prefix}init roll** to add to the order first.", None

    if guild_tracker.tracker_active:
        return "Tracker is already started.", None

    # Start the tracker
    guild_tracker.tracker_active = True
    guild_tracker.turn[0] = "--->"
    guild_tracker.tracker = guild_tracker.build_init_table()

    # Update database
    update_database_func(ctx, guild_tracker)

    # Generate response
    embed, table = guild_tracker.embed_template()
    return table, embed


def handle_next_turn_logic(guild_tracker, ctx):
    """Handle the core logic for advancing to the next turn."""
    if not guild_tracker.tracker_active:
        return f"Tracker not active, use **{ctx.prefix}init start** to begin.", None

    try:
        current_turn_index = guild_tracker.turn.index("--->")
    except ValueError:
        return "Error: No active turn marker found.", None

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
    return f"{message}\n{table}", embed


def handle_delay_logic(guild_tracker, player_name, new_init, ctx, update_database_func):
    """Handle the core logic for delaying a player's turn."""
    # Check if tracker is active
    if not guild_tracker.tracker_active:
        return f"Tracker not active, use **{ctx.prefix}init start** to begin.", None

    # Check if player is in the initiative order
    if player_name not in guild_tracker.combatant_dict:
        return f"{player_name} is not in the initiative order.", None

    # Get current player's initiative and validate new initiative
    current_init = guild_tracker.combatant_dict[player_name]
    if new_init > current_init:
        return f"New initiative ({new_init}) must be lower than original ({current_init}).", None

    # Find the current active player
    active_player = None
    for sublist in guild_tracker.tracker:
        if "--->" in sublist:
            active_player = sublist[1]
            break

    # Check if it's the player's turn
    if player_name != active_player:
        return "Delay should be done on your turn.", None

    # Update initiative and rebuild tracker
    guild_tracker.combatant_dict[player_name] = new_init
    guild_tracker.tracker = guild_tracker.build_init_table()

    # Update database
    update_database_func(ctx, guild_tracker)

    # Generate response
    embed, table = guild_tracker.embed_template()
    message = (
        f"Initiative for {player_name} has been delayed to {new_init}. Initiative order has been recalculated.\n{table}"
    )
    return message, embed


def handle_npc_logic(
    guild_tracker,
    npc_name,
    init_bonus,
    ctx,
    parse_mention_func,
    find_active_player_func,
    update_database_func,
    set_active_player_func,
):
    """Handle the core logic for adding NPCs to initiative."""
    # Handle Discord user mentions
    npc_name = parse_mention_func(ctx, npc_name)

    # Check if NPC is already in the order
    if npc_name in guild_tracker.combatant_dict:
        return f"{npc_name} is already used in the initiative order.", None

    # Roll initiative
    initiative_roll = die_roll.roll("1d20").total
    total_initiative = initiative_roll + init_bonus

    # Find and preserve the current active player
    active_player = find_active_player_func(guild_tracker)

    # Add NPC to combatant dictionary
    guild_tracker.combatant_dict[npc_name] = total_initiative
    guild_tracker.turn = ["    " for _ in range(len(guild_tracker.combatant_dict))]
    guild_tracker.tracker = guild_tracker.build_init_table()

    if guild_tracker.tracker_active:
        # Update database
        update_database_func(ctx, guild_tracker)

        # Restore active player marker
        set_active_player_func(guild_tracker, active_player)

        message = (
            f"Adding {npc_name} to active combat round.\n"
            f"Initiative is ({initiative_roll}+{init_bonus}) {total_initiative}."
        )
    else:
        message = f"{npc_name}'s Initiative is ({initiative_roll}+{init_bonus}) {total_initiative}."

    return message, None


def handle_remove_logic(
    guild_tracker, name, ctx, parse_mention_func, find_active_player_func, update_database_func, set_active_player_func
):
    """Handle the core logic for removing combatants from initiative."""
    # Parse mention to get display name
    name = parse_mention_func(ctx, name)

    # Check if the name is in the initiative order
    if name not in guild_tracker.combatant_dict:
        return f"{name} is not in the initiative order.", None

    # Handle active tracker scenario
    if guild_tracker.tracker_active:
        # Find the currently active player
        active_user = find_active_player_func(guild_tracker)

        if active_user == name:
            return f"{name} is the active combatant, please advance the turn before removing them.", None

        # Remove the combatant
        del guild_tracker.combatant_dict[name]
        guild_tracker.turn = ["    " for _ in range(len(guild_tracker.combatant_dict))]
        guild_tracker.tracker = guild_tracker.build_init_table()

        # Update database
        update_database_func(ctx, guild_tracker)

        # Restore the active player marker
        set_active_player_func(guild_tracker, active_user)

        return f"{name} has been removed from the initiative table.", None
    else:
        # Handle inactive tracker scenario
        del guild_tracker.combatant_dict[name]
        guild_tracker.turn = ["    " for _ in range(len(guild_tracker.combatant_dict))]
        guild_tracker.tracker = guild_tracker.build_init_table()
        return f"{name} has been removed from the initiative table.", None


def handle_update_logic(
    guild_tracker,
    name,
    new_init,
    ctx,
    parse_mention_func,
    find_active_player_func,
    update_database_func,
    set_active_player_func,
):
    """Handle the core logic for updating combatant initiative."""
    # Parse mention to get display name
    name = parse_mention_func(ctx, name)

    # Check if the name is in the initiative order
    if name not in guild_tracker.combatant_dict:
        return f"{name} is not in the initiative order.", None

    # Find and preserve the current active player if tracker is active
    active_player = None
    if guild_tracker.tracker_active:
        active_player = find_active_player_func(guild_tracker)

    # Update the combatant's initiative
    guild_tracker.combatant_dict[name] = new_init
    guild_tracker.tracker = guild_tracker.build_init_table()

    # Update database if tracker is active
    if guild_tracker.tracker_active:
        update_database_func(ctx, guild_tracker)

        # Restore active player marker if there was one
        if active_player:
            set_active_player_func(guild_tracker, active_player)

    return f"{name}'s initiative has been manually set to {new_init}.", None


def handle_active_logic(guild_tracker, name, ctx, parse_mention_func, set_active_player_func):
    """Handle the core logic for setting the active combatant."""
    # Parse mention to get display name
    name = parse_mention_func(ctx, name)

    # Check if tracker is active
    if not guild_tracker.tracker_active:
        return "Initiative tracker is not active.", None

    # Check if the name is in the initiative order
    if name not in guild_tracker.combatant_dict:
        return f"{name} is not in the initiative order.", None

    # Reset all turn markers and set the active player
    guild_tracker.turn = ["    " for _ in range(len(guild_tracker.combatant_dict))]
    set_active_player_func(guild_tracker, name)
    guild_tracker.tracker = guild_tracker.build_init_table()

    # Generate response
    embed, table = guild_tracker.embed_template()
    return f"{name} is now the active combatant.\n{table}", embed


def handle_rebuild_logic(guild_tracker, ctx):
    """Handle the core logic for rebuilding the tracker from database."""
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
    message = f"Initiative tracker has been reset and rebuilt from the backup database.\n{table}"
    return message, embed


def handle_attack_logic(ctx, bonus, roll_type, init_obj):
    """Handle the core logic for player attack rolls."""
    # Valid roll types mapping
    valid_roll_types = {"d": "1d20", "ad": "1ad20", "dd": "1dd20"}

    # Validate roll type
    if roll_type not in valid_roll_types:
        return f"Invalid roll type: {roll_type}. Valid types are: {', '.join(valid_roll_types.keys())}", None

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

    return f"{ctx.author.mention} rolled to attack.", attack_embed


def handle_attack_npc_logic(ctx, bonus, roll_type):
    """Handle the core logic for NPC attack rolls."""
    # Valid roll types mapping
    valid_roll_types = {"d": "1d20", "ad": "1ad20", "dd": "1dd20"}

    # Validate roll type
    if roll_type not in valid_roll_types:
        return f"Invalid roll type: {roll_type}. Valid types are: {', '.join(valid_roll_types.keys())}", None

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

    return f"{ctx.author.mention} rolled an **NPC attack**.", attack_embed
