import os
import sqlite3
import pandas as pd
import glob

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

def delete_jds(jd_files):
    """Delete JD files and their associated scores from the database"""
    if not jd_files:
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        # Delete from database
        placeholders = ','.join(['?' for _ in jd_files])
        c.execute(f"DELETE FROM scores WHERE jd IN ({placeholders})", jd_files)
        conn.commit()

        # Delete files
        for jd_file in jd_files:
            file_path = os.path.join(UPLOAD_DIR, "jds", jd_file)
            if os.path.exists(file_path):
                os.remove(file_path)
                
        # Also delete any associated summaries
        for jd_file in jd_files:
            summary_pattern = os.path.join(UPLOAD_DIR, "summaries", f"{jd_file}_*.txt")
            for summary_file in glob.glob(summary_pattern):
                os.remove(summary_file)
                
    except Exception as e:
        print(f"Error deleting JDs: {e}")
    finally:
        conn.close()

def delete_resumes(jd_name, resume_names):
    """Delete selected resumes for a specific JD from the database"""
    if not resume_names:
        return
        
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        # Delete from database using parameterized query
        placeholders = ','.join(['?' for _ in resume_names])
        c.execute(f"DELETE FROM scores WHERE jd = ? AND resume IN ({placeholders})", 
                 [jd_name] + resume_names)
        conn.commit()
        
        # Delete associated summaries
        for resume_name in resume_names:
            summary_file = os.path.join(UPLOAD_DIR, "summaries", f"{jd_name}_{resume_name}.txt")
            if os.path.exists(summary_file):
                os.remove(summary_file)
                
    except Exception as e:
        print(f"Error deleting resumes: {e}")
    finally:
        conn.close()

