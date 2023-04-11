import sqlite3

with sqlite3.connect('data.db') as db:
    cur = db.cursor()
    a = cur.execute(
        """SELECT * FROM TREE WHERE properties LIKE '<button%' """
    ).fetchall()
    print(a)