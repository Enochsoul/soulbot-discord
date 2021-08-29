"""Cog for generating randomized dungeon rooms."""
import discord
from discord.ext import commands
import json
import random
from soulbot_support import soulbot_db

with open('data/DungeonGen.json') as file_in:
    dungeongen_db = json.load(file_in)


def embed_template(ctx, dungeon_desc: str, exits: list):
    """Dungeon Generator embed template."""
    dungeongen_embed = discord.Embed(title="**Dungeon Generator**",
                                     description=f"{dungeon_desc}",
                                     color=0xff0000)
    dungeongen_embed.add_field(name="__Exits:__",
                               # value="\n\u200b",
                               value=f"Enter **{ctx.prefix}dg go <exit #>** to pick a direction.",
                               inline=False)
    for e in exits:
        dungeongen_embed.add_field(name=f"{exits.index(e)+1}) {list(e.values())[0]}",
                                   value="** **", inline=False)
    return dungeongen_embed


def create_room():
    atmosphere = random.choice(dungeongen_db['atmosphere'])
    floor = random.choice(dungeongen_db['floor'])
    walls_ceiling = random.choice(dungeongen_db['walls_ceiling'])
    furniture = random.choice(dungeongen_db['furniture'])
    exits = random.sample(dungeongen_db['exits'], random.randint(1, 4))
    mobs = random.choice(dungeongen_db['mobs'])
    treasure = random.choice(dungeongen_db['treasure'])
    dungeon_desc = f"{atmosphere}\n{floor}\n{walls_ceiling}\n{furniture}\n{mobs}\n{treasure}"
    return dungeon_desc, exits


class DungeonDelve:
    """Class definition for the Dungeon Delver."""
    def __init__(self):
        self.dungeon = {}
        self.party_loot = []
        self.current_room_id = 0
        self.last_room = 0

    def reset(self):
        """Resets all current dungeon values to default."""
        self.dungeon = {}
        self.party_loot = []
        self.current_room_id = 0
        self.last_room = 0

    def create_dungeon(self, room_num: int):
        """Creates a unique random dungeon with the supplied number of rooms."""
        entrance_desc = "The sun sits high in a bright blue sky, dotted with fluffy white clouds.  " \
                        "Perfect weather for doing anything but diving into a dungeon.\nBefore you is a rugged stone " \
                        "wall, with a heavy wooden door set into an opening in that wall. A sign mounted high on the " \
                        "wall reads:\n\t\t**Welcome to the Dungeon of the Endless.\n\t\tMay you find your fortune in " \
                        "it's ever shifting corridors.**\n"
        entrance_exit = [{1: "Enter the Dungeon"}]
        self.dungeon[0] = {"description": entrance_desc, "exits": entrance_exit}
        # Create all of the rooms.
        while len(self.dungeon) < room_num + 1:
            self.dungeon[len(self.dungeon)] = {"description": create_room()[0], "exits": []}
        # First pass loop to link the rooms.
        for room in self.dungeon:
            room_list = list(range(1, room_num + 1))
            if room != 0:
                room_list.remove(room)
                exits = random.sample(dungeongen_db['exits'], random.randint(1, 4))
                for e in exits:
                    exit_complete = False
                    while not exit_complete:
                        destination_room = random.choice(room_list)
                        if room in self.dungeon[destination_room]["exits"]:
                            room_list.remove(destination_room)
                            destination_room = random.choice(room_list)
                        if len(self.dungeon[room]["exits"]) < 3 and len(self.dungeon[destination_room]["exits"]) < 2:
                            destination_door = {room: random.choice(dungeongen_db['exits'])}
                            source_door = {destination_room: e}
                            self.dungeon[room]["exits"].append(source_door)
                            self.dungeon[destination_room]["exits"].append(destination_door)
                            room_list.remove(destination_room)
                            exit_complete = True
                        else:
                            break
        return


dungeongen_obj = {}
guild_list = soulbot_db.config_all_prefix_load()
for k in guild_list:
    dungeongen_obj[k] = DungeonDelve()


class DungeonGen(commands.Cog, name="Dungeon Generator"):
    """Class definition for Dungeon Generator Cog."""

    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.group(help="Generate a random dungeon room description and contents.")
    async def dg(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(f"Additional arguments required, see "
                           f"**{ctx.prefix}help dg** for available options.")

    @dg.command(help="Generate a new random dungeon.  Specify number of rooms in the dungeon, less than 100.")
    async def new(self, ctx, room_count: int):
        if room_count > 100:
            await ctx.send("You think you'll get through that many rooms?")
        if ctx.guild.id in dungeongen_obj:
            dungeongen_obj[ctx.guild.id].reset()
            dungeongen_obj[ctx.guild.id].create_dungeon(room_count)
            desc = dungeongen_obj[ctx.guild.id].dungeon[0]["description"]
            exits = dungeongen_obj[ctx.guild.id].dungeon[0]["exits"]
        else:
            dungeongen_obj[ctx.guild.id] = DungeonDelve()
            dungeongen_obj[ctx.guild.id].create_dungeon(room_count)
            desc = dungeongen_obj[ctx.guild.id].dungeon[0]["description"]
            exits = dungeongen_obj[ctx.guild.id].dungeon[0]["exits"]
        await ctx.send(embed=embed_template(ctx, desc, exits))

    @dg.command(help="Enter the number of the direction to go.")
    async def go(self, ctx, direction: int):
        if len(dungeongen_obj[ctx.guild.id].dungeon) == 0:
            await ctx.send('Please create a new dungeon first.')
        else:
            directions = dungeongen_obj[ctx.guild.id].dungeon[dungeongen_obj[ctx.guild.id].current_room_id]['exits']
            chosen_exit = directions[direction - 1]
            new_room_desc = dungeongen_obj[ctx.guild.id].dungeon[list(chosen_exit.keys())[0]]["description"]
            new_room_exits = dungeongen_obj[ctx.guild.id].dungeon[list(chosen_exit.keys())[0]]["exits"]
            embed = embed_template(ctx, new_room_desc, new_room_exits)
            dungeongen_obj[ctx.guild.id].current_room_id = list(chosen_exit.keys())[0]
            await ctx.send(f'Exiting to {list(chosen_exit.values())[0]}', embed=embed)

    @dg.command(help="Look at the contents of the current room.")
    async def look(self, ctx):
        description = dungeongen_obj[ctx.guild.id].dungeon[dungeongen_obj[ctx.guild.id].current_room_id]["description"]
        exits = dungeongen_obj[ctx.guild.id].dungeon[dungeongen_obj[ctx.guild.id].current_room_id]["exits"]
        embed = embed_template(ctx, description, exits)
        await ctx.send(embed=embed)

    @new.error
    @go.error
    async def new_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send('Please indicate the number of rooms for the new dungeon.')
        else:
            print(error)


def setup(bot):
    """Discord module required setup for Cog loading."""
    bot.add_cog(DungeonGen(bot))
