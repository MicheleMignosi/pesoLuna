from datetime import datetime
import os
import json
import sqlite3
from flask import Flask, render_template, request, redirect, url_for
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__, template_folder="templates", static_folder="static")

DB_FILE = "luna.db"
DATA_NASCITA = datetime.strptime("2025-08-25", "%Y-%m-%d")  # data reale di nascita

# Minimi e massimi peso per settimana
CRESCITA = {
    0: (2.5, 4.5), 1: (2.7, 4.8), 2: (2.9, 5.0), 3: (3.1, 5.3),
    4: (3.3, 5.6), 5: (3.6, 5.9), 6: (3.8, 6.2), 7: (4.0, 6.5),
    8: (4.3, 6.8), 9: (4.5, 7.0), 10: (4.7, 7.2), 11: (4.9, 7.4),
    12: (5.1, 7.6), 13: (5.3, 7.8), 14: (5.5, 8.0), 15: (5.7, 8.2),
    16: (5.9, 8.4), 17: (6.1, 8.6), 18: (6.3, 8.8), 19: (6.5, 9.0),
    20: (6.7, 9.2), 21: (6.9, 9.4), 22: (7.1, 9.6), 23: (7.3, 9.8),
    24: (7.5, 10.0)
}

# -------------------------
# Google Sheets Setup
# -------------------------
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
google_creds = os.getenv("GOOGLE_CREDENTIALS")
if google_creds is None:
    raise RuntimeError("⚠️ Variabile GOOGLE_CREDENTIALS non trovata su Render!")

info = json.loads(google_creds)
CREDS = Credentials.from_service_account_info(info, scopes=SCOPES)
gc = gspread.authorize(CREDS)

# Inserisci qui l'ID del tuo Google Sheet
SHEET_ID = "TUO_SHEET_ID"

# -------------------------
# Funzioni di utilità
# -------------------------
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Crea il DB se non esiste e inserisce dati iniziali"""
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS misurazioni (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL UNIQUE,
                peso REAL NOT NULL
            )
        """)
        # Misurazioni iniziali
        iniziali = [
            ("2025-08-25", 3.55),
            ("2025-08-30", 3.45),
            ("2025-09-02", 3.50)
        ]
        conn.executemany("INSERT INTO misurazioni (data, peso) VALUES (?, ?)", iniziali)
        conn.commit()
        conn.close()
        print("Database creato con dati iniziali!")

# Inizializza DB all'avvio
init_db()

# -------------------------
# Rotte Flask
# -------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/inserisci", methods=["POST"])
def inserisci():
    peso = float(request.form["peso"])
    data = datetime.now().strftime("%Y-%m-%d")

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO misurazioni (data, peso)
        VALUES (?, ?)
        ON CONFLICT(data) DO UPDATE SET peso=excluded.peso
    """, (data, peso))
    conn.commit()
    conn.close()

    # 🔹 Backup su Google Sheets
    try:
        sh = gc.open_by_key(SHEET_ID)
        worksheet = sh.Foglio1
        worksheet.append_row([data, peso])
    except Exception as e:
        print("Errore scrittura Google Sheets:", e)

    return redirect(url_for("grafico"))

@app.route("/grafico")
def grafico():
    conn = get_db_connection()
    rows = conn.execute("SELECT data, peso FROM misurazioni ORDER BY data").fetchall()
    conn.close()

    labels = []
    pesi = []
    min_range = []
    max_range = []

    for row in rows:
        data_mis = datetime.strptime(row["data"], "%Y-%m-%d")
        settimana = (data_mis - DATA_NASCITA).days // 7

        # Formatta data in italiano
        labels.append(data_mis.strftime("%d/%m/%Y"))
        pesi.append(row["peso"])

        # Valori min/max per la settimana della rilevazione
        if settimana in CRESCITA:
            minimo, massimo = CRESCITA[settimana]
        else:
            ultimo_sett = max(CRESCITA.keys())
            minimo, massimo = CRESCITA[ultimo_sett]

        min_range.append(float(minimo))
        max_range.append(float(massimo))

    return render_template("grafico.html",
                           labels=labels,
                           pesi=pesi,
                           min_range=min_range,
                           max_range=max_range)

# -------------------------
# Avvio Flask
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)






