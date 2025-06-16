import sqlite3


conn = sqlite3.connect("users.db")
cursor = conn.cursor()
cursor.execute(
    "INSERT INTO allowed_users VALUES (788845076, 'ivzvrr')"
)
conn.commit()