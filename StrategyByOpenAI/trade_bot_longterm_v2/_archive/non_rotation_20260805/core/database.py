import sqlite3
import os

os.makedirs("database", exist_ok=True)


class Database:

    def __init__(self):

        self.conn = sqlite3.connect(
            "database/trading.db",
            check_same_thread=False
        )

        self.create_tables()

    def create_tables(self):

        cur = self.conn.cursor()

        cur.execute("""

        CREATE TABLE IF NOT EXISTS trades(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            symbol TEXT,

            entry_time TEXT,

            exit_time TEXT,

            side TEXT,

            quantity INTEGER,

            entry_price REAL,

            exit_price REAL,

            pnl REAL

        )

        """)

        cur.execute("""

        CREATE TABLE IF NOT EXISTS signals(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            symbol TEXT,

            strategy TEXT,

            side TEXT,

            score REAL,

            time TEXT

        )

        """)

        cur.execute("""

        CREATE TABLE IF NOT EXISTS positions(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            symbol TEXT,

            quantity INTEGER,

            entry_price REAL,

            stoploss REAL,

            target REAL,

            active INTEGER

        )

        """)

        self.conn.commit()

    def execute(self, query, params=()):

        cur = self.conn.cursor()

        cur.execute(query, params)

        self.conn.commit()

    def fetchall(self, query, params=()):

        cur = self.conn.cursor()

        cur.execute(query, params)

        return cur.fetchall()

    def close(self):

        self.conn.close()