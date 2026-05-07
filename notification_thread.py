import threading
import time

from database import connect_db
from fine_calculator import calculate_fine


# =========================================
# GLOBAL NOTIFICATIONS
# Librarian sees all
# =========================================

admin_notifications = []


# =========================================
# USER-SPECIFIC NOTIFICATIONS
# Example:
# {
#   1: ["Book overdue"],
#   2: ["Due tomorrow"]
# }
# =========================================

user_notifications = {}


# =========================================
# BACKGROUND THREAD FUNCTION
# =========================================

def check_notifications():

    while True:

        conn = connect_db()
        cursor = conn.cursor()

        # CLEAR OLD NOTIFICATIONS
        admin_notifications.clear()
        user_notifications.clear()

        # =================================
        # LOW STOCK BOOKS
        # =================================

        low_stock = cursor.execute("""
        SELECT * FROM books
        WHERE quantity <= 1
        """).fetchall()

        for book in low_stock:

            message = (
                f"Only {book['quantity']} copy left of "
                f"{book['title']}"
            )

            admin_notifications.append(message)

        # =================================
        # OVERDUE BOOKS
        # =================================

        issued = cursor.execute("""

        SELECT
        issued_books.*,
        books.title,
        users.username

        FROM issued_books

        JOIN books
        ON books.id = issued_books.book_id

        JOIN users
        ON users.id = issued_books.user_id

        WHERE issued_books.return_status='Not Returned'

        """).fetchall()

        for issue in issued:

            fine = calculate_fine(issue["due_date"])

            # UPDATE FINE
            cursor.execute("""
            UPDATE issued_books
            SET fine_amount=?
            WHERE id=?
            """,
            (fine, issue["id"]))

            # =================================
            # OVERDUE NOTIFICATION
            # =================================

            if fine > 0:

                admin_message = (
                    f"{issue['username']} has overdue book: "
                    f"{issue['title']} | Fine ₹{fine}"
                )

                admin_notifications.append(admin_message)

                # USER NOTIFICATION
                user_message = (
                    f"Your book '{issue['title']}' "
                    f"is overdue. Fine ₹{fine}"
                )

                user_id = issue["user_id"]

                # CREATE USER LIST
                if user_id not in user_notifications:

                    user_notifications[user_id] = []

                user_notifications[user_id].append(
                    user_message
                )

        conn.commit()
        conn.close()

        # RUN EVERY 10 SECONDS
        time.sleep(10)


# =========================================
# START THREAD
# =========================================

def start_notification_thread():

    thread = threading.Thread(
        target=check_notifications,
        daemon=True
    )

    thread.start()