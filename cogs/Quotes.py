"""Cog for managing Quotes database."""
import requests
from soulbot_support import soulbot_db
from discord.ext import commands
import re


class Quotes(commands.Cog):
    """Class definition for Quotes Cog."""
    def __init__(self, bot):
        self.bot = bot

    @commands.group(help="Display a random quote submitted to the database, or one containing a search string.  "
                         "Just like the internet, everything submitted is forever.")
    async def quote(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(soulbot_db.quote_db_random(ctx.guild.id))

    @quote.group(name="add", help="Add a quote to the database.")
    async def add_quote(self, ctx, *, quote_text: str):
        for _ in range(0, len(re.findall('@', quote_text))):
            if len(re.findall('<@[!|&]\d+>', quote_text)) > 0:
                mentioned_users = re.findall('<@[!|&]\d+>', quote_text)
                for member in mentioned_users:
                    if '!' in member:
                        member_id = member.replace('<', '').replace('>', '').replace('!', '').replace('@', '')
                        member_name = ctx.guild.get_member(int(member_id)).display_name
                    else:
                        member_name = ""
                    quote_text = quote_text.replace(member, member_name)
            elif '@here' in quote_text or '@everyone' in quote_text:
                quote_text = quote_text.replace('@', '')
                soulbot_db.quote_db_add(quote_text, ctx.guild.id)
        soulbot_db.quote_db_add(quote_text, ctx.guild.id)
        await ctx.send(f'Added "{str(quote_text)}" to quotes database.')

    @quote.group(name='search', help='Search for a quote containing a specific term.')
    async def quote_search(self, ctx, *, search_term: str):
        await ctx.send(soulbot_db.quote_db_search(search_term, ctx.guild.id))

    @commands.command(help="Very Vahti like.", name='vahti', case_insensitive=True)
    async def whale(self, ctx):
        response = requests.get('https://sv443.net/jokeapi/v2/joke/Pun'
                                '?blacklistFlags=nsfw,religious,political,racist,sexist',
                                headers={'Accept': 'application/json'})
        output = response.json()
        if output['type'] == 'twopart':
            await ctx.send(f"\n{output['setup']}\n\n{output['delivery']}")
        else:
            await ctx.send(f"{output['joke']}")

    @quote.error
    @whale.error
    @add_quote.error
    @quote_search.error
    async def cog_command_error(self, ctx, error):
        await ctx.send(f'Experienced the following error:\n{error}')


def setup(bot):
    """Discord module required setup for Cog loading."""
    bot.add_cog(Quotes(bot))
