import sqlite3

with sqlite3.connect('data.db') as db:
        cur = db.cursor()
        a = cur.execute("""SELECT qid FROM tree WHERE properties IS '<text>' """).fetchall()
        print(a)