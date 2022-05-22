import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/" , methods=["GET"])
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = session["user_id"]
    transactions = db.execute("SELECT * FROM (SELECT symbol, SUM(shares) as shares, price FROM transactions WHERE user_id=? GROUP by symbol) WHERE shares !=0 ",user_id)
    cash_db = db.execute("SELECT cash FROM users WHERE id=?",user_id)
    cash = cash_db[0]["cash"]

    total = cash

    for shares in transactions:
        total += shares["price"] * shares["shares"]

    return render_template ("index.html", database = transactions, cash = cash , total = total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")

    else:
        symbol = request.form.get("symbol")
        shares=int(request.form.get("shares"))

        if not symbol:
            return apology ("")

        stock=lookup(symbol.upper())

        if stock == None:
            return apology("Symbol Doesn't Exist")

        if shares<1:
            return apology("Enter a no. more than 0")

        transaction_value = shares*stock["price"]

        user_id = session["user_id"]
        user_cash_db = db.execute("SELECT cash FROM users WHERE id=?", user_id)
        user_cash = user_cash_db[0]["cash"]

        if transaction_value > user_cash:
            return apology("Insuffucuent balance")

        new_cash = user_cash - transaction_value

        date= datetime.datetime.now()

        db.execute("UPDATE users SET cash=? WHERE id=? ", new_cash, user_id )

        db.execute("INSERT into transactions (user_id, symbol, shares, price, datetime) values (?,?,?,?,?)",user_id,stock["symbol"],shares,stock["price"],date )

        flash("Bought!")

        return redirect ("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    """Show portfolio of stocks"""
    user_id = session["user_id"]
    transactions = db.execute("SELECT symbol, shares, price, datetime FROM transactions WHERE user_id=?",user_id)

    return render_template ("history.html", database = transactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    #If request method is get. return template
    if request.method == "GET":
        return render_template("quote.html")

    #else submit the quote
    else:
        symbol = request.form.get("symbol")

        if not symbol:
            return apology ("No Symbol")

        stock=lookup(symbol.upper())

        if stock == None:
            return apology("Symbol Doesn't Exist")
        return render_template("quoted.html", name = stock["name"], price = stock["price"], symbol = stock["symbol"] )


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")

    else:
        username = request.form.get("username")
        password=  request.form.get("password")
        confirmation=  request.form.get("confirmation")

        if not username:
            return apology("Username required")

        if not password:
            return apology("Password required")

        if password != confirmation:
            return apology("Passwords do not match")

        hash=generate_password_hash(password)
        try:
            new_user = db.execute ("INSERT INTO users (username,hash) VALUES (?,?)",username,hash )
        except:
            return apology ("Username already exists")

        session["user_id"]= new_user

        return redirect("/")



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":

       user_id = session["user_id"]

       symbols_user = db.execute("SELECT DISTINCT symbol FROM transactions WHERE user_id=?",user_id)

       return render_template("sell.html", symbols = [row["symbol"] for row in symbols_user])

    else:
        symbol = request.form.get("symbol")

        shares=int(request.form.get("shares"))

        if not symbol:
            return apology ("Enter a symbol")

        stock=lookup(symbol.upper())

        if stock == None:
            return apology("Symbol Doesn't Exist")

        if shares<1:
            return apology("Enter a no. more than 0")

        transaction_value = shares*stock["price"]

        user_id = session["user_id"]
        user_cash_db = db.execute("SELECT cash FROM users WHERE id=?", user_id)
        user_cash = user_cash_db[0]["cash"]

        user_shares_db= db.execute("SELECT shares FROM transactions WHERE user_id=? AND symbol=? GROUP by shares", user_id, symbol )
        user_shares= user_shares_db[0]["shares"]

        if shares > user_shares:
            return apology("Shares not in portfolio")


        new_cash = user_cash + transaction_value

        date= datetime.datetime.now()

        db.execute("UPDATE users SET cash=? WHERE id=? ", new_cash, user_id )

        db.execute("INSERT into transactions (user_id, symbol, shares, price, datetime) values (?,?,?,?,?)",user_id,stock["symbol"], ((-1) * (shares)),stock["price"],date )

        flash("Sold!")

        return redirect ("/")



@app.route("/changepwd", methods=["GET", "POST"])
def changepwd():
    """Change Password"""
    if request.method == "GET":
        return render_template("change_pwd.html")

    else:
        new_pwd=  request.form.get("new_pwd")
        confirmation=  request.form.get("confirmation")

        user_id = session["user_id"]

        if not new_pwd:
            return apology("New Password required")

        if new_pwd != confirmation:
            return apology("Passwords do not match")

        hash=generate_password_hash(new_pwd)
        try:
            db.execute ("UPDATE users SET hash=? WHERE id=?",hash, user_id )
        except:
            return apology ("No can do")

        return redirect("/")

