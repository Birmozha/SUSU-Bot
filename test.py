import sqlite3

tree = []
with sqlite3.connect('data.db') as db:
        cur = db.cursor()
        a = cur.execute("""SELECT qid FROM tree WHERE properties IS '<text>' """).fetchall()
        print(a)