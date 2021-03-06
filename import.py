import os
import csv


from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.environ.get("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


f = open("books.csv")
reader = csv.reader(f)

for isbn, title, author, year in reader:
    db.execute("INSERT INTO booklist (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
               {"isbn": isbn, "title": title, "author": author, "year": year})
    print(
        f"Book: {title} by {author} was published in {year} and has ISBN number of  {isbn}.")
db.commit()
