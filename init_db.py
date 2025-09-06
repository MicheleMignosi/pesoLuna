import sqlite3

conn = sqlite3.connect("luna.db")
c = conn.cursor()

# Creiamo la tabella se non esiste
c.execute("""
CREATE TABLE IF NOT EXISTS misurazioni (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT NOT NULL,
    peso REAL NOT NULL
)
""")

conn.commit()
conn.close()
print("Database creato con successo!")
