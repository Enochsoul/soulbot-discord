"""Cog for generating randomized dungeon rooms."""
import discord
from discord.ext import commands
import json
import random

with open('data/DungeonGen.json') as input:
    dungeongen_db = json.load(input)

def embed_template(dungeon_desc:str, exits:list):
    """Dungeon Generator embed template."""
    embed_template = discord.Embed(title="**Dungeon Generator**",
                                    description={dungeon_desc},
                                    color=0xff0000)
    embed_template.add_field(name="__Exits:__",
                            value="",
                            inline=False)
    for exit in exits:
        embed_template.add_field(name={exit},
                                value="",
                                inline=True)
    return embed_template


class DungeonGen(commands.Cog, name="Dungeon Generator"):
    """Class definition for Dungeon Generator Cog."""
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.group(help="Generate a random dungeon room description and contents.")
    async def dg(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(f"Additional arguments required, see "
                           f"**{ctx.prefix}help dg** for available options.")
    
    @dg.command(help="Generate a new room.")
    async def new(self, ctx):
        atmosphere = random.choice(dungeongen_db['atmosphere'])
        floor = random.choice(dungeongen_db['floor'])
        walls_ceiling = random.choice(dungeongen_db['walls_ceiling'])
        furniture = random.choice(dungeongen_db['furniture'])
        exits = random.sample(dungeongen_db['exits'], random.randint(1,4))
        mobs = random.choice(dungeongen_db['mobs'])
        treasure = random.choice(dungeongen_db['treasure'])
        dungeon_desc = f"{atmosphere}\n{floor}\n{walls_ceiling}\n{furniture}\n{mobs}\n{treasure}"
        print(dungeon_desc)
        print(exits)
        embed = embed_template(dungeon_desc, exits)
        print(embed.description)
        await ctx.send("Testing!")

def setup(bot):
    """Discord module required setup for Cog loading."""
    bot.add_cog(DungeonGen(bot))