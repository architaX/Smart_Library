from datetime import datetime

def calculate_fine(due_date):

    today = datetime.now().date()

    due = datetime.strptime(
        due_date,
        "%Y-%m-%d"
    ).date()

    # ₹5 per day fine
    fine_per_day = 5

    if today > due:

        days_late = (today - due).days

        return days_late * fine_per_day

    return 0