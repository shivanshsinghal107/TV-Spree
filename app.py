import time
import os, datetime
import imdb

from flask import Flask, session, request, render_template, redirect
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

ia = imdb.IMDb()

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

@app.route("/search", methods = ['GET', 'POST'])
def search():
    if request.method == 'POST':
        title = request.form.get("search")
        movies = []
        query = 'SELECT * FROM movies WHERE ' + 'title LIKE \'%'+title+'%\''
        data = db.execute(query).fetchall()
        if len(data) <= 0:
            access = 'imdb'
            res = ia.search_movie(title)
            print(len(res))
            movie = ia.get_movie(res[0].movieID)
            movies.append(movie)
        else:
            access = 'local'
            for d in data:
                movies.append(d)
        if session.get("logged_in"):
            return render_template("search.html", movies = movies, loginstatus = 'True', curruser = session["username"],
                                    access = access)
        else:
            return render_template("search.html", movies = movies, loginstatus = 'False', access = access)
    else:
        return "<script>alert('Please enter the search query');window.location = 'http://127.0.0.1:5000/';</script>"

@app.route("/watched/<username>", methods = ['GET'])
def watched(username):
    if session.get("logged_in"):
        username = session["username"]
        watchedMovies = db.execute("SELECT * FROM mwatched WHERE username = :username", {"username": username}).fetchall()
        movies = []
        for m in watchedMovies:
            id = m.wid
            data = db.execute("SELECT * FROM movies WHERE id = :id", {"id": id}).fetchall()[0]
            movies.append(data)
        return render_template("watched.html", curruser = username, movies = movies)
    else:
        return "<script>alert('Please Login first'); window.location = 'http://127.0.0.1:5000/login';</script>"

@app.route("/addWatched/<id>", methods = ['GET', 'POST'])
def addWatched(id):
    if session.get("logged_in"):
        data = db.execute("SELECT * FROM movies WHERE id = :id", {"id": id}).fetchall()
        if len(data) <= 0:
            m = ia.get_movie(id)
            genres = ""
            for g in m['genres']:
                genres += g + ", "
            genres = genres[:-2]
            cast = ""
            for c in m['cast'][:5]:
                cast += c['name'] + f"({c.currentRole}), "
            cast = cast[:-2]
            db.execute("INSERT INTO movies (id, title, release_date, rating, cast, genres, duration, summary, cover_url) VALUES (:id, :title, :release_date, :rating, :cast, :genres, :duration, :summary, :cover_url)", {"id": id, "title": m['title'], "release_date": m['original air date'][:11], "rating": m['rating'], "cast": cast, "genres": genres, "duration": m['runtimes'][0], "summary": m['plot outline'], "cover_url": m['full-size cover url']})
            db.commit()
            print(f"{m['title']} inserted")
        db.execute("INSERT INTO mwatched (wid, username) VALUES (:wid, :username)", {"wid": id, "username": session["username"]})
        db.commit()
        return "<script>alert('Added to Watched list'); window.location = 'http://127.0.0.1:5000/';</script>"
    else:
        return "<script>alert('Please Login first'); window.location = 'http://127.0.0.1:5000/login';</script>"
