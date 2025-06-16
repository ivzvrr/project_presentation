import sqlite3


conn = sqlite3.connect("users.db")
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS allowed_users (
        user_id INTEGER PRIMARY KEY,
        username TEXT
    )
""")
conn.commit()