"""Module containing support command for the main bot."""
import sqlite3
import random
import time
from datetime import tzinfo, timedelta, datetime


class Zone(tzinfo):
    """Class to redefine timezones."""
    def __init__(self, offset, isdst, name):
        self.offset = offset
        self.isdst = isdst
        self.name = name

    daylight_check = bool(time.daylight)

    def utcoffset(self, dt):
        return timedelta(hours=self.offset) + self.dst(dt)

    def dst(self, dt):
        return timedelta(hours=1) if self.isdst else timedelta(0)

    def tzname(self, dt):
        return self.name


GMT = Zone(0, False, 'GMT')
ET = Zone(-5, Zone.daylight_check, 'ET')
CT = Zone(-6, Zone.daylight_check, 'CT')
MT = Zone(-7, Zone.daylight_check, 'MT')
PT = Zone(-8, Zone.daylight_check, 'PT')


class DatabaseIO:
    """Class definition to contain all interactions with the SQLite3 database."""
    def __init__(self):
        self.bot_db = sqlite3.connect('data/discordbot.sql',
                                      detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        self.c = self.bot_db.cursor()

    def init_db_add(self, init_insert: list):
        """Insert/overwrite Initiative tracker data into the database.

        :param init_insert: List of tuples containing player/NPC initiative values.
        """
        self.c.executemany('''INSERT OR REPLACE INTO initiative(name, init) VALUES(?,?)''', init_insert)
        self.bot_db.commit()

    def init_db_reset(self):
        """Delete initiative table data."""
        self.c.execute('''DELETE FROM initiative''')

    def init_db_rebuild(self):
        """Retrieve initiative table from the database to rebuild the bot data.

        :return: List of tuples of aoo player/NPC names and initiative values."""
        self.c.execute('''SELECT name, init FROM initiative''')
        all_rows = self.c.fetchall()
        return all_rows

    def quote_db_add(self, quote_insert: str):
        """Add new quote to the SQL database.

        :param quote_insert: Text to add to database.
        """
        self.c.execute('''INSERT INTO quotes(quote) VALUES(?)''', (quote_insert,))
        self.bot_db.commit()

    def quote_db_search(self, quote_search: str):
        """Search SQL database for entries containing text string.

        :param quote_search: Text to search for in existing quotes.
        :return: Return random quote, or failure message.
        """
        self.c.execute('''SELECT quote FROM quotes where quote LIKE ?''', ("%" + str(quote_search) + "%",))
        quote_text = self.c.fetchall()
        if len(quote_text) > 0:
            random_index = random.randint(0, len(quote_text) - 1)
            return f'QUOTE: "{quote_text[random_index][0]}"'
        else:
            return f'No quote found with the term "{quote_search}"'

    def quote_db_random(self):
        """Pull random line from the database.

        :return: Text from randomly selected database entry.
        """
        self.c.execute('''SELECT * FROM quotes''')
        count = len(self.c.fetchall())
        if count > 0:
            self.c.execute('''SELECT quote FROM quotes ORDER BY RANDOM() LIMIT 1''')
            quote_text = self.c.fetchone()[0]
            return f'QUOTE: "{quote_text}"'
        else:
            return f"No quotes in the database."

    def next_game_db_get(self):
        """Pulls Next Game date from the database."""
        self.c.execute('''SELECT next_date FROM next_game where id=?''', (1,))
        return self.c.fetchone()

    def next_game_db_add(self, output_date):
        """Replaces current next game data with supplied new date.

        :param output_date: Formatted date string."""
        self.c.execute(
            '''INSERT OR REPLACE INTO next_game(id, created_date, next_date) VALUES(?,?,?)''',
            (1, datetime.today(),
             output_date.replace(tzinfo=None)))
        self.bot_db.commit()


soulbot_db = DatabaseIO()
