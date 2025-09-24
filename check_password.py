import os
import sys
import sqlite3
from werkzeug.security import check_password_hash

def get_db_conn():
    """Establishes a connection to the database."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, 'quicksave', 'data', 'quicksave.db')
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        sys.exit(1)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def check_password(username, password):
    """Checks if the provided password is correct for the given username."""
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

    if user:
        if check_password_hash(user['password_hash'], password):
            print(f"✅ Password for user '{username}' is correct.")
        else:
            print(f"❌ Password for user '{username}' is incorrect.")
    else:
        print(f"User '{username}' not found in the database.")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python check_password.py <username> <password>")
        sys.exit(1)

    username_arg = sys.argv[1]
    password_arg = sys.argv[2]
    check_password(username_arg, password_arg)