"""Cog for managing Quotes database."""

import re
from typing import Any, Dict, Match, Optional

import discord
import loguru
import requests
import soulbot_support
from discord.ext import commands


class Quotes(commands.Cog):
    """Class definition for Quotes Cog."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        loguru.logger.info("Quotes cog initialized")

    @commands.group(
        help="Display a random quote submitted to the database, or one containing a search string. "
        "Just like the internet, everything submitted is forever."
    )
    async def quote(self, ctx: commands.Context) -> None:
        """Base quote command - shows random quote if no subcommand."""
        if ctx.invoked_subcommand is None:
            random_quote: str = soulbot_support.soulbot_db.quote_db_random(
                ctx.guild.id
            )
            loguru.logger.info(
                f"User {ctx.author} requested random quote in {ctx.guild.name}"
            )
            await ctx.send(random_quote)

    @quote.command(name="add", help="Add a quote to the database.")
    async def add_quote(
        self, ctx: commands.Context, *, quote_text: str
    ) -> None:
        """Add a quote to the database, converting mentions to display names."""
        try:
            processed_quote: str = self._process_mentions(ctx, quote_text)
            soulbot_support.soulbot_db.quote_db_add(
                processed_quote, ctx.guild.id
            )
            loguru.logger.info(
                f"User {ctx.author} added quote in {ctx.guild.name}: {processed_quote[:50]}..."
            )
            await ctx.send(f'Added "{processed_quote}" to quotes database.')
        except Exception as e:
            loguru.logger.error(f"Failed to add quote by {ctx.author}: {e}")
            await ctx.send(f"Failed to add quote: {e}")

    @quote.command(
        name="search", help="Search for a quote containing a specific term."
    )
    async def quote_search(
        self, ctx: commands.Context, *, search_term: str
    ) -> None:
        """Search for quotes containing the specified term."""
        result: str = soulbot_support.soulbot_db.quote_db_search(
            search_term, ctx.guild.id
        )
        loguru.logger.info(
            f"User {ctx.author} searched quotes for: {search_term}"
        )
        await ctx.send(result)

    @commands.command(
        help="Get a random pun joke.", name="vahti", case_insensitive=True
    )
    async def vahti(self, ctx: commands.Context) -> None:
        """Get a random pun from JokeAPI."""
        try:
            joke: str = await self._fetch_random_joke()
            loguru.logger.info(f"User {ctx.author} requested a pun joke")
            await ctx.send(joke)
        except Exception as e:
            loguru.logger.error(f"Failed to fetch joke for {ctx.author}: {e}")
            await ctx.send(f"Failed to fetch joke: {e}")

    def _process_mentions(self, ctx: commands.Context, quote_text: str) -> str:
        """Process Discord mentions in quote text, converting them to display names."""
        # Handle user mentions (format: <@!123456789> or <@123456789>)
        user_mention_pattern: str = r"<@!?(\d+)>"

        def replace_user_mention(match: Match[str]) -> str:
            user_id: int = int(match.group(1))
            member: Optional[discord.Member] = ctx.guild.get_member(user_id)
            return member.display_name if member else f"@Unknown({user_id})"

        processed_text: str = re.sub(
            user_mention_pattern, replace_user_mention, quote_text
        )

        # Handle role mentions (format: <@&123456789>)
        role_mention_pattern: str = r"<@&(\d+)>"

        def replace_role_mention(match: Match[str]) -> str:
            role_id: int = int(match.group(1))
            role: Optional[discord.Role] = ctx.guild.get_role(role_id)
            return f"@{role.name}" if role else f"@UnknownRole({role_id})"

        processed_text = re.sub(
            role_mention_pattern, replace_role_mention, processed_text
        )

        # Handle @everyone and @here mentions - remove the @ to prevent actual mentions
        processed_text = processed_text.replace("@everyone", "everyone")
        processed_text = processed_text.replace("@here", "here")

        return processed_text

    async def _fetch_random_joke(self) -> str:
        """Fetch a random pun joke from the JokeAPI."""
        api_url: str = "https://sv443.net/jokeapi/v2/joke/Pun"
        params: Dict[str, str] = {
            "blacklistFlags": "nsfw,religious,political,racist,sexist"
        }
        headers: Dict[str, str] = {"Accept": "application/json"}

        response: requests.Response = requests.get(
            api_url, params=params, headers=headers, timeout=10
        )
        response.raise_for_status()

        joke_data: Dict[str, Any] = response.json()

        if joke_data.get("error", False):
            raise Exception(
                f"API Error: {joke_data.get('message', 'Unknown error')}"
            )

        if joke_data.get("type") == "twopart":
            return f"{joke_data['setup']}\n\n{joke_data['delivery']}"
        else:
            return joke_data.get("joke", "No joke found")

    @quote.error
    @add_quote.error
    @quote_search.error
    @vahti.error
    async def cog_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        """Handle errors for all commands in this cog."""
        if isinstance(error, commands.MissingRequiredArgument):
            loguru.logger.warning(
                f"Missing required argument in {ctx.command}: {error}"
            )
            await ctx.send(
                f"Missing required argument. Use `{ctx.prefix}help {ctx.command}` for usage."
            )
        elif isinstance(error, commands.CommandInvokeError):
            loguru.logger.error(
                f"Command invoke error in {ctx.command}: {error.original}"
            )
            await ctx.send(f"An error occurred: {error.original}")
        else:
            loguru.logger.error(
                f"Quotes command error in {ctx.command}: {error}"
            )
            await ctx.send(f"Command error: {error}")


def setup(bot: commands.Bot) -> None:
    """Discord module required setup for Cog loading."""
    loguru.logger.info("Loading Quotes cog")
    bot.add_cog(Quotes(bot))
