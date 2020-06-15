import imdb
import ast
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
            date = datetime.datetime.utcnow()
            db.execute("INSERT INTO users (username, password, join_date) VALUES (:username, :password, :join_date)",
                        {"username": username, "password": password, "join_date": date})
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
            query = title.replace(" ", "+")
            return redirect(f"http://127.0.0.1:5000/results/{query}")
        else:
            return "<script>alert('Please enter the query in the search box');window.location = 'http://127.0.0.1:5000/';</script>"
    else:
        return "<script>alert('Method not allowed');window.location = 'http://127.0.0.1:5000/';</script>"

@app.route("/results/<query>", methods = ['GET', 'POST'])
def result(query):
    title = query.replace("+", " ")
    search = f"%{title}%"
    movies = []
    access = []
    data = db.execute("SELECT * FROM movies WHERE title LIKE :title", {"title": search}).fetchall()
    res = ia.search_movie(title)
    if len(data) > 0:
        in_ids = []
        for d in data:
            movies.append(d)
            access.append('local')
            in_ids.append(int(d.id))
            print("ddone")
        print(in_ids)
        out_ids = []
        for r in res:
            if (title.lower() in r['title'].lower()) & (r['kind'] == res[0]['kind']):
                out_ids.append(int(r.movieID))
        print(out_ids)
        ids = list(set(out_ids).difference(in_ids))
        print(ids)
        for id in ids:
            movie = ia.get_movie(id)
            movies.append(movie)
            access.append('imdb')
            print("done")
    elif 'series' in res[0]['kind']:
        data = db.execute("SELECT * FROM series WHERE title LIKE :title", {"title": search}).fetchall()
        if len(data) > 0:
            print("series in database")
            movies.append(data[0])
            access.append('local')
        else:
            print("series not in database")
            movie = ia.get_movie(res[0].movieID)
            ia.update(movie, 'episodes')
            movies.append(movie)
            access.append('imdb')
    else:
        print("movie not in database")
        for r in res:
            if (title.lower() in r['title'].lower()) & (r['kind'] == res[0]['kind']):
                movie = ia.get_movie(r.movieID)
                movies.append(movie)
                access.append('imdb')
                print("done")
    if len(movies) == 0 & len(res) > 0:
        movie = ia.get_movie(res[0].movieID)
        movies.append(movie)
    print(len(movies), res[0]['kind'])
    if len(movies) == 0:
        db.close()
        return "<script>alert('No results found');window.location = 'http://127.0.0.1:5000/';</script>"
    #if 'movie' in res[0]['kind']:
    #    # getting one series for a movie like case of 'Warrior'
    #    for r in res:
    #        if r['title'].startswith(title.title()) & ('series' in r['kind']):
    #            movie = ia.get_movie(r.movieID)
    #            ia.update(movie, 'episodes')
    #            movies.append(movie)
    #            access.append('imdb')
    #            print("done")
    #            break
    db.close()
    if session.get("logged_in"):
        return render_template("search.html", movies = movies, loginstatus = 'True', curruser = session["username"],
                                access = access)
    else:
        return render_template("search.html", movies = movies, loginstatus = 'False', access = access)

@app.route("/watched/<username>", methods = ['GET'])
def watched(username):
    if session.get("logged_in"):
        username = session["username"]
        watched = db.execute("SELECT * FROM watched WHERE username = :username ORDER BY date DESC", {"username": username}).fetchall()
        movies = []
        ratings = []
        for w in watched:
            id = w.wid
            mdata = db.execute("SELECT * FROM movies WHERE id = :id", {"id": id}).fetchall()
            sdata = db.execute("SELECT * FROM series WHERE id = :id", {"id": id}).fetchall()
            if len(mdata) > 0:
                movies.append(mdata[0])
                ratings.append(w.user_rating)
            elif len(sdata) > 0:
                movies.append(sdata[0])
                ratings.append(w.user_rating)
            else:
                break
        db.close()
        return render_template("watched.html", curruser = username, movies = movies, ratings = ratings)
    else:
        return "<script>alert('Please Login first'); window.location = 'http://127.0.0.1:5000/login';</script>"

@app.route("/addWatched/<id>", methods = ['GET', 'POST'])
def addWatched(id):
    if session.get("logged_in"):
        access = request.args.get("access")
        movie_object = request.args.get("movie_object")
        print(type(movie_object))
        print(movie_object)
        m = ast.literal_eval(movie_object)
        print(type(m))
        print(m)
        user_rating = request.form.get("user_rating")
        date = str(datetime.datetime.utcnow())
        data = db.execute("SELECT * FROM movies WHERE id = :id", {"id": id}).fetchall()
        if len(data) <= 0:
            data = db.execute("SELECT * FROM series WHERE id = :id", {"id": id}).fetchall()
        print(len(data))
        if len(data) <= 0:
            genres = ""
            for g in m['genres']:
                genres += g + ", "
            genres = genres[:-2]
            cast_id = ""
            for id in m['cast_id']:
                cast_id += id + ", "
            cast_id = cast_id[:-2]
            if access == 'imdb':
                cast = ""
                #cast_url = ""
                for i in range(0, len(m['cast'])):
                    cast += m['cast'][i] + f"({m['roles'][i]}), "
                cast = cast[:-2]
            else:
                cast = m['cast']
            if 'movie' in m['kind']:
                db.execute("INSERT INTO movies (id, kind, title, release, rating, cast, cast_id, genres, duration, budget, worldwide_gross, summary, cover_url) VALUES (:id, :kind, :title, :release, :rating, :cast, :cast_id, :genres, :duration, :budget, :worldwide_gross, :summary, :cover_url)", {"id": m['id'], "kind": m['kind'], "title": m['title'], "release": m['release'], "rating": m['rating'], "cast": cast, "cast_id": cast_id, "genres": genres, "duration": m['duration'], "budget": m['budget'], "worldwide_gross": m['worldwide_gross'], "summary": m['summary'], "cover_url": m['cover_url']})
                db.commit()
            elif 'series' in m['kind']:
                db.execute("INSERT INTO series (id, kind, title, release, rating, cast, cast_id, seasons, episodes, genres, duration, summary, cover_url) VALUES (:id, :kind, :title, :release, :rating, :cast, :cast_id, :seasons, :episodes, :genres, :duration, :summary, :cover_url)", {"id": m['id'], "kind": m['kind'], "title": m['title'], "release": m['release'], "rating": m['rating'], "cast": cast, "cast_id": cast_id, "seasons": m['seasons'], "episodes": m['episodes'], "genres": genres, "duration": m['duration'], "summary": m['summary'], "cover_url": m['cover_url']})
                db.commit()
            print(f"{m['title']} inserted")
            data = db.execute("SELECT * FROM watched WHERE wid = :wid", {"wid": m['id']}).fetchall()
            if len(data) <= 0:
                db.execute("INSERT INTO watched (wid, user_rating, kind, date, username) VALUES (:wid, :user_rating, :kind, :date, :username)", {"wid": m['id'], "user_rating": user_rating, "kind": m['kind'], "date": date, "username": session["username"]})
                db.commit()
                db.close()
                return "<script>alert('Added to Watched list'); window.location = window.history.back();</script>"
            else:
                db.close()
                return "<script>alert('You already watched this'); window.location = window.history.back();</script>"
        else:
            d = db.execute("SELECT * FROM watched WHERE wid = :wid", {"wid": m['id']}).fetchall()
            if len(d) <= 0:
                db.execute("INSERT INTO watched (wid, user_rating, kind, date, username) VALUES (:wid, :user_rating, :kind, :date, :username)", {"wid": m['id'], "user_rating": user_rating, "kind": data[0]['kind'], "date": date, "username": session["username"]})
                db.commit()
                db.close()
                return "<script>alert('Added to Watched list'); window.location = window.history.back();</script>"
            else:
                db.close()
                return "<script>alert('You already watched this'); window.location = window.history.back();</script>"
    else:
        return "<script>alert('Please Login first'); window.location = 'http://127.0.0.1:5000/login';</script>"

@app.route("/removeWatched/<id>", methods = ['GET', 'POST'])
def removeWatched(id):
    if session.get("logged_in"):
        db.execute("DELETE FROM watched WHERE wid = :wid", {"wid": id})
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
    print(movie_object)
    movie = ast.literal_eval(movie_object)
    if access == 'local':
        print("local")
        cast_url = ""
        ids = movie['cast_id'].split(', ')
        print(len(ids))
        for id in ids:
            p = ia.get_person(id)
            print("get_person() done")
            if 'full-size headshot' in p.keys():
                cast_url += p['full-size headshot'] + ", "
        movie['cast_url'] = cast_url[:-2]
    else:
        print("imdb")
        genres = ""
        for g in movie['genres']:
            genres += g + ", "
        genres = genres[:-2]
        movie['genres'] = genres
        cast = ""
        cast_url = ""
        for i in range(0, len(movie['cast_id'])):
            p = ia.get_person(movie['cast_id'][i])
            print("get_person() done")
            cast += movie['cast'][i] + f"({movie['roles'][i]}), "
            if 'full-size headshot' in p.keys():
                cast_url += p['full-size headshot'] + ", "
        movie['cast'] = cast[:-2]
        movie['cast_url'] = cast_url[:-2]
    return render_template("description.html", movie = movie, access = access)
