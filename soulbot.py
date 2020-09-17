import json

from discord.ext import commands

with open('soulbot.conf', "r") as config:
    bot_config = json.load(config)
token = bot_config['discord_token']
bot = commands.Bot(command_prefix=bot_config['command_prefix'])


@bot.command(help="Changes the bot command prefix.", name='setprefix')
@commands.has_guild_permissions(manage_guild=True)
async def set_prefix(ctx, prefix: str):
    bot_config['command_prefix'] = prefix
    bot.command_prefix = prefix
    with open('soulbot.conf', 'w') as outfile:
        json.dump(bot_config, outfile)
    await ctx.send(f"Prefix now set to {prefix}.")


@set_prefix.error
async def on_prefix_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f"{error}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CommandNotFound):
        await ctx.send(f"{ctx.prefix}{ctx.invoked_with} is not a valid command.  "
                       f"See **{ctx.prefix}help** for available commands.")


# =========================================================
# Bot Start
# =========================================================

@bot.event
async def on_ready():
    print(f"{bot.user.name} has connected to Discord.")


if __name__ == "__main__":
    bot.load_extension('CogAdmin')
    bot.load_extension('DiceRoller')
    for cog in bot_config['load_cogs']:
        try:
            bot.load_extension(f'cogs.{cog}')
        except Exception as e:
            print(f'There was a problem loading Cog {cog}.\nException:\n{e}')
try:
    bot.run(token)
except Exception as e:
    print(f'Got the following error trying to startup the bot, check your config and try again.\n\n{e}')
