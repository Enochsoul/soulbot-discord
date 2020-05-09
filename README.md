# botsoul-discord
Simple Discord bot for my 13th Age RPG group.

Still a work in progress, requires a .env file with your discord bot token.  Right now designed to run as a standalone bot for a single server.  If you invite it to multiple servers all settings will be shared.

### Install:
1) git clone to your chosen location
2) create .env with your Discord bot token and default command prefix:

EG:
```  
  #.env
  DISCORD_TOKEN=(put your token here)
  COMMAND_PREFIX=!
```
3) Build environment from the requirements.txt(Virtual or system, your call.)
4) Run the bot script.
5) Create Discord Role called GM or DM, and assign to the user acting as the DM.  No special permissions required.  Access to some commands is restricted to user with this Role name.  
  
### Current Features:
- XP Tracking - I know it's not expressly used for 13th Age, but I wrote it before I realized and just left it in.
- OGL/d20 initiative tracking(As used by 13th Age), should also work for DnD 4e.
    - Players roll initiative and get added to a tracking table.
    - Players can delay their initiative to a set number smaller than their current.
    - DM can create NPCs, add them at any time before or after combat starts.
    - DM can update any NPC or player's initiative to any value as needed.
    - DM can remove any player or NPC from the initiative order.
    - DM commands on players can be referenced by Discord @ mention.
    - Commands advance the initiative order, indicating who's turn it currently is and tracks the Escalation Die(13th Age specific).
- Dice Roller(In the format of NdN+N with highlighting of natural max rolls.  No rerolls or dice popping)
- Attack dice roller, rolls 1d20 plus supplied player bonus.  Adds escalation dice automatically, and breaks out natural roll value.

