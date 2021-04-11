"""Module containing support command for the main bot."""
import sqlite3
import random
import arrow

MT = arrow.now('US/Mountain').tzinfo
PT = arrow.now('US/Pacific').tzinfo
CT = arrow.now('US/Central').tzinfo
ET = arrow.now('US/Eastern').tzinfo
UTC = arrow.utcnow().tzinfo


class DatabaseIO:
    """Class definition to contain all interactions with the SQLite3 database."""

    def __init__(self):
        self.bot_db = sqlite3.connect('data/discordbot.sql',
                                      detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        self.c = self.bot_db.cursor()
        self.c.execute('''CREATE TABLE IF NOT EXISTS next_game
                      (guild_id INTEGER UNIQUE, created_date INTEGER, next_date INTEGER, 
                      announce_on INTEGER DEFAULT 0)''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS quotes
                      (id INTEGER PRIMARY KEY, guild_id INTEGER, quote TEXT)''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS initiative
                      (guild_id INTEGER, name TEXT, init INTEGER)''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS config
                      (guild_id INTEGER UNIQUE PRIMARY KEY, prefix TEXT, 
                      next_game_start TEXT, next_game_interval INTEGER, announce_channel TEXT)''')

    def init_db_add(self, init_insert: list):
        """Insert/overwrite Initiative tracker data into the database.

        :param init_insert: List of tuples containing player/NPC initiative values.
        """
        self.c.executemany('''INSERT INTO initiative(guild_id, name, init) VALUES(?,?,?)''', init_insert)

    def init_db_reset(self, guild_id: int):
        """Delete initiative table data."""
        self.c.execute('''DELETE FROM initiative where guild_id=?''', (guild_id,))

    def init_db_rebuild(self, guild_id: int):
        """Retrieve initiative table from the database to rebuild the bot data.

        :return: List of tuples of all player/NPC names and initiative values."""
        self.c.execute('''SELECT name, init FROM initiative WHERE guild_id=?''', (guild_id,))
        all_rows = self.c.fetchall()
        return all_rows

    def init_db_commit(self):
        """Commits changes to the database.  Allows commits to be more selective from the commands.
        """
        self.bot_db.commit()

    def quote_db_add(self, quote_insert: str, guild_id: int):
        """Add new quote to the SQL database.

        :param quote_insert: Text to add to database.
        """
        self.c.execute('''INSERT INTO quotes(guild_id, quote) VALUES(?,?)''', (guild_id, quote_insert))
        self.bot_db.commit()

    def quote_db_search(self, quote_search: str, guild_id: int):
        """Search SQL database for entries containing text string.

        :param quote_search: Text to search for in existing quotes.
        :return: Return random quote, or failure message.
        """
        self.c.execute('''SELECT quote FROM quotes where quote LIKE ? AND guild_id=?''',
                       ("%" + str(quote_search) + "%", guild_id))
        quote_text = self.c.fetchall()
        if len(quote_text) > 0:
            random_index = random.randint(0, len(quote_text) - 1)
            return f'QUOTE: "{quote_text[random_index][0]}"'
        else:
            return f'No quote found with the term "{quote_search}"'

    def quote_db_random(self, guild_id: int):
        """Pull random line from the database.

        :return: Text from randomly selected database entry.
        """
        self.c.execute('''SELECT * FROM quotes where guild_id=?''', (guild_id,))
        count = len(self.c.fetchall())
        if count > 0:
            self.c.execute('''SELECT id, quote FROM quotes where guild_id=? ORDER BY RANDOM() LIMIT 1''', (guild_id,))
            quote_text = self.c.fetchone()[1]
            return f'QUOTE: "{quote_text}"'
        else:
            return f"No quotes in the database."

    def next_game_db_get(self, guild_id):
        """Pulls Next Game date from the database."""
        self.c.execute('''SELECT next_date, announce_on FROM next_game where guild_id=?''', (guild_id,))
        return self.c.fetchone()

    def next_game_db_add(self, output_date, guild_id: int):
        """Replaces current next game data with supplied new date.

        :param output_date: Formatted date string.
        :param guild_id: Discord guild ID"""
        self.c.execute(
            '''INSERT OR REPLACE INTO next_game(guild_id, created_date, next_date) VALUES(?,?,?)''',
            (guild_id, arrow.now(UTC).timestamp,
             output_date))
        self.bot_db.commit()

    def next_game_announce_toggle(self, state: int, guild_id: int):
        """Toggles the announce_on for the given guild ID.

        :param state: 0 or 1 integers
        :param guild_id: Discord guild ID
        """
        self.c.execute('''UPDATE next_game SET announce_on=? where guild_id=?''', (state, guild_id,))
        self.bot_db.commit()

    def next_game_get_defaults(self, guild_id: int):
        """Gets the default next game start time and interval from the config database.

        :param guild_id: Discord guild ID.
        """
        self.c.execute('''SELECT next_game_start, next_game_interval FROM config where guild_id=?''', (guild_id,))
        return self.c.fetchone()

    def next_game_get_all_announcing(self):
        self.c.execute('''SELECT guild_id, next_date from next_game WHERE announce_on = 1''')
        return self.c.fetchall()

    def next_game_table_reset(self):
        """Deletes and recreates the Next Game table.
        Required after redesign to use Arrow module due to database column datatype change."""
        self.c.execute('''DROP TABLE next_game''')
        self.bot_db.commit()
        self.c.execute('''CREATE TABLE IF NOT EXISTS next_game
                      (id INTEGER PRIMARY KEY, created_date INTEGER, next_date INTEGER)''')
        self.bot_db.commit()

    def config_all_prefix_load(self):
        """Loads config settings for all registered guilds."""
        self.c.execute('''SELECT guild_id, prefix FROM config''')
        configs = self.c.fetchall()
        return {k: v for k, v in configs}

    def config_insert_all(self, guild_id: int, prefix: str, default_time: str, default_interval: int,
                          announce_channel: str):
        """Creates DB row for new server with values."""
        self.c.execute('''INSERT INTO config(guild_id, prefix, next_game_start, next_game_interval, announce_channel) 
        VALUES(?,?,?,?,?)''', (guild_id, prefix, default_time, default_interval, announce_channel))
        self.bot_db.commit()

    def config_prefix_update(self, guild_id: int, prefix: str):
        """Adds or updates a guild's configured prefix."""
        self.c.execute('''UPDATE config SET prefix=? WHERE guild_id=?''', (prefix, guild_id,))
        self.bot_db.commit()

    def config_next_game_default_time_update(self, guild_id: int, default_time: int):
        """Adds or updates a guild's configured Next Game time."""
        self.c.execute('''UPDATE config SET next_game_start=? WHERE guild_id=?''',
                       (default_time, guild_id, ))
        self.bot_db.commit()

    def config_next_game_default_interval_update(self, guild_id: int, default_interval: int):
        """Adds or updates a guild's configured default Next Game Interval."""
        self.c.execute('''UPDATE config SET next_game_interval=? WHERE guild_id=?''',
                       (default_interval, guild_id, ))
        self.bot_db.commit()

    def config_next_game_announce_channel(self, guild_id: int, announce_channel: str):
        """Update's a server's configured channel for next game announcements."""
        self.c.execute('''UPDATE config SET announce_channel=? WHERE guild_id=?''', (announce_channel, guild_id, ))
        self.bot_db.commit()

    def guild_remove_all(self, guild_id: int):
        """Function called when bot is removed from guild, cleans up all DB references."""
        self.c.execute('''DELETE from config where guild_id=?''', (guild_id,))
        self.c.execute('''DELETE from next_game where guild_id=?''', (guild_id,))
        self.c.execute('''DELETE from quotes where guild_id=?''', (guild_id,))
        self.c.execute('''DELETE from initiative where guild_id=?''', (guild_id,))
        self.bot_db.commit()


soulbot_db = DatabaseIO()
