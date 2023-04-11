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
@app.route('/index')
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
            level_id = cur.execute("""WITH RECURSIVE
                            cte(qid, level) AS (
                                VALUES((?), 0)
                                UNION ALL
                                SELECT tree.qid, cte.level+1
                                FROM tree JOIN cte ON tree.pid = cte.qid
                                ORDER BY 2 DESC)
                                SELECT level, qid FROM cte""", (null[0], )).fetchall()
            
            level_id = [el for el in level_id]
            tree = []
            for el in level_id:
                temp = cur.execute("""SELECT data.text, tree.properties FROM data, tree WHERE data.qid is (?) AND tree.qid IS (?)""", (el[1], el[1])).fetchone()
                temp = (temp[0], tuple(temp[1].split(', ')))
                tree.append((el[0]+1, temp[0], el[1], temp[1])) # (УРОВЕНЬ, ТЕКСТ, НОМЕР, СВОЙСТВА)
    return render_template('tree.html', tree=tree)

@app.route('/tree/<int:id>/change', methods=['POST', 'GET'])
def changeLeaf(id):
    with sqlite3.connect('data.db') as db:
        cur = db.cursor()
        properties = list(map(lambda x: x[0].split(', ')[1], set(cur.execute("""SELECT properties FROM tree WHERE properties LIKE '<text%' """).fetchall())))
        current_property = (cur.execute("""SELECT properties FROM tree WHERE qid IS (?) """, (id, )).fetchone()[0]).split(', ')
        if len(current_property) == 2:
            current_property = current_property[1]
            del properties[properties.index(current_property)]
        properties.insert(0, current_property)
        data = cur.execute("""SELECT text FROM data WHERE qid IS (?)""", (id, )).fetchone()
        
    if request.method == "POST":
        text = request.form['text']
        property = None
        try:
            if request.form['button-type']:
                property = '<text>, ' + request.form['button-type']
        except KeyError:
            pass
        
        with sqlite3.connect('data.db') as db:
            cur = db.cursor()
            cur.execute("""UPDATE data
                            SET  (text)
                            = ((?))
                            WHERE QID is (?) ;
                            """, (text, id))
            if property:
                cur.execute("""UPDATE tree
                                SET  (properties)
                                = ((?))
                                WHERE QID is (?) ;
                                """, (property, id))
            
        return redirect('/tree')
    
    return render_template('changeLeaf.html', data=data, properties=properties)



if __name__ == '__main__':
    app.run(debug=True)
    