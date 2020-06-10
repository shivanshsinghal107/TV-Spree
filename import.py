import os

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
db.execute('''CREATE TABLE IF NOT EXISTS movies (id INTEGER NOT NULL, title VARCHAR(64), release_date text, status VARCHAR(20),
            rating FLOAT(1), genre VARCHAR(64), cast text, duration INTEGER, summary text, PRIMARY KEY(id))''')
db.execute('''CREATE TABLE IF NOT EXISTS series (id INTEGER NOT NULL, title VARCHAR(64), release_date text, staus VARCHAR(20),
            rating FLOAT(1), season INTEGER, episodes INTEGER, cast text, duration INTEGER, genre VARCHAR(64), origin VARCHAR(20), summary text, next_episode text, PRIMARY KEY(id))''')
db.execute('''CREATE TABLE IF NOT EXISTS mwatched (id INTEGER PRIMARY KEY AUTOINCREMENT, wid INTEGER NOT NULL,
            username VARCHAR(16) NOT NULL, FOREIGN KEY(username) REFERENCES users(username) ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY(wid) REFERENCES movies(id) ON DELETE CASCADE ON UPDATE CASCADE)''')
db.execute('''CREATE TABLE IF NOT EXISTS swatched (id INTEGER PRIMARY KEY AUTOINCREMENT, wid INTEGER NOT NULL,
            username VARCHAR(16) NOT NULL, FOREIGN KEY(username) REFERENCES users(username) ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY(wid) REFERENCES series(id) ON DELETE CASCADE ON UPDATE CASCADE)''')
db.commit()
db.close()

def main():
    movies = db.execute("SELECT * FROM movies").fetchall()
    series = db.execute("SELECT * FROM series").fetchall()
    if len(movies) > 0:
        for movie in movies:
            print(f'{movie.title}\t{movie.year}\tRating {movie.rating}')
    else:
        print("No movies in database till now")

    if len(series) > 0:
        for s in series:
            print(f'{s.title}\tSeason {s.season}\tRating {s.rating}')
    else:
        print("No series in database till now")

if __name__ == "__main__":
    main()
