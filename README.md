# botsoul-discord
Simple Discord bot for my RPG group.

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
5) Create Discord Role called GM or DM, and assign to the user acting as the DM.  No special permissions required.  
  
### Current Features:
- XP Tracking
- 13th Age style initiative tracking, should also work for DnD 4e.
    - Players can delay their initiative to a set number smaller than their current.
    - DM can create NPCs, add them at any time before or after combat starts.
    - DM can update any NPC or player's initiative to any value as needed.
    - DM can remove any player or NPC from the initiative order.
    - DM commands on players can be referenced by Discord @ mention.
- Dice Roller(In the format of NdN+N with highlighting of natural max rolls.  No rerolls or dice popping)

