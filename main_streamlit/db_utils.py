import os
import sqlite3
import pandas as pd

UPLOAD_DIR = "uploaded_data"
DB_PATH = os.path.join(UPLOAD_DIR, "scores.db")

def init_db():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS scores (
                    jd TEXT,
                    resume TEXT,
                    email TEXT,
                    score REAL,
                    timestamp TEXT
                )''')
    conn.commit()
    conn.close()

def load_scores():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM scores", conn)
    conn.close()
    return df

def save_scores_to_db(df):
    conn = sqlite3.connect(DB_PATH)
    df.to_sql("scores", conn, if_exists='append', index=False)
    conn.commit()
    conn.close()

def delete_jds(jd_list):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for jd in jd_list:
        c.execute("DELETE FROM scores WHERE jd = ?", (jd,))
        jd_path = os.path.join("uploaded_data", "jds", jd)
        if os.path.exists(jd_path):
            os.remove(jd_path)
    conn.commit()
    conn.close()

