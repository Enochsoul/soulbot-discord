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
                      (id INTEGER PRIMARY KEY, guild_id INTEGER, created_date INTEGER, next_date INTEGER)''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS quotes
                      (id INTEGER PRIMARY KEY, guild_id INTEGER, quote TEXT)''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS initiative
                      (guild_id INTEGER, name TEXT, init INTEGER)''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS config
                      (guild_id INTEGER UNIQUE PRIMARY KEY, prefix TEXT)''')

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
        self.c.execute('''SELECT quote FROM quotes where quote LIKE ? AND guild_id=?''', ("%" + str(quote_search) + "%", guild_id))
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
            self.c.execute('''SELECT quote FROM quotes where guild_id=? ORDER BY RANDOM() LIMIT 1''', (guild_id,))
            quote_text = self.c.fetchone()[0]
            return f'QUOTE: "{quote_text}"'
        else:
            return f"No quotes in the database."

    def next_game_db_get(self, guild_id):
        """Pulls Next Game date from the database."""
        self.c.execute('''SELECT next_date FROM next_game where id=? and guild_id=?''', (1,guild_id))
        return self.c.fetchone()

    def next_game_db_add(self, output_date, guild_id: int):
        """Replaces current next game data with supplied new date.

        :param output_date: Formatted date string."""
        self.c.execute(
            '''INSERT OR REPLACE INTO next_game(id, guild_id, created_date, next_date) VALUES(?,?,?,?)''',
            (1, guild_id, arrow.now(UTC).timestamp,
             output_date))
        self.bot_db.commit()

    def next_game_table_reset(self):
        """Deletes and recreates the Next Game table.
        Required after redesign to use Arrow module due to database column datatype change."""
        self.c.execute('''DROP TABLE next_game''')
        self.bot_db.commit()
        self.c.execute('''CREATE TABLE IF NOT EXISTS next_game
                      (id INTEGER PRIMARY KEY, created_date INTEGER, next_date INTEGER)''')
        self.bot_db.commit()

    def config_load(self):
        """Loads config settings for all registered guilds."""
        self.c.execute('''SELECT * FROM config''')
        configs = self.c.fetchall()
        return {k:v for k,v in configs}

    def config_insert(self, guild_id: int, prefix: str):
        """Adds or updates a guild's configured prefix."""
        self.c.execute('''INSERT or REPLACE INTO config(guild_id, prefix) VALUES(?,?)''', (guild_id, prefix))
        self.bot_db.commit()


soulbot_db = DatabaseIO()
