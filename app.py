import imdb
import ast
import os, datetime
import numpy as np
import pandas as pd
# these below two lines are for avoiding a runtime error
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from collections import Counter, OrderedDict
from base64 import b64encode
from io import BytesIO

from flask import Flask, session, request, render_template, redirect, url_for
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
    mtrending = db.execute("SELECT * FROM movies WHERE tag = :tag ORDER BY id", {"tag": "trending"}).fetchall()
    strending = db.execute("SELECT * FROM series WHERE tag = :tag ORDER BY id", {"tag": "trending"}).fetchall()
    mupcoming = db.execute("SELECT * FROM movies WHERE tag = :tag ORDER BY id", {"tag": "upcoming"}).fetchall()
    mtoprated = db.execute("SELECT * FROM movies WHERE tag = :tag ORDER BY id", {"tag": "top_rated"}).fetchall()
    stoprated = db.execute("SELECT * FROM series WHERE tag = :tag ORDER BY id", {"tag": "top_rated"}).fetchall()
    netflix = []
    for m in db.execute("SELECT * FROM movies WHERE tag = :tag ORDER BY id", {"tag": "netflix"}).fetchall():
        netflix.append(m)
    for s in db.execute("SELECT * FROM series WHERE tag = :tag ORDER BY id", {"tag": "netflix"}).fetchall():
        netflix.append(s)
    amazon = []
    for m in db.execute("SELECT * FROM movies WHERE tag = :tag ORDER BY id", {"tag": "amazon"}).fetchall():
        amazon.append(m)
    for s in db.execute("SELECT * FROM series WHERE tag = :tag ORDER BY id", {"tag": "amazon"}).fetchall():
        amazon.append(s)
    db.close()
    if session.get("logged_in"):
        curruser = session["username"]
        return render_template("index.html", loginstatus = 'True', curruser = curruser, mtrending = mtrending, strending = strending, mupcoming = mupcoming, mtoprated = mtoprated, stoprated = stoprated, netflix = netflix, amazon = amazon)
    else:
        return render_template("index.html", loginstatus = 'False', mtrending = mtrending, strending = strending, mupcoming = mupcoming, mtoprated = mtoprated, stoprated = stoprated, netflix = netflix, amazon = amazon)

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
    data = db.execute("SELECT DISTINCT * FROM movies WHERE title LIKE :title", {"title": search}).fetchall()
    res = ia.search_movie(title)
    if len(data) > 0:
        in_ids = []
        for d in data:
            movies.append(d)
            access.append('local')
            in_ids.append(int(d.wid))
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
        data = db.execute("SELECT DISTINCT * FROM series WHERE title LIKE :title", {"title": search}).fetchall()
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
    print(len(movies), res[0]['kind'], access[0])
    if len(movies) == 0:
        db.close()
        return "<script>alert('No results found');window.location = 'http://127.0.0.1:5000/';</script>"
    db.close()
    if session.get("logged_in"):
        return render_template("search.html", movies = movies, loginstatus = 'True', curruser = session["username"],
                                access = access)
    else:
        return render_template("search.html", movies = movies, loginstatus = 'False', access = access)

@app.route("/<username>/<table>", methods = ['GET', 'POST'])
def watchlist(username, table):
    if session.get("logged_in"):
        username = session["username"]
        db.execute("CREATE TABLE watchlist AS SELECT * FROM mwatched UNION SELECT * FROM swatched")
        watched = db.execute("SELECT * FROM watchlist WHERE username = :username AND list = :list ORDER BY date DESC", {"username": username, "list": table}).fetchall()
        movies = []
        ratings = []
        for w in watched:
            wid = w.wid
            mdata = db.execute("SELECT DISTINCT * FROM movies WHERE wid = :wid", {"wid": wid}).fetchall()
            sdata = db.execute("SELECT DISTINCT * FROM series WHERE wid = :wid", {"wid": wid}).fetchall()
            if len(mdata) > 0:
                movies.append(mdata[0])
                ratings.append(w.user_rating)
            elif len(sdata) > 0:
                movies.append(sdata[0])
                ratings.append(w.user_rating)
            else:
                break
        db.execute("DROP TABLE IF EXISTS watchlist")
        db.close()
        return render_template("watchlist.html", table = table, curruser = username, movies = movies, ratings = ratings)
    else:
        return "<script>alert('Please Login first'); window.location = 'http://127.0.0.1:5000/login';</script>"

@app.route("/add/<id>", methods = ['GET', 'POST'])
def add(id):
    if session.get("logged_in"):
        access = request.args.get("access")
        movie_object = request.args.get("movie_object")
        m = ast.literal_eval(movie_object)
        user_rating = request.form.get("user_rating")
        table = request.form.get("status").lower()
        date = str(datetime.datetime.utcnow())
        data = db.execute("SELECT DISTINCT * FROM movies WHERE wid = :wid", {"wid": id}).fetchall()
        if len(data) <= 0:
            data = db.execute("SELECT DISTINCT * FROM series WHERE wid = :wid", {"wid": id}).fetchall()
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
                for i in range(0, len(m['cast'])):
                    cast += m['cast'][i] + f"({m['roles'][i]}), "
                cast = cast[:-2]
            else:
                cast = m['cast']
            if 'movie' in m['kind']:
                db.execute("INSERT INTO movies (wid, tag, kind, title, release, rating, cast, cast_id, genres, duration, budget, worldwide_gross, summary, cover_url) VALUES (:wid, :tag, :kind, :title, :release, :rating, :cast, :cast_id, :genres, :duration, :budget, :worldwide_gross, :summary, :cover_url)", {"wid": m['wid'], "tag": "any", "kind": m['kind'], "title": m['title'], "release": m['release'], "rating": m['rating'], "cast": cast, "cast_id": cast_id, "genres": genres, "duration": m['duration'], "budget": m['budget'], "worldwide_gross": m['worldwide_gross'], "summary": m['summary'], "cover_url": m['cover_url']})
                watch_table = 'mwatched'
            elif 'series' in m['kind']:
                db.execute("INSERT INTO series (wid, tag, kind, title, release, rating, cast, cast_id, seasons, episodes, genres, duration, summary, cover_url) VALUES (:wid, :tag, :kind, :title, :release, :rating, :cast, :cast_id, :seasons, :episodes, :genres, :duration, :summary, :cover_url)", {"wid": m['wid'], "tag": "any", "kind": m['kind'], "title": m['title'], "release": m['release'], "rating": m['rating'], "cast": cast, "cast_id": cast_id, "seasons": m['seasons'], "episodes": m['episodes'], "genres": genres, "duration": m['duration'], "summary": m['summary'], "cover_url": m['cover_url']})
                watch_table = 'swatched'
            db.commit()
            print(f"{m['title']} inserted")
            data = db.execute(f"SELECT * FROM {watch_table} WHERE wid = :wid", {"wid": m['wid']}).fetchall()
            if len(data) <= 0:
                db.execute(f"INSERT INTO {watch_table} (wid, user_rating, list, date, username) VALUES (:wid, :user_rating, :list, :date, :username)", {"wid": m['wid'], "user_rating": user_rating, "list": table, "date": date, "username": session["username"]})
                db.commit()
                db.close()
                return "<script>alert('Added to watch list'); window.location = window.history.back();</script>"
            else:
                db.close()
                return "<script>alert('Already in the watch list'); window.location = window.history.back();</script>"
        else:
            if 'movie' in data[0]['kind']:
                watch_table = 'mwatched'
            else:
                watch_table = 'swatched'
            d = db.execute(f"SELECT * FROM {watch_table} WHERE wid = :wid", {"wid": m['wid']}).fetchall()
            if len(d) <= 0:
                db.execute(f"INSERT INTO {watch_table} (wid, user_rating, list, date, username) VALUES (:wid, :user_rating, :list, :date, :username)", {"wid": m['wid'], "user_rating": user_rating, "list": table, "date": date, "username": session["username"]})
                db.commit()
                db.close()
                return "<script>alert('Added to watch list'); window.location = window.history.back();</script>"
            else:
                db.close()
                return "<script>alert('Already in the watch list'); window.location = window.history.back();</script>"
    else:
        return "<script>alert('Please login first'); window.location = 'http://127.0.0.1:5000/login';</script>"

@app.route("/removeWatched/<id>/<kind>/<list>", methods = ['GET', 'POST'])
def removeWatched(id, kind, list):
    if session.get("logged_in"):
        if 'movie' in kind:
            watch_table = 'mwatched'
        else:
            watch_table = 'swatched'
        db.execute(f"DELETE FROM {watch_table} WHERE wid = :wid AND list = :list", {"wid": id, "list": list})
        db.commit()
        db.close()
        print("deleted")
        username = session["username"]
        return redirect(f"http://127.0.0.1:5000/{username}/{list}")
    else:
        return "<script>alert('Please login first'); window.location = 'http://127.0.0.1:5000/login';</script>"

@app.route("/addto", methods = ['GET', 'POST'])
def addto():
    if request.method == 'POST':
        remove_list = request.args.get("list").lower()
        id = request.args.get("id")
        kind = request.args.get("kind")
        add_list = request.form.get("addto").lower()
        username = session["username"]
        return redirect(f"http://127.0.0.1:5000/moveto/{remove_list}/{add_list}/{id}/{kind}")
    else:
        return "<script>alert('Method not allowed'); window.location = window.history.back();</script>"

@app.route("/moveto/<remove_list>/<add_list>/<id>/<kind>", methods = ['GET', 'POST'])
def moveto(remove_list, add_list, id, kind):
    if 'movie' in kind:
        watch_table = 'mwatched'
    else:
        watch_table = 'swatched'
    date = str(datetime.datetime.utcnow())
    username = session["username"]
    db.execute(f"UPDATE {watch_table} SET list = :list WHERE username = :username AND wid = :wid", {"list": add_list, "username": username, "wid": id})
    db.commit()
    db.close()
    return redirect(f"http://127.0.0.1:5000/{username}/{remove_list}")

@app.route("/<id>/description", methods = ['GET', 'POST'])
def description(id):
    access = request.args.get("access")
    movie_object = request.args.get("movie_object")
    movie = ast.literal_eval(movie_object)
    if access == 'local':
        cast_url = ""
        ids = movie['cast_id'].split(', ')
        for id in ids:
            p = ia.get_person(id)
            print("get_person() done")
            if 'full-size headshot' in p.keys():
                cast_url += p['full-size headshot'] + ", "
        movie['cast_url'] = cast_url[:-2]
    else:
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

@app.route("/<username>", methods = ['GET', 'POST'])
def profile(username):
    if session.get("logged_in"):
        lists = ['completed', 'watching', 'paused', 'dropped']
        movies = []
        series = []
        genres = []
        hours = 0
        matrix = np.zeros([1, 60], dtype = int)
        dates = []
        for list in lists:
            for m in (db.execute(f"SELECT * FROM mwatched WHERE list = :list", {"list": list}).fetchall()):
                movies.append(m)
                dates.append(int(m.date[8:10]))
            for s in (db.execute("SELECT * FROM swatched WHERE list = :list", {"list": list}).fetchall()):
                series.append(s)
                dates.append(int(s.date[8:10]))
        for m in movies:
            data = db.execute("SELECT DISTINCT * FROM movies WHERE wid = :wid", {"wid": m.wid}).fetchall()[0]
            if data.duration != 'NA':
                hours += int(data.duration)
            gdata = data['genres'].split(', ')
            for g in gdata:
                genres.append(g)
        for s in series:
            data = db.execute("SELECT DISTINCT * FROM series WHERE wid = :wid", {"wid": s.wid}).fetchall()[0]
            if data.duration != 'NA':
                hours += int(data.episodes) * int(data.duration)
            gdata = data['genres'].split(', ')
            for g in gdata:
                genres.append(g)
        if len(genres) > 0:
            c = dict(Counter(genres))
            sorted_count = sorted(c.items(), key = lambda x: x[1])
            counts = OrderedDict(sorted_count)
            df = pd.DataFrame(counts.items(), columns=['Genre', 'Value'])
            df['Percent'] = round((df['Value'] / sum(df['Value']))*100).astype(int)
            fig = plt.figure()
            plt.barh(range(len(df)), df['Percent'], align = 'center')
            plt.yticks(range(len(df)), df['Genre'])
            plt.xlim(0, np.max(df['Percent'])*1.4)
            for i, v in enumerate(df['Percent']):
                plt.text(v + 0.5, i, str(v)+"%", color='black')
            plt.xticks([])
            plt.box(False)
            img = BytesIO()
            fig.savefig(img, format = 'png', bbox_inches = 'tight')
            img.seek(0)
            encoded = b64encode(img.getvalue())

            d = dict(Counter(dates))
            sorted_days = sorted(d.items(), key = lambda x: x[1])
            days = dict(sorted_days)
            for day in days.keys():
                matrix[0][day] = days[day]
            W = matrix.reshape(3, 20)
            Z = np.random.randn(3, 20)
            fig1 = plt.figure(figsize = (11, 2))
            plt.pcolormesh(Z, edgecolors='w', linewidths=5, cmap ='Greens')
            plt.xticks([])
            plt.yticks([])
            plt.box(False)
            img1 = BytesIO()
            fig1.savefig(img1, format = 'png', bbox_inches = 'tight')
            img.seek(0)
            encoded1 = b64encode(img1.getvalue())

            hours /= 60
            days = round(hours/24)
            db.close()
            return render_template("profile.html", curruser = session["username"], movies = len(movies), series = len(series), hours = round(hours), days = days, img_data = encoded.decode('utf-8'), img1_data = encoded1.decode('utf-8'), activity = "True")
        else:
            db.close()
            return render_template("profile.html", curruser = session["username"], movies = len(movies), series = len(series), hours = 0, days = 0, activity = "False")
    else:
        return "<script>alert('Please login first'); window.location = 'http://127.0.0.1:5000/login';</script>"
