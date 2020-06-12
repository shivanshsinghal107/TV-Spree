import os
import imdb

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

db.execute('''CREATE TABLE IF NOT EXISTS users (username VARCHAR(16) NOT NULL, password VARCHAR(64) NOT NULL,
            name VARCHAR(32) NOT NULL, join_date text, PRIMARY KEY(username))''')
db.execute('''CREATE TABLE IF NOT EXISTS email (mail VARCHAR(64) NOT NULL, username VARCHAR(16) NOT NULL,
            FOREIGN KEY(username) REFERENCES users(username) ON DELETE CASCADE ON UPDATE CASCADE,
            PRIMARY KEY(mail, username))''')
# origin, status, box office
db.execute('''CREATE TABLE IF NOT EXISTS movies (id INTEGER NOT NULL, kind VARCHAR(20), title VARCHAR(64), release text,
            rating FLOAT, cast text, cast_url text, genres VARCHAR(100), duration INTEGER, summary text, cover_url text, PRIMARY KEY(id))''')
# origin, status, box office, next_episode
db.execute('''CREATE TABLE IF NOT EXISTS series (id INTEGER NOT NULL, kind VARCHAR(20), title VARCHAR(64), release text,
            rating FLOAT, cast text, cast_url text, seasons INTEGER, episodes INTEGER, genres VARCHAR(100), duration INTEGER, summary text, cover_url text, PRIMARY KEY(id))''')
db.execute('''CREATE TABLE IF NOT EXISTS mwatched (id INTEGER PRIMARY KEY AUTOINCREMENT, wid INTEGER NOT NULL,
            username VARCHAR(16) NOT NULL, FOREIGN KEY(username) REFERENCES users(username) ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY(wid) REFERENCES movies(id) ON DELETE CASCADE ON UPDATE CASCADE)''')
db.execute('''CREATE TABLE IF NOT EXISTS swatched (id INTEGER PRIMARY KEY AUTOINCREMENT, wid INTEGER NOT NULL,
            username VARCHAR(16) NOT NULL, FOREIGN KEY(username) REFERENCES users(username) ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY(wid) REFERENCES series(id) ON DELETE CASCADE ON UPDATE CASCADE)''')
db.commit()
db.close()

def main():
    ia = imdb.IMDb()
    top250 = ia.get_top250_movies()
    count = 1
    for t in top250[:10]:
        id = t.movieID
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
        db.execute("INSERT INTO movies (id, kind, title, release, rating, cast, cast_url, genres, duration, summary, cover_url) VALUES (:id, :kind, :title, :release, :rating, :cast, :cast_url, :genres, :duration, :summary, :cover_url)", {"id": id, "kind": m['kind'], "title": m['title'], "release": m['original air date'][:11], "rating": m['rating'], "cast": cast, "cast_url": cast_url, "genres": genres, "duration": m['runtimes'][0], "summary": plot, "cover_url": m['full-size cover url']})
        db.commit()
        print(f"{count}. {m['title']} inserted")
        count += 1
    movies = db.execute("SELECT * FROM movies").fetchall()
    series = db.execute("SELECT * FROM series").fetchall()
    if len(movies) > 0:
        for movie in movies:
            print(f'Title: {movie.title}\tDuration: {movie.duration} minutes\tRating: {movie.rating}')
    else:
        print("No movies in database till now")

    if len(series) > 0:
        for s in series:
            print(f'{s.title}\tSeason {s.season}\tRating {s.rating}')
    else:
        print("\nNo series in database till now")

if __name__ == "__main__":
    main()
