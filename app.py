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
    1: (3.66, 3.59),
    2: (3.87, 3.73),
    3: (4.08, 3.87),
    4: (4.29, 4.01),
    5: (4.50, 4.15),
    6: (4.71, 4.29),
    7: (4.92, 4.43),
    8: (5.13, 4.57),
    9: (5.34, 4.71),
    10: (5.55, 4.85),
    11: (5.76, 4.99),
    12: (5.97, 5.13),
    13: (6.18, 5.27),
    14: (6.39, 5.41),
    15: (6.60, 5.55),
    16: (6.81, 5.69),
    17: (7.02, 5.83),
    18: (7.23, 5.97),
    19: (7.44, 6.11),
    20: (7.65, 6.25),
    21: (7.86, 6.39),
    22: (8.07, 6.53),
    23: (8.28, 6.67)
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
SHEET_NAME = "Sheet1"  # Assicurati che questo sia il nome corretto del foglio

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







