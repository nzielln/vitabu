import os

from flask import Flask, session, render_template, request, redirect, url_for, jsonify
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine
from flask_session import Session

from datetime import date
import requests

app = Flask(__name__)

# Check for environment variable
if not os.environ.get("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")
else:
    print("Connected!")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv(
    "DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/", methods=["GET", "POST"])
def signup():

    # clear any information from previous session

    firstname = request.form.get("firstname")
    lastname = request.form.get("lastname")
    username = request.form.get("username")
    password = request.form.get("password")

    errormessage1 = "Please ensure all fields are filled out."
    usermessage2 = "Please choose a different username."
    usermessage3 = "Please choose a different password."
    usermessage4 = "Please choose a different username and password."

    if request.method == "GET":
        if session.get("signed_in"):
            user_id = session.get("user_id")
            user = db.execute(
                "SELECT * FROM users WHERE id = :id", {"id": user_id}).fetchone()
            return render_template('welcome.html', firstname=user.firstname)
        else:
            return render_template("signup.html")

    if request.method == "POST":

        # make sure all fields are filled out
        if not request.form.get("firstname") or not request.form.get("lastname") or not request.form.get("username") or not request.form.get("password"):
            return render_template('signup.html', errormessage=errormessage1)
        # make sure username and passwords are not already in use
        checkname = db.execute(
            "SELECT * FROM users WHERE username = :uname", {"uname": username}).fetchone()
        if checkname:
            return render_template('signup.html', errormessage=usermessage2)

        checkword = db.execute(
            "SELECT * FROM users WHERE password = :pname", {"pname": password}).fetchone()
        if checkword:
            return render_template('signup.html', errormessage=usermessage3)
        session["user_name"] = username
        session["signed_in"] = True

        db.execute("INSERT INTO users (firstname, lastname, username, password) VALUES (:firstname, :lastname, :username, :password)",
                   {"firstname": firstname, "lastname": lastname, "username": username, "password": password})
        db.commit()
        user = db.execute(
            "SELECT * FROM users WHERE username = :username",  {"username": username}).fetchone()
        session["user_id"] = user.id

        return render_template('welcome.html', firstname=firstname)

        # set user_id and user_name
    return render_template("signup.html")


@app.route("/signin", methods=["GET", "POST"])
def signin():

    username = request.form.get("username")
    password = request.form.get("password")
    errormessage1 = "Please ensure all fields are filled out."
    usermessage4 = "Username/password is invalid"

    olduser = session.get("user_name")

    if request.method == "GET":
        if session.get("signed_in"):
            name = db.execute(
                "SELECT * FROM users WHERE username = :username", {"username": olduser}).fetchone()
            return render_template('welcome.html', firstname=name.firstname)
        else:
            return render_template("signin.html")

    if request.method == "POST":

            # make sure all fields are filled out
        if not request.form.get("username") or not request.form.get("password"):
            return render_template('signin.html', errormessage=errormessage1)
        # make sure username and passwords exist
        checkname = db.execute(
            "SELECT * FROM users WHERE username = :username", {"username": username}).fetchone()
        checkword = db.execute(
            "SELECT * FROM users WHERE password = :password", {"password": password}).fetchone()

        if checkname == None or not checkword:
            return render_template('signin.html', errormessage=usermessage4)
        else:
            getname = db.execute(
                "SELECT * FROM users WHERE username = :username", {"username": username}).fetchone()
            session["user_id"] = getname.id
            session["user_name"] = getname.username
            session["signed_in"] = True

            return render_template('welcome.html', firstname=getname.firstname)

    else:
        return render_template("signin.html")


@app.route("/books/<int:bookid>", methods=["GET", "POST"])
def book(bookid):
    books = db.execute(
        "SELECT * FROM booklist WHERE id = :id", {"id": bookid}).fetchone()
    title = books.title
    author = books.author
    isbn = books.isbn
    year = books.year

    # get all reviews on load
    reviews1 = db.execute(
        "SELECT * FROM reviews WHERE book_id= :bookid", {"bookid": bookid}).fetchall()

    # get initital ratings
    ratings1 = db.execute("SELECT ROUND(AVG(stars)) FROM reviews WHERE book_id= :bookid", {
        "bookid": bookid}).fetchone()[0]
    ratings_before = ratings1
    if ratings1 == None:
        ratings_before = 0
    else:
        ratings_before = ratings1

    starrating = ratings_before
    staro = (5 - starrating)

    # get initial number of ratings
    number_ratings = db.execute("SELECT COUNT(*) FROM reviews WHERE book_id= :bookid", {
        "bookid": bookid}).fetchone()[0]
    total_ratings = number_ratings

    # get good reads api

    res = requests.get("https://www.goodreads.com/book/review_counts.json",
                       params={"key": "8179G4POTuNJldXfQvIUsA", "isbns": isbn})
    if res.status_code != 200:
        return redirect("/")
    data = res.json()

    # get average rating and round it
    average_rating = float(data['books'][0]['average_rating'])
    ratings = round(average_rating)

    # get number of ratings
    work_ratings = data['books'][0]['work_ratings_count']

    # add to existing numbers (from database)
    if ratings1 == None or ratings_before == 0:
        starrating = ratings
    else:
        starrating = round((ratings_before + ratings)/2)

    staro = 5 - starrating
    total_ratings = work_ratings + number_ratings

    # make sure user is logged in
    if request.method == "GET":
        if session.get("user_id") is None and not session.get("signed_in"):
            return redirect("/signin")
        # if book not found
        if books is None:
            return render_template("bookpage.html", errormessage="Book not found. Please try again.")
        else:
            return render_template("bookpage.html", total_ratings=total_ratings, books=books, title=title, year=year, reviews=reviews1, author=author, isbn=isbn, stars=starrating, staro=staro)
    # when user submits review
    if request.method == "POST":
        check_user = db.execute("SELECT * FROM reviews WHERE username = :user AND book_id = :bookid",
                                {"user": session.get("user_name"), "bookid": bookid})
        # check to make sure they haven't submitted one before
        if check_user.rowcount == 1:
            return render_template("bookpage.html", total_ratings=total_ratings, books=books, title=title, year=year, reviews=reviews1, author=author, isbn=isbn, stars=starrating, staro=staro)
        book_id = bookid
        review = request.form.get("review")
        stars = int(request.form.get("rating"))
        today = date.today()
        # insert into database
        db.execute("INSERT INTO reviews (review, stars, username, date, book_id, user_id) VALUES (:review, :stars, :username, :date, :id, :user_id)", {
            "review": review, "stars": stars, "username": session.get('user_name'), "date": today, "id": book_id, "user_id": session.get('user_id')
        })
        db.commit()

# display reviews with submitted review
    reviews = db.execute(
        "SELECT * FROM reviews WHERE book_id= :bookid", {"bookid": bookid}).fetchall()
    # adjust ratings with new one
    ratings2 = db.execute("SELECT ROUND(AVG(stars)) FROM reviews WHERE book_id= :bookid", {
        "bookid": bookid}).fetchone()[0]
    total_ratings = work_ratings + number_ratings + 1
    starrating = round((ratings+ratings2)/2)
    staro = 5 - starrating
    return render_template("bookpage.html", total_ratings=total_ratings, title=title, year=year, author=author, isbn=isbn, books=books, reviews=reviews, stars=starrating, staro=staro)


@app.route("/search", methods=["GET", "POST"])
def search():
    if session.get("user_id") is None and not session.get("signed_in"):
        return redirect("/signin")

    title_n = request.form.get('title')
    isbn_n = request.form.get('isbn')
    author_n = request.form.get('author')
    message = "No books matching those details were found. Please try again."
    tryagain = "Search books."
    noauthor = "No Author Specified"
    notitle = "No Title specified"
    noisbn = "No ISBN Number specified"


# select books from list based on search criteria

    if request.method == "POST":

        if request.form.get('title') and not request.form.get('isbn') and not request.form.get('author'):
            title = title_n.lower()
            titles = db.execute(
                "SELECT * FROM booklist WHERE LOWER(title) LIKE '%"+title+"%' LIMIT 25")
            books = titles.fetchall()
            if not books:
                return render_template("results.html", message=message, tryagain=tryagain)
            else:
                return render_template("results.html", books=books, searchtitle=title, searchisbn=noisbn, searchauthor=noauthor)

        if not request.form.get('title') and request.form.get('isbn') and not request.form.get('author'):
            isbn = isbn_n.lower()
            titles = db.execute(
                "SELECT * FROM booklist WHERE LOWER(isbn) LIKE '%"+isbn+"%' LIMIT 25")
            books = titles.fetchall()
            if not books:
                return render_template("results.html", message=message, tryagain=tryagain)
            else:
                return render_template("results.html", books=books, searchtitle=title, searchisbn=noisbn, searchauthor=noauthor)

        if not request.form.get('title') and not request.form.get('isbn') and request.form.get('author'):
            author = author_n.lower()
            titles = db.execute(
                "SELECT * FROM booklist WHERE LOWER(author) LIKE '%"+author+"%' LIMIT 25")
            books = titles.fetchall()
            if not books:
                return render_template("results.html", message=message, tryagain=tryagain)
            else:
                return render_template("results.html", books=books, searchtitle=title, searchisbn=noisbn, searchauthor=noauthor)

    # more than one field filled out
        if request.form.get('title') and not request.form.get('isbn') and request.form.get('author'):
            title = title_n.lower()
            author = author_n.lower()

            titles = db.execute(
                "SELECT * FROM booklist WHERE LOWER(author) LIKE '%"+author+"%' AND LOWER(title) LIKE '%"+title+"%' LIMIT 25")
            books = titles.fetchall()
            if not books:
                return render_template("results.html", message=message, tryagain=tryagain)
            else:
                return render_template("results.html", books=books, searchtitle=title, searchisbn=noisbn, searchauthor=noauthor)
        if request.form.get('title') and request.form.get('isbn') and request.form.get('author'):
            title = title_n.lower()
            author = author_n.lower()
            isbn = isbn_n.lower()

            titles = db.execute(
                "SELECT * FROM booklist WHERE LOWER(author) LIKE '%"+author+"%' AND LOWER(title) LIKE '%"+title+"%' AND LOWER(isbn) LIKE '%"+isbn+"%' LIMIT 25")
            books = titles.fetchall()
            if not books:
                return render_template("results.html", message=message, tryagain=tryagain)
            else:
                return render_template("results.html", books=books, searchtitle=title, searchisbn=noisbn, searchauthor=noauthor)

        return render_template("results.html", message=message, tryagain=tryagain)
    else:
        return render_template("search.html")


@app.route("/results", methods=["GET"])
def results():
    if session.get("user_id") is None and not session.get("signed_in"):
        return redirect("/signin")
    return render_template("results.html")


@app.route("/signout")
def logout():
    session.clear()

    session["user_id"] = ""
    session["user_name"] = ""
    session["signed_in"] = False

    return redirect('/signin')


@app.route("/API/book/<isbn>", methods=["GET", "POST"])
def api(isbn):
    if session.get("user_id") is None and not session.get("signed_in"):
        return redirect("/signin")
    book = db.execute(
        "SELECT * FROM booklist WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    book_id = book.id

    # get reviews db
    reviews = db.execute(
        "SELECT * FROM reviews WHERE book_id= :bookid", {"bookid": book.id}).fetchall()

    # get ratings db
    db_ratings = db.execute("SELECT ROUND(AVG(stars)) FROM reviews WHERE book_id= :bookid", {
        "bookid": book.id}).fetchone()[0]

    # get number ratings fom db
    db_ratings_count = db.execute("SELECT COUNT(*) FROM reviews WHERE book_id= :bookid", {
        "bookid": book.id}).fetchone()[0]

    # get good reads api
    res = requests.get("https://www.goodreads.com/book/review_counts.json",
                       params={"key": "8179G4POTuNJldXfQvIUsA", "isbns": isbn})
    if res.status_code != 200:
        return redirect("/")
    data = res.json()

    # get api average rating and round it
    average_rating = float(data['books'][0]['average_rating'])
    api_ratings = round(average_rating)

    # get api number of ratings
    api_work_ratings = data['books'][0]['work_ratings_count']

    if db_ratings == None:
        db_ratings = 0
        rating = api_ratings
    else:
        db_ratings = db_ratings
        rating = round((db_ratings + api_ratings)/2)

    if db_ratings_count == None:
        db_ratings_count = 0
    else:
        db_ratings_count = db_ratings_count
        rating_count = db_ratings_count + api_work_ratings

    return jsonify({
        "title": book.title,
        "author": book.author,
        "year": book.year,
        "isbn": isbn,
        "review_count": rating_count,
        "average_score": rating
    })


if __name__ == '__main__':
    app.run(debug=True)
