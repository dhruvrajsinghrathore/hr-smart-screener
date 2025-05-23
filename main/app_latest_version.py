import os
import PyPDF2
import pandas as pd
import streamlit as st
import sqlite3
from sentence_transformers import SentenceTransformer, util
from datetime import datetime

UPLOAD_DIR = "uploaded_data"
JD_DIR = os.path.join(UPLOAD_DIR, "jds")
RESUME_DIR = os.path.join(UPLOAD_DIR, "resumes")
DB_PATH = os.path.join(UPLOAD_DIR, "scores.db")

os.makedirs(JD_DIR, exist_ok=True)
os.makedirs(RESUME_DIR, exist_ok=True)

model = SentenceTransformer('all-MiniLM-L6-v2')

def extract_text_from_pdf(file_path):
    with open(file_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        return " ".join(page.extract_text() or "" for page in reader.pages)

def extract_sections(text):
    sections = {"skills": "", "experience": "", "projects": "", "other": ""}
    current = "other"
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        l = line.lower()
        if "skill" in l:
            current = "skills"
        elif "experience" in l:
            current = "experience"
        elif "project" in l:
            current = "projects"
        sections[current] += line + " "
    return sections

def weighted_score(resume_sections, jd_text):
    jd_emb = model.encode(jd_text, convert_to_tensor=True)
    weights = {"skills": 0.1, "experience": 0.6, "projects": 0.3}## make this dynamic that can be set by the user from the UI
    score = 0.0
    for sec, text in resume_sections.items():
        if text.strip() == "":
            continue
        emb = model.encode(text, convert_to_tensor=True)
        sim = util.pytorch_cos_sim(emb, jd_emb).item()
        score += weights.get(sec, 0.0) * sim
    return round(score * 100, 2)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS scores (
                    jd TEXT,
                    resume TEXT,
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

def truncate_scores():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM scores")
    conn.commit()
    conn.close()

init_db()

st.title("Resume-to-JD Matching Dashboard")

st.sidebar.header("Upload Section")
uploaded_jd = st.sidebar.file_uploader("Upload Job Description", type=["txt"])
uploaded_resumes = st.sidebar.file_uploader("Upload Resume(s)", type=["pdf"], accept_multiple_files=True)

if uploaded_jd:
    jd_name = uploaded_jd.name
    jd_path = os.path.join(JD_DIR, jd_name)
    with open(jd_path, 'wb') as f:
        f.write(uploaded_jd.read())

if uploaded_resumes:
    uploaded_resume_names = []
    for file in uploaded_resumes:
        resume_path = os.path.join(RESUME_DIR, file.name)
        uploaded_resume_names.append(file.name)
        with open(resume_path, 'wb') as f:
            f.write(file.read())
else:
    uploaded_resume_names = []

jd_files = sorted(os.listdir(JD_DIR))
selected_jd = st.selectbox("Select a Job Description", jd_files)

if selected_jd:
    with open(os.path.join(JD_DIR, selected_jd), 'r', encoding='utf-8') as f:
        jd_text = f.read()
    st.text_area("Selected JD Content", jd_text, height=200)

    if st.button("Run Scoring") and uploaded_resume_names:
        db_df = load_scores()
        processed_resumes = set(db_df.query(f'jd == "{selected_jd}"')['resume'])
        current_scores = []
        for resume_file in uploaded_resume_names:
            if resume_file in processed_resumes:
                continue
            resume_path = os.path.join(RESUME_DIR, resume_file)
            resume_text = extract_text_from_pdf(resume_path)
            sections = extract_sections(resume_text)
            score = weighted_score(sections, jd_text)
            current_scores.append({
                "jd": selected_jd,
                "resume": resume_file,
                "score": score,
                "timestamp": datetime.now().isoformat()
            })
        if current_scores:
            new_df = pd.DataFrame(current_scores)
            save_scores_to_db(new_df)
            st.success(f"Scored {len(current_scores)} new resume(s).")

if st.sidebar.button("Reset Score Database"):
    truncate_scores()
    st.sidebar.success("All resume scores have been cleared.")

st.subheader("Top Resumes for Selected JD")
scores_df = load_scores()
filtered = scores_df[scores_df["jd"] == selected_jd].sort_values("score", ascending=False).reset_index(drop=True)
st.dataframe(filtered, use_container_width=True, height=400)

csv_all = scores_df.to_csv(index=False).encode('utf-8')
st.download_button("Download All Scores (CSV)", csv_all, "all_jd_resume_scores.csv", "text/csv")
