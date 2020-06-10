import time
import os, datetime
import imdb

from flask import Flask, session, request, render_template, redirect
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///database.db"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
def index():
    if session.get("logged_in"):
        curruser = session["username"]
        return render_template("index.html", loginstatus = 'True', curruser = curruser)
    else:
        return render_template("index.html", loginstatus = 'False')
#    i = imdb.IMDb(accessSystem='http')
#    results = i.search_movie('the matrix')
#    return results

@app.route("/register", methods = ['GET', 'POST'])
def register():
    if session.get("logged_in"):
        return "<script>alert('You are already logged in, Log out first'); window.location = 'http://127.0.0.1:5000/';</script>"
    else:
        if request.method == 'POST':
            username = request.form.get("username")
            password = request.form.get("password")
            email = request.form.get("email")
            name = request.form.get("name")
            date = datetime.datetime.utcnow()
            db.execute("INSERT INTO users (username, password, name, join_date) VALUES (:username, :password, :name, :join_date)",
                        {"username": username, "password": password, "name": name, "join_date": date})
            db.execute("INSERT INTO email (mail, username) VALUES (:mail, :username)", {"mail": email, "username": username})
            db.commit()
            session["logged_in"] = True
            session["username"] = username
            return "<script>alert('Registered Successfully');window.location = 'http://127.0.0.1:5000/';</script>"
        else:
            return render_template("register.html")

@app.route("/login", methods = ['GET', 'POST'])
def login():
    if session.get("logged_in"):
        return "<script>alert('You are already logged in'); window.location = 'http://127.0.0.1:5000/';</script>"
    else:
        if request.method == 'POST':
            username = request.form.get("username")
            password = request.form.get("password")
            data = db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).fetchall()
            if len(data) > 0:
                if data[0].password == password:
                    session["logged_in"] = True
                    session["username"] = username
                    return "<script>alert('Login Successful');window.location = 'http://127.0.0.1:5000/';</script>"
                else:
                    return "<script>alert('Invalid password');window.location = 'http://127.0.0.1:5000/login';</script>"
            else:
                return "<script>alert('Please register first');window.location = 'http://127.0.0.1:5000/register';</script>"
        else:
            return render_template("login.html")

@app.route("/logout", methods = ['GET', 'POST'])
def logout():
    print(session.keys())
    session.clear()
    print(session.keys())
    return redirect("http://127.0.0.1:5000")
