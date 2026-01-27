# soulbot-discord
Version 3.0

Discord bot for my 13th Age RPG group.

A work in progress I made for my group, with no warranty implied or expressed.  I'm not a professional developer, but it's a bit better than it used to be as I've had more development and code experience since I started this project.  I usually squash bugs as my group finds them, if you find something please submit an issue on github.

Version 3.0 is a near complete rewrite under the hood, with only a couple of minor functional changes evident at the user level.  It was an experiment both with a new IDE(Zed), and using AI(Claude 3.5).  I don't get to use Gen AI much in relation to what code I do write at work(Business decisions above my pay grade), so refactoring all the modules in this bot seemed like a good test, since I knew how everything functioned and could verify if what I got from the AI was actually doing what it was supposed to.  Did it work as expected?  Yes and no.  It seemed to introduce unnecessary complexity in some places that had to be fixed up, but overall it did a passable job.

### Dependencies
1) Some current version of Astral's uv. (https://docs.astral.sh/uv/)

### Install(Updated to use uv in 3.0):
1) git clone to your chosen location and change in to the directory.
2) Rename soulbot.conf.default to soulbot.conf.
3) Edit the file and fill out the discord token at minimum in the config file.  See below for other config file options.
4) Build environment with 'uv sync'.
    - uv uses the pyproject.toml file to create the virtual environment with all of the required dependencies.
5) Change into the soulbot directory and run the soulbot.py script with uv to start up the bot.
    - 'uv run soulbot.py'
6) Create Discord Role called GM or DM, and assign to the user acting as the DM.  No special permissions required.  Access to some commands is restricted to user with this Role name.
7) Go to Discord dev applications for your bot, enable Server Members Intent under the Bot section.
7) Cog administration restricted to server admin/guild manager permissions.  

### Docker Install(Updated for 3.0):
Dockerfile and compose YAML files included now.  The only caveat is that I've set the external volume to true, so it's expecting it to be created already, either done manually or because you're upgrading from a previous version.  If you're starting from scratch, remove the line and it should create the volume for you.

__To create volume:__
1) Create volume: docker volume create <vol_name>

__To build and run(From the base repo folder):__

docker compose up -- build

### Current Features(3.0):
- Features modularized in Discord Cogs.  Notes below on how to add your own Cogs.
    - Controlled by the config file in 3.0
    - Cog Administration Cog
        - Loads by default to manage other Cogs.
    - Dice Roller Cog:
        - Loads by default, basic functionality.
        - Generates random number like rolling dice. Uses the format of NdN+N with highlighting of natural max rolls.
          - Python random number generation for single dice rolls.
          - Numpy/Scipy based generation method for multi-dice rolls that better mimics the normal distribution of real life dice.
        - Multiple types of dice rolls:
          - Normal rolls(XdY)
          - Advantage/Disadvantage(XadY or XddY) - Roll 2 dice and take the highest/lowest value.
          - Exploding(XexY) - Roll 1 or more dice, any individual roll of max value is rerolled.  Rerolled max values are also rerolled.
          - Drop highest/lowest(XdhY or XdlY) - Similar to Advantage/Disadvantage, rolls any number of dice but drops the highest/lowest value.
        - Roll multiple dice types together in a single roll(XdY/XdZ)
          - Supports any of the above types of dice rolls.
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
        - Initiative table written to database on every turn, automatically recovered in the event of a bot reset.
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
        - Toggle-able next game @mention announcement in the last hour before the game.
    - Quotes Cog:
        - Add quotations to the database.
        - Recall random quotations from the database.
        - Search for text and display a random quote with matching text.
    - Config Commands:
      - Set the next game announce channel.
      - Set default interval to next game in days.
      - Set default start time of next game.
      - Set bot prefix.

### Configuration File:

A default configuration file(soulbot.conf.default) is included in the repo, it looks like this:
```
{
  "discord_token": "",
  "command_prefix": "!",
  "load_cogs": ["NextGameScheduler", "Quotes", "InitiativeTracker", "ChaosMageCommands"],
  "next_game_time": "15:00 MT",
  "next_game_interval": "14",
  "announce_channel": "general"
}
```
Rename it to soulbot.conf and change the options as necessary.

The options are as follows:
- discord_token(required): Place your discord bot API token inside the quotations here.
- command_prefix: Change this if you want a different default prefix from the start.  Can also be changed by a command inside the bot.
- load_cogs: This is a comma separated list of quotation wrapped cog names that the bot will try to load when starting up.  Names are the name of the file of the Cog without '.py' in the cogs directory.  EG: "ChaosMageCommands"
- next_game_time: The time used when using the next game scheduler.
- next_game_interval: The number of days until the next game when using the default next game scheduler.
- announce_channel: The name of the channel to announce the next game into.

---
### Cogs:

Want to load your own py-cord Cogs?  Place the .py file in the cogs folder, configure it to load in the config file and restart the bot.  

I don't guarantee that any other cogs will work, but they should if they are written for the python py-cord module.  This is just a side effect of how I decided to implement Cog loading.  Use at your own risk.

### Changes(2.2 to 3.0):
- Initiative tracker now auto-saves the state of every turn to the database.
  - In the event of a bot reset, the full state is restored automatically to all guilds/servers with active trackers.
  - The above change was as a result of a change in how the database is managed, and requires a table deletion if you're upgrading from a previous version.
- All the dice roll types noted above.
- Multi-dice rolls.
- Improved multi-dice rolling for better statistical distribution of results.
