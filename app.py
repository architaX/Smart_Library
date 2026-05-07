from flask import Flask, render_template, request, redirect, session, flash

from database import connect_db

from notification_thread import (
    start_notification_thread,
    admin_notifications,
    user_notifications
)

from fine_calculator import calculate_fine

from datetime import datetime


# ==========================================
# CREATE FLASK APPLICATION
# ==========================================

app = Flask(__name__)

# Secret key used for:
# - sessions
# - flash messages
app.secret_key = "smart_library_secret_key"


# ==========================================
# DEFAULT LIBRARIAN LOGIN
# ==========================================

LIBRARIAN_USERNAME = "admin"
LIBRARIAN_PASSWORD = "admin123"


# ==========================================
# START BACKGROUND THREAD
# ==========================================

start_notification_thread()


# ==========================================
# LOGIN PAGE
# ==========================================

@app.route("/", methods=["GET", "POST"])
def login():

    # POST means form submitted
    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        # ==================================
        # LIBRARIAN LOGIN
        # ==================================

        if (
            username == LIBRARIAN_USERNAME
            and
            password == LIBRARIAN_PASSWORD
        ):

            # Store session
            session["role"] = "librarian"
            session["username"] = "Librarian"

            return redirect("/librarian")

        # ==================================
        # USER LOGIN
        # ==================================

        conn = connect_db()
        cursor = conn.cursor()

        user = cursor.execute("""
        SELECT * FROM users
        WHERE username=? AND password=?
        """,
        (username, password)).fetchone()

        conn.close()

        # User found
        if user:

            session["role"] = "user"
            session["user_id"] = user["id"]
            session["username"] = user["username"]

            return redirect("/user")

        else:

            flash("Invalid Username or Password!")

    return render_template("login.html")


# ==========================================
# REGISTER USER
# ==========================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = connect_db()
        cursor = conn.cursor()

        try:

            cursor.execute("""
            INSERT INTO users(username,password)
            VALUES(?,?)
            """,
            (username, password))

            conn.commit()

            flash("Registration Successful!")

            return redirect("/")

        except:

            flash("Username already exists!")

        finally:

            conn.close()

    return render_template("register.html")


# ==========================================
# LIBRARIAN DASHBOARD
# ==========================================

@app.route("/librarian")
def librarian_dashboard():

    # Security check
    if session.get("role") != "librarian":

        return redirect("/")

    conn = connect_db()
    cursor = conn.cursor()

    # ======================================
    # GET ALL BOOKS
    # ======================================

    books = cursor.execute("""
    SELECT * FROM books
    """).fetchall()

    # ======================================
    # GET ALL USERS
    # ======================================

    users = cursor.execute("""
    SELECT * FROM users
    """).fetchall()

    # ======================================
    # GET ISSUED BOOKS
    # ======================================

    issued_books = cursor.execute("""

    SELECT
    issued_books.id,
    users.username,
    books.title,
    issued_books.issue_date,
    issued_books.due_date,
    issued_books.fine_amount,
    issued_books.return_status

    FROM issued_books

    JOIN users
    ON users.id = issued_books.user_id

    JOIN books
    ON books.id = issued_books.book_id

    """).fetchall()

    # ======================================
    # ANALYTICS
    # ======================================

    total_books = len(books)

    total_users = len(users)

    total_issued = len(issued_books)

    overdue_count = 0

    for issue in issued_books:

        if issue["fine_amount"] > 0:

            overdue_count += 1

    conn.close()

    return render_template(

        "librarian_dashboard.html",

        books=books,

        users=users,

        issued_books=issued_books,

        total_books=total_books,

        total_users=total_users,

        total_issued=total_issued,

        overdue_count=overdue_count,

        notifications=admin_notifications
    )


# ==========================================
# USER DASHBOARD
# ==========================================

@app.route("/user")
def user_dashboard():

    # Security check
    if session.get("role") != "user":

        return redirect("/")

    conn = connect_db()
    cursor = conn.cursor()

    # ======================================
    # GET ALL AVAILABLE BOOKS
    # ======================================

    books = cursor.execute("""
    SELECT * FROM books
    """).fetchall()

    # ======================================
    # GET USER BORROWED BOOKS
    # ======================================

    borrowed_books = cursor.execute("""

    SELECT
    books.title,
    issued_books.issue_date,
    issued_books.due_date,
    issued_books.fine_amount,
    issued_books.return_status

    FROM issued_books

    JOIN books
    ON books.id = issued_books.book_id

    WHERE issued_books.user_id=?

    """,
    (session["user_id"],)).fetchall()

    # ======================================
    # TOTAL FINE
    # ======================================

    total_fine = 0

    for book in borrowed_books:

        total_fine += book["fine_amount"]

    conn.close()

    return render_template(

        "user_dashboard.html",

        books=books,

        borrowed_books=borrowed_books,

        total_fine=total_fine,

        notifications=user_notifications.get(
            session["user_id"],
            []
        )
    )


# ==========================================
# ADD BOOK
# ==========================================

@app.route("/add_book", methods=["POST"])
def add_book():

    if session.get("role") != "librarian":

        return redirect("/")

    title = request.form["title"]
    author = request.form["author"]
    quantity = request.form["quantity"]

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO books(title,author,quantity)
    VALUES(?,?,?)
    """,
    (title, author, quantity))

    conn.commit()
    conn.close()

    flash("Book Added Successfully!")

    return redirect("/librarian")


# ==========================================
# ISSUE BOOK
# ==========================================

@app.route("/issue_book", methods=["POST"])
def issue_book():

    if session.get("role") != "librarian":

        return redirect("/")

    user_id = request.form["user_id"]
    book_id = request.form["book_id"]
    issue_date = request.form["issue_date"]
    due_date = request.form["due_date"]

    conn = connect_db()
    cursor = conn.cursor()

    # ======================================
    # CHECK BOOK QUANTITY
    # ======================================

    book = cursor.execute("""
    SELECT * FROM books
    WHERE id=?
    """,
    (book_id,)).fetchone()

    # No stock
    if book["quantity"] <= 0:

        flash("Book Out Of Stock!")

        conn.close()

        return redirect("/librarian")

    # ======================================
    # INSERT ISSUE RECORD
    # ======================================

    cursor.execute("""
    INSERT INTO issued_books(
    user_id,
    book_id,
    issue_date,
    due_date
    )
    VALUES(?,?,?,?)
    """,
    (
        user_id,
        book_id,
        issue_date,
        due_date
    ))

    # ======================================
    # REDUCE QUANTITY
    # ======================================

    cursor.execute("""
    UPDATE books
    SET quantity = quantity - 1
    WHERE id=?
    """,
    (book_id,))

    conn.commit()
    conn.close()

    flash("Book Issued Successfully!")

    return redirect("/librarian")


# ==========================================
# RETURN BOOK
# ==========================================

@app.route("/return_book/<int:id>")
def return_book(id):

    if session.get("role") != "librarian":

        return redirect("/")

    conn = connect_db()
    cursor = conn.cursor()

    issue = cursor.execute("""
    SELECT * FROM issued_books
    WHERE id=?
    """,
    (id,)).fetchone()

    if issue:

        # ==================================
        # UPDATE RETURN STATUS
        # ==================================

        cursor.execute("""
        UPDATE issued_books
        SET return_status='Returned'
        WHERE id=?
        """,
        (id,))

        # ==================================
        # INCREASE QUANTITY
        # ==================================

        cursor.execute("""
        UPDATE books
        SET quantity = quantity + 1
        WHERE id=?
        """,
        (issue["book_id"],))

        conn.commit()

        flash("Book Returned Successfully!")

    conn.close()

    return redirect("/librarian")


# ==========================================
# DELETE BOOK
# ==========================================

@app.route("/delete_book/<int:id>")
def delete_book(id):

    if session.get("role") != "librarian":

        return redirect("/")

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM books
    WHERE id=?
    """,
    (id,))

    conn.commit()
    conn.close()

    flash("Book Deleted Successfully!")

    return redirect("/librarian")


# ==========================================
# SEARCH USERS
# ==========================================

@app.route("/search_user", methods=["GET"])
def search_user():

    if session.get("role") != "librarian":

        return redirect("/")

    username = request.args.get("username")

    conn = connect_db()
    cursor = conn.cursor()

    users = cursor.execute("""
    SELECT * FROM users
    WHERE username LIKE ?
    """,
    ('%' + username + '%',)).fetchall()

    conn.close()

    return render_template(
        "search_results.html",
        users=users
    )


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    flash("Logged Out Successfully!")

    return redirect("/")


# ==========================================
# RUN FLASK APP
# ==========================================

if __name__ == "__main__":

    app.run(debug=True)