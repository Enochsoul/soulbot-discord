import sqlite3
import random
import time
from datetime import tzinfo, timedelta, datetime


class Zone(tzinfo):
    def __init__(self, offset, isdst, name):
        self.offset = offset
        self.isdst = isdst
        self.name = name

    def utcoffset(self, dt):
        return timedelta(hours=self.offset) + self.dst(dt)

    def dst(self, dt):
        return timedelta(hours=1) if self.isdst else timedelta(0)

    def tzname(self, dt):
        return self.name


daylight_check = bool(time.daylight)
GMT = Zone(0, False, 'GMT')
ET = Zone(-5, daylight_check, 'ET')
CT = Zone(-6, daylight_check, 'CT')
MT = Zone(-7, daylight_check, 'MT')
PT = Zone(-8, daylight_check, 'PT')


class DatabaseIO:
    def __init__(self):
        self.bot_db = sqlite3.connect('data/discordbot.sql',
                                      detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        self.c = self.bot_db.cursor()

    def init_db_add(self, init_insert: list):
        self.c.executemany('''INSERT OR REPLACE INTO initiative(name, init) VALUES(?,?)''', init_insert)
        self.bot_db.commit()

    def init_db_delete(self):
        self.c.execute('''DELETE FROM initiative''')

    def init_db_rebuild(self):
        self.c.execute('''SELECT name, init FROM initiative''')
        all_rows = self.c.fetchall()
        return all_rows

    def quote_db_add(self, quote_insert: str):
        self.c.execute('''INSERT INTO quotes(quote) VALUES(?)''', (quote_insert,))
        self.bot_db.commit()

    def quote_db_search(self, quote_search: str):
        self.c.execute('''SELECT quote FROM quotes where quote LIKE ?''', ("%" + str(quote_search) + "%",))
        quote_text = self.c.fetchall()
        if len(quote_text) > 0:
            random_index = random.randint(0, len(quote_text) - 1)
            return f'QUOTE: "{quote_text[random_index][0]}"'
        else:
            return f'No quote found with the term "{quote_search}"'

    def quote_db_random(self):
        self.c.execute('''SELECT * FROM quotes''')
        count = len(self.c.fetchall())
        if count > 0:
            self.c.execute('''SELECT quote FROM quotes ORDER BY RANDOM() LIMIT 1''')
            quote_text = self.c.fetchone()[0]
            return f'QUOTE: "{quote_text}"'
        else:
            return f"No quotes in the database."

    def next_game_db_get(self):
        self.c.execute('''SELECT next_date FROM next_game where id=?''', (1,))
        return self.c.fetchone()

    def next_game_db_add(self, output_date):
        self.c.execute(
            '''INSERT OR REPLACE INTO next_game(id, created_date, next_date) VALUES(?,?,?)''',
            (1, datetime.today(),
             output_date.replace(tzinfo=None)))
        self.bot_db.commit()


soulbot_db = DatabaseIO()
