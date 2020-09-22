"""Cog used for administration of the all other bot Cogs."""

import os
import json

import discord
from discord.ext import commands
from tabulate import tabulate
from soulbot import bot_config


class CogAdmin(commands.Cog, name='Cog Admin'):
    """Class definition for administrating Cogs, inherits from discord extension Cog class.
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.group(help='Commands for administrating Cogs.', name='cogs')
    @commands.has_guild_permissions(manage_guild=True)
    async def cogs_group(self, ctx):
        """Base level cogs group command, returns error to the channel if command is incomplete."""
        if ctx.invoked_subcommand is None:
            await ctx.send(f"Additional arguments required, "
                           f"see **{ctx.prefix}help cogs** for available options.")

    @cogs_group.command(help='List available Cogs.', name='list')
    async def list_cogs(self, ctx):
        """Command to list all Cogs, returns discord embed with table of cogs and their states."""
        cogs_list = [cog.split('.')[0] for cog in os.listdir('cogs') if '.py' in cog]
        cog_status = []
        for cog in cogs_list:
            expanded_cog = ''.join(map(lambda x: x if x.islower() else " " + x, cog)).strip()
            if self.bot.get_cog(expanded_cog) is None:
                loaded = False
            else:
                loaded = True
            if cog in bot_config['load_cogs']:
                startup = True
            else:
                startup = False
            cog_status.append([cog, loaded, startup])
        cogs_table = tabulate(cog_status,
                              headers=['Cog Name', 'Loaded?', 'Startup?'],
                              tablefmt='simple')
        embed = discord.Embed(title="Available Cogs:", description=f'```{cogs_table}```')
        await ctx.send(embed=embed)

    @cogs_group.command(help='Activate a Cog. Case sensitive.', name='load')
    async def load_cog(self, ctx, cog: str):
        """Load Cog by name supplied with the command.

        :param ctx: Context manager from the base bot.
        :param cog: Name of the Cog to add to the startup config.
        :return: Success or Fail message to the channel.
        """
        try:
            self.bot.load_extension(f'cogs.{cog}')
        except commands.ExtensionAlreadyLoaded:
            await ctx.send(f'{cog} is already loaded.')
        except commands.ExtensionNotFound:
            await ctx.send(f'{cog} not found.')
        except Exception as e:
            await ctx.send(f'Error: {e}')
        else:
            await ctx.send(f'{cog} loaded.')

    @cogs_group.command(help='Deactivate a Cog. Case sensitive.', name='unload')
    async def unload_cog(self, ctx, cog: str):
        """Unload Cog by name supplied with the command.

        :param ctx: Context manager from the base bot.
        :param cog: Name of the Cog to add to the startup config.
        :return: Success or Fail message to the channel.
        """
        try:
            self.bot.unload_extension(f'cogs.{cog}')
        except commands.ExtensionNotFound:
            await ctx.send(f'{cog} not found.')
        except Exception as e:
            await ctx.send(f'Error: {e}')
        else:
            await ctx.send(f'{cog} unloaded.')

    @cogs_group.command(help='Reload a Cog. Case sensitive.', name='reload')
    async def reload_cog(self, ctx, cog: str):
        """Reload Cog by name supplied with the command.

        :param ctx: Context manager from the base bot.
        :param cog: Name of the Cog to add to the startup config.
        :return: Success or Fail message to the channel.
        """
        try:
            self.bot.unload_extension(f'cogs.{cog}')
            self.bot.load_extension(f'cogs.{cog}')
        except commands.ExtensionAlreadyLoaded:
            await ctx.send(f'{cog} is already loaded.')
        except commands.ExtensionNotFound:
            await ctx.send(f'{cog} not found.')
        except commands.ExtensionNotLoaded:
            await ctx.send(f"{cog} wasn't loaded, please load it first.")
        except Exception as e:
            await ctx.send(f'Error: {e}')
        else:
            await ctx.send(f'{cog} reloaded.')

    @cogs_group.command(help='Add Cog to startup list.')
    async def startup(self, ctx, cog: str):
        """Adds supplied Cog name to the bot configuration so it will be automatically
        loaded on next startup.  Returns success or fail message to the channel.

        :param ctx: Context manager from the base bot.
        :param cog: Name of the Cog to add to the startup config.
        :return: Success or Fail message to the channel.
        """
        cogs_list = [cog.split('.')[0] for cog in os.listdir('cogs') if '.py' in cog]
        if cog not in bot_config['load_cogs']:
            if cog in cogs_list:
                # Update running config.
                bot_config['load_cogs'].append(cog)
                # Write running config out to disk.
                with open('soulbot.conf', 'w') as outfile:
                    json.dump(bot_config, outfile)
                await ctx.send(f'{cog} added to startup list.')
            else:
                await ctx.send(f'{cog} is not a valid Cog name.')
        else:
            await ctx.send(f'{cog} is already in the startup list.')

    @cogs_group.command(help='Remove Cog from startup list.')
    async def remove(self, ctx, cog: str):
        """Adds supplied Cog name to the bot configuration so it will be automatically
        loaded on next startup.

        :param ctx: Context manager from the base bot.
        :param cog: Name of the Cog to add to the startup config.
        :return: Success or Fail message to the channel.
        """
        cogs_list = [cog.split('.')[0] for cog in os.listdir('cogs') if '.py' in cog]
        if cog in bot_config['load_cogs']:
            if cog in cogs_list:
                bot_config['load_cogs'].remove(cog)
                with open('soulbot.conf', 'w') as outfile:
                    json.dump(bot_config, outfile)
                await ctx.send(f'{cog} removed from the startup list.')
            else:
                await ctx.send(f'{cog} is not a valid Cog name.')
        else:
            await ctx.send(f'{cog} is not in the startup list.')

    @list_cogs.error
    @load_cog.error
    async def cog_command_error(self, ctx, error):
        """Sends any command errors to the channel."""
        await ctx.send(error)


def setup(bot):
    """Discord module required setup for Cog loading."""
    bot.add_cog(CogAdmin(bot))
