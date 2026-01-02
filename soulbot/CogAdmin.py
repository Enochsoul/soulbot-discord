"""Cog used for administration of the all other bot Cogs."""

import json
import os

import discord
from discord.ext import commands
from loguru import logger
from tabulate import tabulate


class CogAdmin(discord.Cog, name="Cog Admin"):
    """Class definition for administrating Cogs, inherits from discord extension Cog class."""

    def __init__(self, bot):
        self.bot = bot
        logger.info("CogAdmin cog initialized")

    @commands.group(help="Commands for administrating Cogs.", name="cogs")
    @commands.has_guild_permissions(manage_guild=True)
    async def cogs_group(self, ctx):
        """Base level cogs group command, returns error to the channel if command is incomplete."""
        if ctx.invoked_subcommand is None:
            await ctx.send(f"Additional arguments required, see **{ctx.prefix}help cogs** for available options.")

    @cogs_group.command(help="List available Cogs.", name="list")
    async def list_cogs(self, ctx):
        """Command to list all Cogs, returns discord embed with table of cogs and their states."""
        cogs_list = [cog.split(".")[0] for cog in os.listdir("cogs") if ".py" in cog]
        cog_status = []
        for cog in cogs_list:
            expanded_cog = "".join(map(lambda x: x if x.islower() else " " + x, cog)).strip()
            if self.bot.get_cog(expanded_cog) is None:
                loaded = False
            else:
                loaded = True
            if cog in self.bot.config["load_cogs"]:
                startup = True
            else:
                startup = False
            cog_status.append([cog, loaded, startup])
        cogs_table = tabulate(cog_status, headers=["Cog Name", "Loaded?", "Startup?"], tablefmt="simple")
        embed = discord.Embed(title="Available Cogs:", description=f"```{cogs_table}```")
        logger.info(f"User {ctx.author} requested cog list")
        await ctx.send(embed=embed)

    @cogs_group.command(help="Activate a Cog. Case sensitive.", name="load")
    async def load_cog(self, ctx, cog: str):
        """Load Cog by name supplied with the command.

        :param ctx: Context manager from the base bot.
        :param cog: Name of the Cog to add to the startup config.
        :return: Success or Fail message to the channel.
        """
        try:
            self.bot.load_extension(f"cogs.{cog}")
            logger.info(f"User {ctx.author} loaded cog: {cog}")
        except discord.ExtensionAlreadyLoaded:
            logger.warning(f"User {ctx.author} tried to load already loaded cog: {cog}")
            await ctx.send(f"{cog} is already loaded.")
        except discord.ExtensionNotFound:
            logger.warning(f"User {ctx.author} tried to load non-existent cog: {cog}")
            await ctx.send(f"{cog} not found.")
        except Exception as e:
            logger.error(f"Error loading cog {cog}: {e}")
            await ctx.send(f"Error: {e}")
        else:
            await ctx.send(f"{cog} loaded.")

    @cogs_group.command(help="Deactivate a Cog. Case sensitive.", name="unload")
    async def unload_cog(self, ctx, cog: str):
        """Unload Cog by name supplied with the command.

        :param ctx: Context manager from the base bot.
        :param cog: Name of the Cog to add to the startup config.
        :return: Success or Fail message to the channel.
        """
        try:
            self.bot.unload_extension(f"cogs.{cog}")
            logger.info(f"User {ctx.author} unloaded cog: {cog}")
        except discord.ExtensionNotFound:
            logger.warning(f"User {ctx.author} tried to unload non-existent cog: {cog}")
            await ctx.send(f"{cog} not found.")
        except Exception as e:
            logger.error(f"Error unloading cog {cog}: {e}")
            await ctx.send(f"Error: {e}")
        else:
            await ctx.send(f"{cog} unloaded.")

    @cogs_group.command(help="Reload a Cog. Case sensitive.", name="reload")
    async def reload_cog(self, ctx, cog: str):
        """Reload Cog by name supplied with the command.

        :param ctx: Context manager from the base bot.
        :param cog: Name of the Cog to add to the startup config.
        :return: Success or Fail message to the channel.
        """
        try:
            self.bot.unload_extension(f"cogs.{cog}")
            self.bot.load_extension(f"cogs.{cog}")
            logger.info(f"User {ctx.author} reloaded cog: {cog}")
        except discord.ExtensionAlreadyLoaded:
            logger.warning(f"User {ctx.author} tried to reload already loaded cog: {cog}")
            await ctx.send(f"{cog} is already loaded.")
        except discord.ExtensionNotFound:
            logger.warning(f"User {ctx.author} tried to reload non-existent cog: {cog}")
            await ctx.send(f"{cog} not found.")
        except discord.ExtensionNotLoaded:
            logger.warning(f"User {ctx.author} tried to reload unloaded cog: {cog}")
            await ctx.send(f"{cog} wasn't loaded, please load it first.")
        except Exception as e:
            logger.error(f"Error reloading cog {cog}: {e}")
            await ctx.send(f"Error: {e}")
        else:
            await ctx.send(f"{cog} reloaded.")

    @cogs_group.command(help="Add Cog to startup list.")
    async def startup(self, ctx, cog: str):
        """Adds supplied Cog name to the bot configuration so it will be automatically
        loaded on next startup.  Returns success or fail message to the channel.

        :param ctx: Context manager from the base bot.
        :param cog: Name of the Cog to add to the startup config.
        :return: Success or Fail message to the channel.
        """
        cogs_list = [cog.split(".")[0] for cog in os.listdir("cogs") if ".py" in cog]
        if cog not in self.bot.config["load_cogs"]:
            if cog in cogs_list:
                # Update running config.
                self.bot.config["load_cogs"].append(cog)
                # Write running config out to disk.
                with open("soulbot.conf", "w") as outfile:
                    json.dump(self.bot.config, outfile)
                logger.info(f"User {ctx.author} added cog {cog} to startup list")
                await ctx.send(f"{cog} added to startup list.")
            else:
                logger.warning(f"User {ctx.author} tried to add invalid cog to startup: {cog}")
                await ctx.send(f"{cog} is not a valid Cog name.")
        else:
            await ctx.send(f"{cog} is already in the startup list.")

    @cogs_group.command(help="Remove Cog from startup list.")
    async def remove(self, ctx, cog: str):
        """Adds supplied Cog name to the bot configuration so it will be automatically
        loaded on next startup.

        :param ctx: Context manager from the base bot.
        :param cog: Name of the Cog to add to the startup config.
        :return: Success or Fail message to the channel.
        """
        cogs_list = [cog.split(".")[0] for cog in os.listdir("cogs") if ".py" in cog]
        if cog in self.bot.config["load_cogs"]:
            if cog in cogs_list:
                self.bot.config["load_cogs"].remove(cog)
                with open("soulbot.conf", "w") as outfile:
                    json.dump(self.bot.config, outfile)
                logger.info(f"User {ctx.author} removed cog {cog} from startup list")
                await ctx.send(f"{cog} removed from the startup list.")
            else:
                logger.warning(f"User {ctx.author} tried to remove invalid cog from startup: {cog}")
                await ctx.send(f"{cog} is not a valid Cog name.")
        else:
            await ctx.send(f"{cog} is not in the startup list.")

    @list_cogs.error
    @load_cog.error
    async def cog_command_error(self, ctx, error):
        """Sends any command errors to the channel."""
        logger.error(f"CogAdmin command error: {error}")
        await ctx.send(str(error))


def setup(bot):
    """Discord module required setup for Cog loading."""
    logger.info("Loading CogAdmin cog")
    bot.add_cog(CogAdmin(bot))
