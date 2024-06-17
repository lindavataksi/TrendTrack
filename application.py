import os

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from cs50 import SQL
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from model import predict_stock_price

from helpers import apology, login_required, lookup, usd
import datetime

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    users = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    bank = users[0]["cash"]
    transactions = db.execute(
        "SELECT * FROM transactions WHERE user_id = ?;", session["user_id"])

    transactions = [
        dict(x, **{'price': lookup(x['symbol'])['price']}) for x in transactions]
    transactions = [dict(x, **{'total': x['price']*x['shares']})
                    for x in transactions]

    total = bank + sum([x['total'] for x in transactions])
    return render_template("index.html", bank=bank, transactions=transactions, total=total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "GET":
        return render_template("buy.html")
    elif request.method == "POST":
        symbol = request.form.get("symbol")
        share = request.form.get("shares")

        if not share:
            return apology("Invalid shares input", 400)

        try:
            share = int(share)
        except ValueError:
            return apology("Invalid shares input", 400)

        quote = lookup(symbol)

        if quote is None:
            return apology("Symbol not found", 400)
        elif share <= 0:
            return apology("Enter a positive number", 400)

        result = db.execute(
            "SELECT * FROM users WHERE id = ?;", session["user_id"])
        user_cash = result[0]["cash"]

        total_cost = share * quote["price"]

        user_id = session["user_id"]
        date = datetime.datetime.now()

        db.execute("INSERT INTO transactions (user_id, symbol, company, shares, price, total, date) VALUES (?, ?, ?, ?, ?, ?, ?);",
                   user_id, symbol, quote["name"], share, quote["price"], (share * quote["price"]), date)

        if user_cash < total_cost:
            return apology("Insufficient funds", 400)
        else:
            db.execute("UPDATE users SET cash = ? WHERE id = ?;",
                       (user_cash - total_cost), session["user_id"])
            flash("Bought!")
        return redirect("/")


@app.route("/history")
@login_required
def history():
    transactions = db.execute(
        "SELECT * FROM transactions WHERE user_id = ?;", session["user_id"])
    return render_template("history.html", transactions=transactions)


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
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

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
    if request.method == "GET":
        return render_template("quote.html")
    elif request.method == "POST":
        symbol = request.form.get("symbol")
        print("SYMBOL TEST", symbol)
        quote = lookup(symbol)
        print("QUOTE TEST", quote)
        if quote is None:
            flash("Invalid symbol or no data found for the symbol", "error")
            return redirect(url_for("quote"))
        else:
            flash("Quoted!")
            return render_template("quoted.html", name=quote["name"], price=quote["price"], symbol=quote["symbol"])
    else:
        return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    elif request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        passwordconfirmation = request.form.get("confirmation")
        existing_user = db.execute(
            "SELECT * FROM users WHERE username = ?", username)
        if not username:
            return apology("Username is required", 400)
        elif len(existing_user) != 0:
            return apology("User already exists", 400)
        elif not password:
            return apology("Enter a password", 400)
        elif not passwordconfirmation:
            return apology("Enter a password confirmation", 400)
        elif password != passwordconfirmation:
            return apology("Passwords do not match", 400)
        else:
            # Generate the hash of the password
            hash = generate_password_hash(
                password, method="pbkdf2:sha256", salt_length=8
            )
            db.execute(
                "INSERT INTO users (username, hash) VALUES(?, ?)", username, hash)
            flash("Registered!")
            return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    stock = db.execute("""SELECT symbol, sum(shares) as sum_of_shares
                                  FROM transactions
                                  WHERE user_id = ?
                                  GROUP BY user_id, symbol
                                  HAVING sum_of_shares > 0;""", session["user_id"])

    if request.method == "POST":
        symbol = request.form.get("symbol")
        share = int(request.form.get("shares"))
        if not share:
            return apology("Invalid shares input", 400)
        try:
            share = int(share)
        except ValueError:
            return apology("Invalid shares input", 400)

        quote = lookup(symbol)
        if quote is None:
            return apology("Symbol not found", 400)
        price = quote["price"]
        sale = share * price
        rows = db.execute(
            "SELECT cash FROM users WHERE id = :id", id=session["user_id"])
        usercash = sale + (rows[0]["cash"])

        if share > int(stock[0]["sum_of_shares"]):
            return apology("Cannot afford", 400)

        user_id = session["user_id"]
        date = datetime.datetime.now()

        db.execute("UPDATE users SET cash = ? WHERE id = ?;",
                   (usercash), session["user_id"])

        db.execute("INSERT INTO transactions (user_id, symbol, company, shares, price, total, date) VALUES (?, ?, ?, ?, ?, ?, ?);",
                   user_id, symbol, quote["name"], -share, quote["price"], (share * quote["price"]), date)

        flash("Sold!")
        return redirect("/")
    else:
        return render_template("sell.html", stock=stock)


@app.route("/predict", methods=['POST', 'GET'])
@login_required
def predict():
    user_stock = db.execute("""SELECT symbol, sum(shares) as sum_of_shares
                                  FROM transactions
                                  WHERE user_id = ?
                                  GROUP BY user_id, symbol
                                  HAVING sum_of_shares > 0;""", session["user_id"])
    if request.method == 'POST':
        ticker = request.form['Ticker']
        current_price, future_price, accuracy_percentage = predict_stock_price(
            ticker)

        # Check if the ticker exists in user_stock symbols
        ticker_in_user_stock = any(
            ticker == stock['symbol'] for stock in user_stock)

        if ticker_in_user_stock:
            if future_price > current_price:
                advice = "Future price is greater. Consider keeping the stock for potential gains."
            else:
                advice = "Current price is greater. You might want to sell the stock to avoid losses."
            prediction_text = (
                f"You currently hold this stock  - The current price of {ticker} is ${current_price} "
                f"and the predicted price after 1 year is ${future_price}."
            )
        else:
            prediction_text = (
                f"The current price of {ticker} is ${current_price} "
                f"and the predicted price after 1 year is ${future_price}."
            )
            advice = ""

        accuracy = ""
        if accuracy_percentage < 50:
            accuracy = " This is a volatile stock. Be cautious when considering this prediction."

        flash("Predicted!")
        return render_template('predict.html', prediction_text=prediction_text, accuracy=accuracy, advice=advice)

    return render_template('predict.html')


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# errors check
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

if __name__ == "__main__":
    app.run(debug=True)
