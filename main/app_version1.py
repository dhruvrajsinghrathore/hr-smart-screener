import os
import PyPDF2
import pandas as pd
import streamlit as st
from sentence_transformers import SentenceTransformer, util
from datetime import datetime

UPLOAD_DIR = "uploaded_data"
JD_DIR = os.path.join(UPLOAD_DIR, "jds")
RESUME_DIR = os.path.join(UPLOAD_DIR, "resumes")
SCORE_LOG = os.path.join(UPLOAD_DIR, "score_log.csv")

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
    weights = {"skills": 0.1, "experience": 0.6, "projects": 0.3}
    score = 0.0
    for sec, text in resume_sections.items():
        if text.strip() == "":
            continue
        emb = model.encode(text, convert_to_tensor=True)
        sim = util.pytorch_cos_sim(emb, jd_emb).item()
        score += weights.get(sec, 0.0) * sim
    return round(score * 100, 2)

def load_past_scores():
    if os.path.exists(SCORE_LOG):
        return pd.read_csv(SCORE_LOG)
    else:
        return pd.DataFrame(columns=["JD", "Resume", "Score", "Timestamp"])

def save_new_scores(new_scores):
    existing = load_past_scores()
    updated = pd.concat([existing, new_scores], ignore_index=True)
    updated.to_csv(SCORE_LOG, index=False)

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
    for file in uploaded_resumes:
        resume_path = os.path.join(RESUME_DIR, file.name)
        with open(resume_path, 'wb') as f:
            f.write(file.read())

jd_files = sorted(os.listdir(JD_DIR))
selected_jd = st.selectbox("Select a Job Description", jd_files)

if selected_jd:
    with open(os.path.join(JD_DIR, selected_jd), 'r', encoding='utf-8') as f:
        jd_text = f.read()
    st.text_area("Selected JD Content", jd_text, height=200)

    if st.button("Run Scoring"):
        current_scores = []
        processed_resumes = set(load_past_scores().query(f'JD == "{selected_jd}"')['Resume'])
        for resume_file in os.listdir(RESUME_DIR):
            if resume_file in processed_resumes:
                continue
            resume_path = os.path.join(RESUME_DIR, resume_file)
            resume_text = extract_text_from_pdf(resume_path)
            sections = extract_sections(resume_text)
            score = weighted_score(sections, jd_text)
            current_scores.append({
                "JD": selected_jd,
                "Resume": resume_file,
                "Score": score,
                "Timestamp": datetime.now().isoformat()
            })
        if current_scores:
            new_df = pd.DataFrame(current_scores)
            save_new_scores(new_df)
            st.success(f"Scored {len(current_scores)} new resume(s).")

st.subheader("Top Resumes for Selected JD")
score_data = load_past_scores()
filtered = score_data[score_data["JD"] == selected_jd].sort_values("Score", ascending=False).reset_index(drop=True)
st.dataframe(filtered, use_container_width=True, height=400)
