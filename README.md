# soulbot-discord
Discord bot for my 13th Age RPG group.

A work in progress I made for my group, with no warranty implied or expressed.  I'm not a professional developer, so it's likely rough AF, but it works.  I usually squash bugs as my group finds them, if you find something feel free to submit a bug report on github.

Designed to run as a standalone bot for a single discord server.  If you invite it to multiple servers all activity will be shared, so don't do that.

### Install:
1) git clone to your chosen location.
2) create .env with your Discord bot token and default command prefix(can also be changed once the bot is active):

EG:
```  
  #.env
  DISCORD_TOKEN=(put your token here)
  COMMAND_PREFIX=!
```
3) Build environment from the requirements.txt.
    - Can be in a virtual environment(recommended, it's how it was developed) or use the main system Python instance.
4) Run the bot script.
5) Create Discord Role called GM or DM, and assign to the user acting as the DM.  No special permissions required.  Access to some commands is restricted to user with this Role name.  
  
### Current Features:
- OGL/d20 initiative tracking(As used by 13th Age), should also work for DnD 4e.
    - Players roll initiative and get added to a tracking table before combat begins.
    - Players can delay their initiative to a set number smaller than their current.
    - DM can create NPCs, add them at any time before or after combat starts.
        - NPC names should have no spaces or contained in quotation marks. EG: Bad_Guy1 or "Bad Guy1"
    - DM can update any NPC or player's initiative to any value as needed.
    - DM can remove any player or NPC from the initiative order.
    - DM commands on players can be referenced by Discord @ mention.
    - DM can change the active turn at will.
    - Commands advance the initiative order, indicating who's turn it currently is and tracks the Escalation Die(13th Age specific).
    - DM can directly change who has the active turn.
    - Initiative database written to disk, recoverable with DM command if there are bot issues.
- Dice Roller(In the format of NdN+N with highlighting of natural max rolls.  No rerolls or dice popping)
- Experimental Dice Roller based on the random.org API.
    - You'll need your own API key from them put into the .env file as RANDOM_ORG_API for this to work.
- Attack dice roller, rolls 1d20 plus supplied player bonus.  Adds escalation dice automatically, and breaks out natural roll value.
- Next Game schedule:
    - Shows when the next game is in several different timezones, and time until the next game.
    - Toggleable next game @mention announcement in the last hour before the game.
- Quote database:
    - Add quotations to the database.
    - Recall random quotations from the database.
    - Search for text and display a random quote with matching text.
