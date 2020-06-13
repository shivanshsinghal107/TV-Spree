import imdb
import os, datetime

from flask import Flask, session, request, render_template, redirect
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# imdb access
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
            db.close()
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
                    db.close()
                    return "<script>alert('Login Successful');window.location = 'http://127.0.0.1:5000/';</script>"
                else:
                    db.close()
                    return "<script>alert('Invalid password');window.location = 'http://127.0.0.1:5000/login';</script>"
            else:
                db.close()
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
        if title:
            search = f"%{title}%"
            movies = []
            data = db.execute("SELECT * FROM movies WHERE title LIKE :title", {"title": search}).fetchall()
            if len(data) <= 0:
                access = 'imdb'
                res = ia.search_movie(title)
                #for r in res:
                #    if r['title'].startswith(title.title()):
                movie = ia.get_movie(res[0].movieID)
                if 'series' in movie['kind']:
                    ia.update(movie, 'episodes')
                    movies.append(movie)
                print(len(res), res[0]['kind'])
            else:
                access = 'local'
                for d in data:
                    movies.append(d)
            db.close()
            if session.get("logged_in"):
                return render_template("search.html", movies = movies, loginstatus = 'True', curruser = session["username"],
                                        access = access)
            else:
                return render_template("search.html", movies = movies, loginstatus = 'False', access = access)
        else:
            return "<script>alert('Please enter the query in the search box');window.location = 'http://127.0.0.1:5000/';</script>"
    else:
        return "<script>alert('Please enter the search query');window.location = 'http://127.0.0.1:5000/';</script>"

@app.route("/watched/<username>", methods = ['GET'])
def watched(username):
    if session.get("logged_in"):
        username = session["username"]
        watchedMovies = db.execute("SELECT * FROM mwatched WHERE username = :username", {"username": username}).fetchall()
        watchedSeries = db.execute("SELECT * FROM swatched WHERE username = :username", {"username": username}).fetchall()
        movies = []
        ratings = []
        for m in watchedMovies:
            id = m.wid
            data = db.execute("SELECT * FROM movies WHERE id = :id", {"id": id}).fetchall()
            if len(data) > 0:
                movies.append(data[0])
                ratings.append(m.user_rating)
            else:
                break
        for s in watchedSeries:
            id = s.wid
            data = db.execute("SELECT * FROM series WHERE id = :id", {"id": id}).fetchall()
            if len(data) > 0:
                movies.append(data[0])
                ratings.append(m.user_rating)
            else:
                break
        db.close()
        return render_template("watched.html", curruser = username, movies = movies, ratings = ratings)
    else:
        return "<script>alert('Please Login first'); window.location = 'http://127.0.0.1:5000/login';</script>"

@app.route("/addWatched/<id>", methods = ['GET', 'POST'])
def addWatched(id):
    if session.get("logged_in"):
        user_rating = request.form.get("user_rating")
        mdata = db.execute("SELECT * FROM movies WHERE id = :id", {"id": id}).fetchall()
        sdata = db.execute("SELECT * FROM series WHERE id = :id", {"id": id}).fetchall()
        if len(mdata) <= 0 & len(sdata) <= 0:
            m = ia.get_movie(id)
            plot = ""
            if 'plot outline' in m.keys():
                plot = m['plot outline']
            genres = ""
            for g in m['genres']:
                genres += g + ", "
            genres = genres[:-2]
            cast = ""
            cast_url = ""
            for c in m['cast'][:5]:
                cast += c['name'] + f"({c.currentRole}), "
                p = ia.get_person(c.personID)
                if 'full-size headshot' in p.keys():
                    cast_url += p['full-size headshot'] + ", "
            cast = cast[:-2]
            cast_url = cast_url[:-2]
            if 'movie' in m['kind']:
                db.execute("INSERT INTO movies (id, kind, title, release, rating, cast, cast_url, genres, duration, summary, cover_url) VALUES (:id, :kind, :title, :release, :rating, :cast, :cast_url, :genres, :duration, :summary, :cover_url)", {"id": id, "kind": m['kind'], "title": m['title'], "release": m['original air date'][:11], "rating": m['rating'], "cast": cast, "cast_url": cast_url, "genres": genres, "duration": m['runtimes'][0], "summary": plot, "cover_url": m['full-size cover url']})
                db.commit()
                print(f"{m['title']} inserted")
                data = db.execute("SELECT * FROM mwatched WHERE wid = :wid", {"wid": id}).fetchall()
                if len(data) <= 0:
                    db.execute("INSERT INTO mwatched (wid, user_rating, username) VALUES (:wid, :user_rating, :username)",
                    {"wid": id, "user_rating": user_rating, "username": session["username"]})
                    db.commit()
                    db.close()
                    return "<script>alert('Added to Watched list'); window.location = 'http://127.0.0.1:5000/';</script>"
                else:
                    db.close()
                    return "<script>alert('You already watched this'); window.location = 'http://127.0.0.1:5000/'</script>"
            elif 'series' in m['kind']:
                ia.update(m, 'episodes')
                db.execute("INSERT INTO series (id, kind, title, release, rating, cast, cast_url, seasons, episodes, genres, duration, summary, cover_url) VALUES (:id, :kind, :title, :release, :rating, :cast, :cast_url, :seasons, :episodes, :genres, :duration, :summary, :cover_url)", {"id": id, "kind": m['kind'], "title": m['title'], "release": m['series years'], "rating": m['rating'], "cast": cast, "cast_url": cast_url, "seasons": m['number of seasons'], "episodes": m['number of episodes'], "genres": genres, "duration": m['runtimes'][0], "summary": plot, "cover_url": m['full-size cover url']})
                db.commit()
                print(f"{m['title']} inserted")
                data = db.execute("SELECT * FROM swatched WHERE wid = :wid", {"wid": id}).fetchall()
                if len(data) <= 0:
                    db.execute("INSERT INTO swatched (wid, user_rating, username) VALUES (:wid, :user_rating, :username)",
                    {"wid": id, "user_rating": user_rating, "username": session["username"]})
                    db.commit()
                    db.close()
                    return "<script>alert('Added to Watched list'); window.location = 'http://127.0.0.1:5000/';</script>"
                else:
                    db.close()
                    return "<script>alert('You already watched this'); window.location = 'http://127.0.0.1:5000/'</script>"
        else:
            if len(mdata) > 0:
                data = db.execute("SELECT * FROM mwatched WHERE wid = :wid", {"wid": id}).fetchall()
                if len(data) <= 0:
                    db.execute("INSERT INTO mwatched (wid, user_rating, username) VALUES (:wid, :user_rating, :username)",
                    {"wid": id, "user_rating": user_rating, "username": session["username"]})
                    db.commit()
                    db.close()
                    return "<script>alert('Added to Watched list'); window.location = 'http://127.0.0.1:5000/';</script>"
                else:
                    db.close()
                    return "<script>alert('You already watched this'); window.location = 'http://127.0.0.1:5000/'</script>"
            if len(sdata) > 0:
                data = db.execute("SELECT * FROM swatched WHERE wid = :wid", {"wid": id}).fetchall()
                if len(data) <= 0:
                    db.execute("INSERT INTO swatched (wid, user_rating, username) VALUES (:wid, :user_rating, :username)",
                    {"wid": id, "user_rating": user_rating, "username": session["username"]})
                    db.commit()
                    db.close()
                    return "<script>alert('Added to Watched list'); window.location = 'http://127.0.0.1:5000/';</script>"
                else:
                    db.close()
                    return "<script>alert('You already watched this'); window.location = 'http://127.0.0.1:5000/'</script>"
    else:
        return "<script>alert('Please Login first'); window.location = 'http://127.0.0.1:5000/login';</script>"

@app.route("/removeWatched/<id>", methods = ['GET', 'POST'])
def removeWatched(id):
    if session.get("logged_in"):
        if len(db.execute("SELECT * FROM mwatched WHERE wid = :wid", {"wid": id}).fetchall()) > 0:
            db.execute("DELETE FROM mwatched WHERE wid = :wid", {"wid": id})
            db.commit()
        else:
            db.execute("DELETE FROM swatched WHERE wid = :wid", {"wid": id})
            db.commit()
        db.close()
        print("deleted")
        username = session["username"]
        return redirect(f"http://127.0.0.1:5000/watched/{username}")
    else:
        return "<script>alert('Please Login first'); window.location = 'http://127.0.0.1:5000/login';</script>"

@app.route("/<id>/description", methods = ['GET', 'POST'])
def description(id):
    access = request.args.get("access")
    movie_object = request.args.get("movie_object")
    movie = eval(movie_object)
    if access == 'imdb':
        plot = ""
        if 'plot outline' in movie.keys():
            plot = movie['plot outline']
        genres = ""
        for g in movie['genres']:
            genres += g + ", "
        genres = genres[:-2]
        cast = ""
        cast_url = ""
        for i in range(0, len(movie['cast'])):
            p = ia.get_person(movie['cast'][i])
            cast += p['name'] + f"({movie['roles'][i]}), "
            if 'full-size headshot' in p.keys():
                cast_url += p['full-size headshot'] + ", "
        movie['cast'] = cast[:-2]
        movie['cast_url'] = cast_url[:-2]
    return render_template("description.html", movie = movie, access = access)
