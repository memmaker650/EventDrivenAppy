import sqlite3

conn = sqlite3.connect("test.db")
conn.execute("CREATE TABLE IF NOT EXISTS test(id INTEGER)")
conn.close()

print("SQLite OK")