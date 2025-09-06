import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__, template_folder="templates", static_folder="static")

DB_FILE = "luna.db"
DATA_NASCITA = datetime.strptime("2023-08-25", "%Y-%m-%d")  # data vera di nascita

CRESCITA = {
    0: (2.5, 4.5), 1: (2.7, 4.8), 2: (2.9, 5.0), 3: (3.1, 5.3),
    4: (3.3, 5.6), 5: (3.6, 5.9), 6: (3.8, 6.2), 7: (4.0, 6.5),
    8: (4.3, 6.8), 9: (4.5, 7.0), 10: (4.7, 7.2), 11: (4.9, 7.4),
    12: (5.1, 7.6), 13: (5.3, 7.8), 14: (5.5, 8.0), 15: (5.7, 8.2),
    16: (5.9, 8.4), 17: (6.1, 8.6), 18: (6.3, 8.8), 19: (6.5, 9.0),
    20: (6.7, 9.2), 21: (6.9, 9.4), 22: (7.1, 9.6), 23: (7.3, 9.8),
    24: (7.5, 10.0)
}

# Google Sheets API via Secret
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
google_creds = os.getenv("GOOGLE_CREDENTIALS")
if google_creds is None:
    raise RuntimeError("⚠️ Variabile GOOGLE_CREDENTIALS non trovata su Render!")

info = json.loads(google_creds)
CREDS = Credentials.from_service_account_info(info, scopes=SCOPES)
gc = gspread.authorize(CREDS)
SHEET_ID = "1twt_TcE9Tkmg0g2ypDBDwqYVL89x1YcW88t3phUzOFs"
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.sheet1


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/inserisci", methods=["POST"])
def inserisci():
    peso = float(request.form["peso"])
    data = datetime.now().strftime("%Y-%m-%d")

    # Salva su SQLite
    conn = get_db_connection()
    conn.execute("""
        INSERT INTO misurazioni (data, peso)
        VALUES (?, ?)
        ON CONFLICT(data) DO UPDATE SET peso=excluded.peso
    """, (data, peso))
    conn.commit()
    conn.close()

    # Backup automatico su Google Sheets
    worksheet.append_row([data, peso])

    return redirect(url_for("grafico"))


@app.route("/grafico")
def grafico():
    conn = get_db_connection()
    rows = conn.execute("SELECT data, peso FROM misurazioni ORDER BY data").fetchall()
    conn.close()

    labels = [datetime.strptime(row["data"], "%Y-%m-%d").strftime("%d/%m/%Y") for row in rows]
    pesi = [row["peso"] for row in rows]

    min_range, max_range = [], []
    for row in rows:
        data_mis = datetime.strptime(row["data"], "%Y-%m-%d")
        settimane = (data_mis - DATA_NASCITA).days // 7
        if settimane in CRESCITA:
            minimo, massimo = CRESCITA[settimane]
        else:
            ultimo_sett = max(CRESCITA.keys())
            minimo, massimo = CRESCITA[ultimo_sett]
        min_range.append(float(minimo))
        max_range.append(float(massimo))

    return render_template(
        "grafico.html",
        labels=labels,
        pesi=pesi,
        min_range=min_range,
        max_range=max_range
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)





