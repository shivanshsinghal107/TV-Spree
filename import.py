import os
import imdb
import requests
import datetime
from bs4 import BeautifulSoup

from flask import Flask, session
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

db.execute('''CREATE TABLE IF NOT EXISTS users (username VARCHAR(16) NOT NULL, password VARCHAR(64) NOT NULL, join_date text,
            PRIMARY KEY(username))''')
db.execute('''CREATE TABLE IF NOT EXISTS email (mail VARCHAR(64) NOT NULL, username VARCHAR(16) NOT NULL,
            FOREIGN KEY(username) REFERENCES users(username) ON DELETE CASCADE ON UPDATE CASCADE,
            PRIMARY KEY(mail, username))''')
# origin, status
db.execute('''CREATE TABLE IF NOT EXISTS movies (id INTEGER PRIMARY KEY AUTOINCREMENT, wid INTEGER NOT NULL, tag VARCHAR(30),
            kind VARCHAR(20), title VARCHAR(64), release text, rating FLOAT, cast text, cast_id text, genres VARCHAR(100), duration INTEGER, budget VARCHAR(40), worldwide_gross VARCHAR(40), summary text, cover_url text)''')
# origin, status, next_episode
db.execute('''CREATE TABLE IF NOT EXISTS series (id INTEGER PRIMARY KEY AUTOINCREMENT, wid INTEGER NOT NULL, tag VARCHAR(30),
            kind VARCHAR(20), title VARCHAR(64), release text, rating FLOAT, cast text, cast_id text, seasons INTEGER, episodes INTEGER, genres VARCHAR(100), duration INTEGER, summary text, cover_url text)''')
# movies watchlist
db.execute('''CREATE TABLE IF NOT EXISTS mwatched (id INTEGER PRIMARY KEY AUTOINCREMENT, wid INTEGER NOT NULL, user_rating INTEGER,
            list VARCHAR(10), date text, username VARCHAR(16) NOT NULL, FOREIGN KEY(username) REFERENCES users(username) ON DELETE CASCADE ON UPDATE CASCADE, FOREIGN KEY(wid) REFERENCES movies(wid) ON DELETE CASCADE ON UPDATE CASCADE)''')
# series watchlist
db.execute('''CREATE TABLE IF NOT EXISTS swatched (id INTEGER PRIMARY KEY AUTOINCREMENT, wid INTEGER NOT NULL, user_rating INTEGER,
            list VARCHAR(10), date text, username VARCHAR(16) NOT NULL, FOREIGN KEY(username) REFERENCES users(username) ON DELETE CASCADE ON UPDATE CASCADE, FOREIGN KEY(wid) REFERENCES series(wid) ON DELETE CASCADE ON UPDATE CASCADE)''')
db.commit()

# IMDb Access
ia = imdb.IMDb()

def fetch_movies(ids, tag):
    count = 1
    for id in ids:
        m = ia.get_movie(id)
        plot = ""
        if 'plot outline' in m.keys():
            plot = m['plot outline']
        elif 'plot' in m.keys():
            plot = m['plot'][0]
        if "::" in plot:
            plot = plot.split("::")[0]
        rating = "NA"
        if 'rating' in m.keys():
            rating = m['rating']
        release = "NA"
        if 'original air date' in m.keys():
            release = m['original air date'][:11]
        budget = "NA"
        gross = "NA"
        if 'box office' in m.keys():
            if 'Budget' in m['box office'].keys():
                budget = m['box office']['Budget']
            if 'Cumulative Worldwide Gross' in m['box office'].keys():
                gross = m['box office']['Cumulative Worldwide Gross']
        duration = "NA"
        if 'runtimes' in m.keys():
            duration = m['runtimes'][0]
        cover_url = ""
        if 'full-size cover url' in m.keys():
            cover_url = m['full-size cover url']
        elif 'cover url' in m.keys():
            cover_url = m['cover url']
        genres = ""
        for g in m['genres']:
            genres += g + ", "
        genres = genres[:-2]
        cast = ""
        cast_id = ""
        for c in m['cast'][:5]:
            cast += c['name'] + f"({c.currentRole}), "
            cast_id += f"{c.personID}, "
        cast = cast[:-2]
        cast_id = cast_id[:-2]

        db.execute("INSERT INTO movies (wid, tag, kind, title, release, rating, cast, cast_id, genres, duration, budget, worldwide_gross, summary, cover_url) VALUES (:wid, :tag, :kind, :title, :release, :rating, :cast, :cast_id, :genres, :duration, :budget, :worldwide_gross, :summary, :cover_url)", {"wid": id, "tag": tag, "kind": m['kind'], "title": m['title'], "release": release, "rating": rating, "cast": cast, "cast_id": cast_id, "genres": genres, "duration": duration, "budget": budget, "worldwide_gross": gross, "summary": plot, "cover_url": cover_url})
        db.commit()
        print(f"{count}. {m['title']} inserted")
        count += 1

def fetch_series(ids, tag):
    count = 1
    for id in ids:
        m = ia.get_movie(id)
        ia.update(m, 'episodes')
        plot = ""
        if 'plot outline' in m.keys():
            plot = m['plot outline']
        elif 'plot' in m.keys():
            plot = m['plot'][0]
        if "::" in plot:
            plot = plot.split("::")[0]
        rating = "NA"
        if 'rating' in m.keys():
            rating = m['rating']
        release = "NA"
        seasons = "NA"
        if 'series years' in m.keys():
            release = m['series years']
            if release[-1] == '-':
                release += 'Ongoing'
            else:
                start = release.split("-")[0]
                end = release.split("-")[1]
                seasons = int(end) - int(start)
        if 'number of seasons' in m.keys():
            seasons = m['number of seasons']
        episodes = "NA"
        if 'number of episodes' in m.keys():
            episodes = m['number of episodes']
        duration = "NA"
        if 'runtimes' in m.keys():
            duration = m['runtimes'][0]
        cover_url = ""
        if 'full-size cover url' in m.keys():
            cover_url = m['full-size cover url']
        elif 'cover url' in m.keys():
            cover_url = m['cover url']
        genres = ""
        if 'genres' in m.keys():
            for g in m['genres']:
                genres += g + ", "
            genres = genres[:-2]
        else:
            genres = "NA"
        cast = ""
        cast_id = ""
        for c in m['cast'][:5]:
            cast += c['name'] + f"({c.currentRole}), "
            cast_id += f"{c.personID}, "
        cast = cast[:-2]
        cast_id = cast_id[:-2]

        db.execute("INSERT INTO series (wid, tag, kind, title, release, rating, cast, cast_id, seasons, episodes, genres, duration,  summary, cover_url) VALUES (:wid, :tag, :kind, :title, :release, :rating, :cast, :cast_id, :seasons, :episodes, :genres, :duration,  :summary, :cover_url)", {"wid": id, "tag": tag, "kind": m['kind'], "title": m['title'], "release": release, "rating": rating, "cast": cast, "cast_id": cast_id, "seasons": seasons, "episodes": episodes, "genres": genres, "duration": duration, "summary": plot, "cover_url": cover_url})
        db.commit()
        print(f"{count}. {m['title']} inserted")
        count += 1

# Trending Movies right now
def trending_movies():
    print("Fetching trending movies")
    res = requests.get("https://www.imdb.com/chart/moviemeter/")
    soup = BeautifulSoup(res.text, "html.parser")
    table = soup.find("table")
    data = table.find_all("td", {"class": "posterColumn"})
    ids = []
    for d in data[:4]:
        i = d.find("a")['href'].split("tt")[1]
        ids.append(i[:-1])

    print("Movies IDs fetching done")
    fetch_movies(ids, 'trending')

# Trending TV Shows right now
def trending_series():
    print("Fetching trending series")
    res = requests.get("https://www.imdb.com/chart/tvmeter/")
    soup = BeautifulSoup(res.text, "html.parser")
    table = soup.find("table")
    data = table.find_all("td", {"class": "posterColumn"})
    ids = []
    for d in data[:4]:
        i = d.find("a")['href'].split("tt")[1]
        ids.append(i[:-1])

    print("Series IDs fetching done")
    fetch_series(ids, 'trending')

# Movies Coming Soon
def movies_coming_soon():
    print("Fetching coming soon movies")
    month = int(str(datetime.datetime.utcnow())[5:7])
    ids = []
    for i in range(month+3, month+5):
        if i >= 10:
            res = requests.get(f"https://www.imdb.com/movies-coming-soon/2020-{i}/")
        else:
            res = requests.get(f"https://www.imdb.com/movies-coming-soon/2020-0{i}/")
        soup = BeautifulSoup(res.text, "html.parser")
        div = soup.find("div", {"class": "list detail"})
        tables = div.find_all("table")
        for table in tables[:2]:
            h = table.find("h4")
            a = h.find("a")['href'].split("tt")[1]
            ids.append(a[:-1])

    print("Movies IDs fetching done")
    fetch_movies(ids, 'upcoming')

def fetch_streaming_platforms(ids, tag):
    count = 1
    for id in ids:
        m = ia.get_movie(id)
        if 'series' in m['kind']:
            ia.update(m, 'episodes')
            plot = ""
            if 'plot outline' in m.keys():
                plot = m['plot outline']
            elif 'plot' in m.keys():
                plot = m['plot'][0]
            if "::" in plot:
                plot = plot.split("::")[0]
            rating = "NA"
            if 'rating' in m.keys():
                rating = m['rating']
            release = "NA"
            seasons = "NA"
            if 'series years' in m.keys():
                release = m['series years']
                if release[-1] == '-':
                    release += 'Ongoing'
                else:
                    start = release.split("-")[0]
                    end = release.split("-")[1]
                    seasons = int(end) - int(start)
            if 'number of seasons' in m.keys():
                seasons = m['number of seasons']
            episodes = "NA"
            if 'number of episodes' in m.keys():
                episodes = m['number of episodes']
            duration = "NA"
            if 'runtimes' in m.keys():
                duration = m['runtimes'][0]
            cover_url = ""
            if 'full-size cover url' in m.keys():
                cover_url = m['full-size cover url']
            elif 'cover url' in m.keys():
                cover_url = m['cover url']
            genres = ""
            if 'genres' in m.keys():
                for g in m['genres']:
                    genres += g + ", "
                genres = genres[:-2]
            else:
                genres = "NA"
            cast = ""
            cast_id = ""
            for c in m['cast'][:5]:
                cast += c['name'] + f"({c.currentRole}), "
                cast_id += f"{c.personID}, "
            cast = cast[:-2]
            cast_id = cast_id[:-2]

            db.execute("INSERT INTO series (wid, tag, kind, title, release, rating, cast, cast_id, seasons, episodes, genres, duration,  summary, cover_url) VALUES (:wid, :tag, :kind, :title, :release, :rating, :cast, :cast_id, :seasons, :episodes, :genres, :duration,  :summary, :cover_url)", {"wid": id, "tag": tag, "kind": m['kind'], "title": m['title'], "release": release, "rating": rating, "cast": cast, "cast_id": cast_id, "seasons": seasons, "episodes": episodes, "genres": genres, "duration": duration, "summary": plot, "cover_url": cover_url})
            db.commit()
        else:
            plot = ""
            if 'plot outline' in m.keys():
                plot = m['plot outline']
            elif 'plot' in m.keys():
                plot = m['plot'][0]
            if "::" in plot:
                plot = plot.split("::")[0]
            rating = "NA"
            if 'rating' in m.keys():
                rating = m['rating']
            release = "NA"
            if 'original air date' in m.keys():
                release = m['original air date'][:11]
            budget = "NA"
            gross = "NA"
            if 'box office' in m.keys():
                if 'Budget' in m['box office'].keys():
                    budget = m['box office']['Budget']
                if 'Cumulative Worldwide Gross' in m['box office'].keys():
                    gross = m['box office']['Cumulative Worldwide Gross']
            duration = "NA"
            if 'runtimes' in m.keys():
                duration = m['runtimes'][0]
            cover_url = ""
            if 'full-size cover url' in m.keys():
                cover_url = m['full-size cover url']
            elif 'cover url' in m.keys():
                cover_url = m['cover url']
            genres = ""
            for g in m['genres']:
                genres += g + ", "
            genres = genres[:-2]
            cast = ""
            cast_id = ""
            for c in m['cast'][:5]:
                cast += c['name'] + f"({c.currentRole}), "
                cast_id += f"{c.personID}, "
            cast = cast[:-2]
            cast_id = cast_id[:-2]

            db.execute("INSERT INTO movies (wid, tag, kind, title, release, rating, cast, cast_id, genres, duration, budget, worldwide_gross, summary, cover_url) VALUES (:wid, :tag, :kind, :title, :release, :rating, :cast, :cast_id, :genres, :duration, :budget, :worldwide_gross, :summary, :cover_url)", {"wid": id, "tag": tag, "kind": m['kind'], "title": m['title'], "release": release, "rating": rating, "cast": cast, "cast_id": cast_id, "genres": genres, "duration": duration, "budget": budget, "worldwide_gross": gross, "summary": plot, "cover_url": cover_url})
            db.commit()
        print(f"{count}. {m['title']} inserted")
        count += 1

# Upcoming Netflix Originals
def upcoming_on_netflix():
    print("Fetching Upcoming Netflix Originals")
    res = requests.get("https://www.imdb.com/list/ls025607548/?sort=moviemeter,asc&st_dt=&mode=detail&page=1")
    soup = BeautifulSoup(res.text, "html.parser")
    heads = soup.find_all("h3", {"class": "lister-item-header"})
    ids = []
    if len(heads) > 8:
        for h in heads[:8]:
            i = h.find("a")['href'].split("tt")[1]
            ids.append(i[:-1])
    else:
        for h in heads:
            i = h.find("a")['href'].split("tt")[1]
            ids.append(i[:-1])

    print("Netflix IDs fetching done")
    fetch_streaming_platforms(ids, 'netflix')

# Upcoming Amazon Originals
def upcoming_on_amazon():
    print("Fetching Upcoming Amazon Originals")
    res = requests.get("https://www.imdb.com/list/ls025817658/?sort=moviemeter,asc&st_dt=&mode=detail&page=1")
    soup = BeautifulSoup(res.text, "html.parser")
    heads = soup.find_all("h3", {"class": "lister-item-header"})
    ids = []
    if len(heads) > 8:
        for h in heads[:8]:
            i = h.find("a")['href'].split("tt")[1]
            ids.append(i[:-1])
    else:
        for h in heads:
            i = h.find("a")['href'].split("tt")[1]
            ids.append(i[:-1])

    print("Amazon IDs fetching done")
    fetch_streaming_platforms(ids, 'amazon')

# Top Rated Movies
def top_movies():
    print("Fetching top rated movies")
    top250 = ia.get_top250_movies()
    ids = []
    for t in top250[:4]:
        ids.append(t.movieID)

    print("Movies IDs fetching done")
    fetch_movies(ids, 'top_rated')

# Top Rated TV Shows
def top_series():
    print("Fetching top rated series")
    res = requests.get("https://www.imdb.com/chart/toptv/")
    soup = BeautifulSoup(res.text, "html.parser")
    table = soup.find("table")
    data = table.find_all("td", {"class": "posterColumn"})
    ids = []
    for d in data[:4]:
        i = d.find("a")['href'].split("tt")[1]
        ids.append(i[:-1])

    print("Series IDs fetching done")
    fetch_series(ids, 'top_rated')

update = input("Update top rated movies & series(Y/N): ")
if update.upper() == 'Y':
    top_series()
    print()
    top_movies()
    print()
trending_movies()
print()
trending_series()
print()
movies_coming_soon()
print()
upcoming_on_netflix()
print()
upcoming_on_amazon()
db.close()
print("Finished")
