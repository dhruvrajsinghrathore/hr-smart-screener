import os
import pandas as pd
from datetime import datetime
import streamlit as st
from resume_parser import extract_text_from_pdf, extract_sections, extract_email
from scorer import weighted_score
from summarizer import summarize_resume_with_jd
from db_utils import init_db, load_scores, save_scores_to_db, delete_jds

UPLOAD_DIR = "uploaded_data"
JD_DIR = os.path.join(UPLOAD_DIR, "jds")
RESUME_DIR = os.path.join(UPLOAD_DIR, "resumes")
SUMMARY_DIR = os.path.join(UPLOAD_DIR, "summaries")

os.makedirs(JD_DIR, exist_ok=True)
os.makedirs(RESUME_DIR, exist_ok=True)
os.makedirs(SUMMARY_DIR, exist_ok=True)

init_db()

st.set_page_config(page_title="Resume Analyzer Pro", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
        .stApp {
            background-color: #0e1117;
            color: white;
        }
        .block-container {
            padding-top: 1rem;
        }
        h1 {
            text-align: center;
        }
        .custom-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 18px;
            color: white;
        }
        .custom-table th, .custom-table td {
            padding: 10px;
            border-bottom: 1px solid #444;
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1>📊 Resume Analyzer Pro</h1>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.subheader("📥 Upload Resumes")
    uploaded_resumes = st.file_uploader("Upload Resume(s)", type=["pdf"], accept_multiple_files=True)

with col2:
    st.subheader("📋 Job Description")
    uploaded_jd = st.file_uploader("Upload JD (.txt)", type=["txt"])
    jd_text_input = st.text_area("Or paste JD below if not uploading:")
    jd_name_input = st.text_input("JD Title (required to save JD for dashboard)", max_chars=100)

jd_files = sorted(os.listdir(JD_DIR))

if "selected_jd" not in st.session_state:
    st.session_state.selected_jd = jd_files[0] if jd_files else ""

selected_jd = st.selectbox("Select Existing JD (for viewing/summarizing)", jd_files, index=jd_files.index(st.session_state.selected_jd) if st.session_state.selected_jd in jd_files else 0)

uploaded_resume_names = []
if uploaded_resumes:
    for file in uploaded_resumes:
        resume_path = os.path.join(RESUME_DIR, file.name)
        uploaded_resume_names.append(file.name)
        with open(resume_path, 'wb') as f:
            f.write(file.read())

if st.button("Analyze Resumes"):
    jd_name = ""
    jd_text = ""
    if uploaded_jd:
        jd_text = uploaded_jd.read().decode("utf-8")
        jd_name = uploaded_jd.name
    elif jd_text_input.strip() and jd_name_input.strip():
        jd_text = jd_text_input.strip()
        jd_name = jd_name_input.strip() + ".txt"
    elif selected_jd:
        jd_name = selected_jd
        with open(os.path.join(JD_DIR, jd_name), 'r', encoding='utf-8') as f:
            jd_text = f.read()

    if jd_text and jd_name:
        jd_path = os.path.join(JD_DIR, jd_name)
        if not os.path.exists(jd_path):
            with open(jd_path, 'w', encoding='utf-8') as f:
                f.write(jd_text)

        db_df = load_scores()
        processed_resumes = set(db_df.query(f'jd == "{jd_name}"')['resume'])
        current_scores = []

        with st.spinner("Analyzing resumes..."):
            progress = st.progress(0)
            for i, resume_file in enumerate(uploaded_resume_names):
                if resume_file in processed_resumes:
                    continue
                resume_path = os.path.join(RESUME_DIR, resume_file)
                resume_text = extract_text_from_pdf(resume_path)
                sections = extract_sections(resume_text)
                score = weighted_score(sections, jd_text)
                email = extract_email(resume_text)
                current_scores.append({
                    "jd": jd_name,
                    "resume": resume_file,
                    "email": email,
                    "score": score,
                    "timestamp": datetime.now().isoformat()
                })
                progress.progress((i + 1) / len(uploaded_resume_names))
            progress.empty()

        if current_scores:
            new_df = pd.DataFrame(current_scores)
            save_scores_to_db(new_df)
            st.success(f"Scored {len(current_scores)} new resume(s).")
            jd_files = sorted(os.listdir(JD_DIR))
            st.session_state.selected_jd = jd_name  # Update JD dropdown to reflect newly added JD

st.divider()
st.subheader("📈 Resume Analysis Dashboard")

scores_df = load_scores()
filtered = scores_df[scores_df["jd"] == selected_jd].sort_values("score", ascending=False).reset_index(drop=True)

if not filtered.empty:
    st.markdown("### 📄 Analysis Results")
    st.dataframe(filtered[["resume", "email", "score", "timestamp"]], use_container_width=True, height=350)
else:
    st.info("No resume scores found for selected JD.")

st.subheader("🧠 LLM-Powered Summaries")
all_resumes = filtered["resume"].tolist()
summary_key = f"summary_selected_{selected_jd}"
if summary_key not in st.session_state:
    st.session_state[summary_key] = []

selected_rows = st.multiselect("Select resumes to summarize:", all_resumes, default=st.session_state[summary_key])
st.session_state[summary_key] = selected_rows

if selected_rows:
    for resume_name in selected_rows:
        resume_path = os.path.join(RESUME_DIR, resume_name)
        resume_text = extract_text_from_pdf(resume_path)
        jd_text_summary = open(os.path.join(JD_DIR, selected_jd), 'r', encoding='utf-8').read()
        summary = summarize_resume_with_jd(resume_text, jd_text_summary, resume_name, selected_jd)

        with st.container():
            st.markdown(f"""
            <div style='background-color:#1e2230;padding:20px;border-radius:10px;margin-bottom:10px;'>
                <h4 style='color:#a3d3ff;'>{resume_name}</h4>
                <pre style='color:white;background-color:#23283b;border:none;'>{summary}</pre>
            </div>
            """, unsafe_allow_html=True)

st.divider()
csv_all = scores_df.to_csv(index=False).encode('utf-8')
st.download_button("⬇️ Download All Scores", csv_all, "all_jd_resume_scores.csv", "text/csv")

st.subheader("🗑️ Delete JD Records")
jds_to_delete = st.multiselect("Select JD(s) to delete from database and disk:", jd_files)
if st.button("Delete Selected JD(s)"):
    delete_jds(jds_to_delete)
    st.success("Selected JD records and files deleted successfully.")
