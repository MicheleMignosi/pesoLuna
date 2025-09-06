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
    0: (3.45, 3.45),
    1: (3.59, 3.66),
    2: (3.73, 3.87),
    3: (3.87, 4.08),
    4: (4.01, 4.29),
    5: (4.15, 4.50),
    6: (4.29, 4.71),
    7: (4.43, 4.92),
    8: (4.57, 5.13),
    9: (4.71, 5.34),
    10: (4.85, 5.55),
    11: (4.99, 5.76),
    12: (5.13, 5.97),
    13: (5.27, 6.18),
    14: (5.41, 6.39),
    15: (5.55, 6.60),
    16: (5.69, 6.81),
    17: (5.83, 7.02),
    18: (5.97, 7.23),
    19: (6.11, 7.44),
    20: (6.25, 7.65),
    21: (6.39, 7.86),
    22: (6.53, 8.07),
    23: (6.67, 8.28)
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

SHEET_ID = "1twt_TcE9Tkmg0g2ypDBDwqYVL89x1YcW88t3phUzOFs"
SHEET_NAME = "Foglio1"  

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

    # Salva in SQLite
    conn = get_db_connection()
    conn.execute("""
        INSERT INTO misurazioni (data, peso)
        VALUES (?, ?)
        ON CONFLICT(data) DO UPDATE SET peso=excluded.peso
    """, (data, peso))
    conn.commit()
    conn.close()

    # 🔹 Backup su Google Sheets con debug dettagliato
    try:
        print("Provo ad aprire il Google Sheet...")
        sh = gc.open_by_key(SHEET_ID)
        worksheet = sh.worksheet(SHEET_NAME)
        worksheet.append_row([data, peso])
        print(f"Riga scritta su Google Sheet: {data}, {peso}")
    except gspread.SpreadsheetNotFound:
        print(f"Errore: Google Sheet con ID '{SHEET_ID}' non trovato!")
    except gspread.WorksheetNotFound:
        print(f"Errore: Foglio '{SHEET_NAME}' non trovato nel Google Sheet!")
    except Exception as e:
        print("Errore generico durante scrittura Google Sheets:", e)

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







