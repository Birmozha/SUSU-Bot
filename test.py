import sqlite3

with sqlite3.connect('data.db') as db:
        cur = db.cursor()
        a = cur.execute("""SELECT data.text FROM data, tree WHERE tree.pid IN (13, 15)""").fetchall()
        print(a)