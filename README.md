# soulbot-discord
Version 2.0

Discord bot for my 13th Age RPG group.

A work in progress I made for my group, with no warranty implied or expressed.  I'm not a professional developer, so it's likely rough AF, but it works.  I usually squash bugs as my group finds them, if you find something please submit an issue on github.

Designed to run as a standalone bot for a single discord server.  If you invite it to multiple servers all activity will be shared, so don't do that.

### Install(Updated in 2.0):
1) git clone to your chosen location.
2) Rename soulbot.conf.default to soulbot.conf.
3) Fill out the discord token at minimum in the config file.  See below for other config file options.
4) Build environment from the requirements.txt.
    - Can be in a virtual environment(recommended, it's how it was developed) or use the main system Python instance.
5) Run the soulbot.py script to start up the bot.
6) Create Discord Role called GM or DM, and assign to the user acting as the DM.  No special permissions required.  Access to some commands is restricted to user with this Role name.
7) Go to Discord dev applications for your bot, enable Server Members Intent under the Bot section.
7) Cog administration restricted to server admin/guild manager permissions.  

---  
### Current Features:
- Features modularized in Discord Cogs.  Notes below on how to add your own Cogs.
    - Cog Administration Cog:
        - Loads by default to manage other Cogs.
    - Dice Roller Cog:
        - Loads by default, basic functionality.
        - Generates random number like rolling dice. Uses the format of NdN+N with highlighting of natural max rolls.  
        - No automatic rerolls or dice popping.
        - Three different methods of generating numbers.
            - Defaults to python based randint function.
            - Generates array of random numbers, and selects randomly from these arrays(d20, d12, d10, d8, d6).  Uses default method for all other dice rolls.
            - Random.org API to generate random numbers.  Requires account set up on random.org and API key supplied in config file.
    - Initiative Tracker Cog:  
        - Built for 13th Age, but should also work for DnD 4e, 5e or other OGL/d20 systems if you ignore the Escalation die.
        - Players roll initiative and get added to a tracking table before combat begins.
        - Players can delay their initiative to a set number smaller than their current.
        - DM can create NPCs, add them at any time before or after combat starts.
            - NPC names should have no spaces or contained in quotation marks. EG: Bad_Guy1 or "Bad Guy1"
        - DM can update any NPC or player's initiative to any value as needed.
        - DM can remove any player or NPC from the initiative order.
        - DM commands on players can be referenced by Discord @ mention.
        - DM can directly change who has the active turn.   
        - DM can set/change the Escalation die.
        - Commands advance the initiative order, indicating who's turn it currently is and tracks the Escalation Die(13th Age specific).
        - Initiative database written to disk, recoverable with DM command if there are bot issues.
        - Attack dice roller for PCs that use the Escalation die.  Rolls 1d20 plus supplied player bonus and adds escalation dice automatically.
            - Breaks out natural roll vs total roll.
            - Flags Natural, +2 and +4 Crits.
        - Attack dice roller for NPCs that don't use the Escalation die.  Rolls 1d20 plus supplied bonus.  Otherwise identical to PC attack roller.
    - Chaos Mage Commands Cog:
        - 13th Age specific, you'll still need the book.
        - Tracks each Chaos Mage player's spell determination pool separately if there are multiple.
        - Tracks as described under Chaos Magic Categories(pg15 13TW), with 'Stones' in a pool.  
        - Command draws randomly out of the pool, which is refilled automatically when only one option is left.
        - Command to randomly draw an element for Chaos Mages with one or more Warp Talents.
    - Next Game Schedule Cog:
        - Shows when the next game is in several different timezones, and time until the next game.
        - Toggleable next game @mention announcement in the last hour before the game.
        - Upgraded this module. If you used a version previous to 2.0.2, you'll need to run the '!next reset' to wipe
          the DB table and rebuild it for the new data type introduced in 2.0.2.
    - Quotes Cog:
        - Add quotations to the database.
        - Recall random quotations from the database.
        - Search for text and display a random quote with matching text.

---
### Configuration File(New in 2.0):

A default configuration file(soulbot.conf.default) is included in the repo, it looks like this:
```
{
  "discord_token": "",
  "command_prefix": "!",
  "load_cogs": [],
  "dice_roller": "default",
  "random_org_key": ""
}
```
Rename it to soulbot.conf and change the options as necessary.

The options are as follows:
- discord_token(Required): Place your discord bot API token inside the quotations here.
- command_prefix(Required): Change this if you want a different default prefix from the start.  Can also be changed by a command inside the bot.
- load_cogs: This is a comma separated list of quotation wrapped cog names that the bot will try to load when starting up.  Names are the name of the file of the Cog without '.py' in the cogs directory.  EG: "ChaosMageCommands"
- dice_roller(Required): Configures the type of dice roller to use, wrapped in quotations.  Options are: default, array, random_org.
- random_org_key: If you want to use the random.org API for your random number generation, put your API key here inside the quotations. 

---
### Cogs(New in 2.0):

Want to load your own Cogs?  Place the .py file in the cogs folder, and use the Cogs Admin module to load it and/or configure it to load on start.  No bot restart required.  

I don't guarantee that any other cogs will work, but they should if they are written for the python discord module.  This is just a side effect of how I decided to implement Cog loading.  Use at your own risk.  