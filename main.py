import sqlite3
import os

from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, request
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')


login_manager = LoginManager()
login_manager.init_app(app)

users = {'a1': {'password': 'pass1'},
         'a2': {'password': 'pass2'}}

class User(UserMixin):
    pass

@login_manager.user_loader
def userLoader(username):
    if username not in users:
        return
    user = User()
    user.id = username
    return user




@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and password == users[username]['password']:
            user = User()
            user.id = username
            login_user(user)
            return redirect('/index')
        return 'Invalid'
    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    return render_template('login.html')


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/tree')
@login_required
def tree():
    tree = []
    with sqlite3.connect('data.db') as db:
        cur = db.cursor()
        nulls = cur.execute("""SELECT qid FROM tree WHERE pid IS null""").fetchall()
        for null in nulls:
            cur.execute("""WITH RECURSIVE
                        cte(qid, level) AS (
                            VALUES((?), 0)
                            UNION ALL
                            SELECT tree.qid, cte.level+1
                            FROM tree JOIN cte ON tree.pid = cte.qid
                            ORDER BY 2 DESC)
                        SELECT level || ' ' || qid FROM cte""", (null[0], ))
            a = cur.fetchall()
            for el in a:
                el = str(el[0])
                el = el.split()
                el = (int(el[0]), int(el[1]))
                tree.append(el)
            newTree = []
            for el in tree:
                temp = cur.execute("""SELECT text FROM data WHERE qid IS (?)""", (str(el[1]), )).fetchone()
                newTemp = cur.execute("""SELECT properties FROM tree WHERE qid is (?)""", (str(el[1]), )).fetchone()
                new = (el[0]+1, temp[0], el[1], newTemp[0])
                newTree.append(new)
            
    return render_template('tree.html', a=newTree, maxlevel=max(newTree)[0])

@app.route('/tree/<int:id>/change', methods=['POST', 'GET'])
def changeLeaf(id):
    with sqlite3.connect('data.db') as db:
        cur = db.cursor()
        text = cur.execute("""SELECT text FROM data WHERE qid IS (?)""", (id, )).fetchone()
        
    if request.method == "POST":
        question = request.form['question']
        answer = request.form['answer']
        photo = request.form['photo']
        if len(photo) == 0:
            photo = None
        with sqlite3.connect('data.db') as db:
            cur = db.cursor()
            cur.execute("""
                               UPDATE questions
                        SET  (question, answer, photo)
                        = ((?), (?), (?))
                        WHERE QID is (?) ;
                        """, (question, answer, photo, id))
        return redirect('/tree')
    
    return render_template('changeLeaf.html', text=text)



if __name__ == '__main__':
    app.run(debug=True)
    