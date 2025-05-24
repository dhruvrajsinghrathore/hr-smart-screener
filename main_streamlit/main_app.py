import os
import pandas as pd
from datetime import datetime
import streamlit as st
from resume_parser import extract_text_from_pdf, extract_sections, extract_email
from scorer import weighted_score
from summarizer import summarize_resume_with_jd, summarize_resumes_with_jd, clear_summaries
from db_utils import init_db, load_scores, save_scores_to_db, delete_jds, delete_resumes

UPLOAD_DIR = "uploaded_data"
JD_DIR = os.path.join(UPLOAD_DIR, "jds")
RESUME_DIR = os.path.join(UPLOAD_DIR, "resumes")
SUMMARY_DIR = os.path.join(UPLOAD_DIR, "summaries")

os.makedirs(JD_DIR, exist_ok=True)
os.makedirs(RESUME_DIR, exist_ok=True)
os.makedirs(SUMMARY_DIR, exist_ok=True)

init_db()

st.set_page_config(page_title="Resume Analyzer Pro", layout="wide", initial_sidebar_state="expanded")

# Add theme configuration
st.markdown("""
    <style>
        /* Progress bar color */
        .stProgress > div > div > div > div {
            background-color: #4f46e5;
        }
        
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
            text-align: left;
        }
        /* Style for the progress bars in the data editor */
        [data-testid="stDataFrameCell"] progress::-webkit-progress-value {
            background-color: #4f46e5 !important;
        }
        [data-testid="stDataFrameCell"] progress {
            color: #4f46e5 !important;
        }
        [data-testid="stDataFrameCell"] progress::-moz-progress-bar {
            background-color: #4f46e5 !important;
        }
        .bar-container {
            width: 100%;
            background-color: #333;
            border-radius: 4px;
            height: 8px;
            margin-top: 4px;
        }
        .bar-fill {
            height: 8px;
            border-radius: 4px;
            background-color: #4f46e5;
            transition: width 0.5s ease-in-out;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1> Resume Analyzer Pro</h1>", unsafe_allow_html=True)

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
            # Update jd_files list immediately after saving new JD
            jd_files = sorted(os.listdir(JD_DIR))

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
            # Update session state and force selectbox to show new JD
            st.session_state.selected_jd = jd_name
            st.rerun()

st.divider()
st.subheader("📈 Resume Analysis Dashboard")

scores_df = load_scores()
filtered = scores_df[scores_df["jd"] == selected_jd].sort_values("score", ascending=False).reset_index(drop=True)

if not filtered.empty:
    st.markdown("### 📄 Analysis Results")
    
    # Add delete button above the table
    col1, col2, col3 = st.columns([6, 2, 2])
    with col2:
        delete_button = st.button("🗑️ Delete Selected", type="secondary", use_container_width=True)
    
    # Create the selection column directly in the dataframe
    filtered_display = filtered.copy()
    filtered_display.insert(0, 'Select', False)
    
    # Use data_editor instead of dataframe for interactive checkboxes
    edited_df = st.data_editor(
        filtered_display,
        disabled=["resume", "email", "score", "timestamp"],
        hide_index=True,
        column_config={
            "Select": st.column_config.CheckboxColumn(
                "Select",
                help="Select resume for summarization",
                default=False,
                width="small"
            ),
            "resume": st.column_config.TextColumn("Resume"),
            "email": st.column_config.TextColumn(
                "Email",
                help="Click to copy email address"
            ),
            "score": st.column_config.ProgressColumn(
                "Score",
                help="Match score",
                format="%.2f",
                min_value=0,
                max_value=100,
                width="medium"
            ),
            "timestamp": st.column_config.TextColumn("Timestamp")
        },
        use_container_width=True,
        height=350
    )
    
    if delete_button:
        selected_to_delete = edited_df[edited_df['Select']]['resume'].tolist()
        if selected_to_delete:
            # Remove summaries for deleted resumes
            if st.session_state.summaries:
                st.session_state.summaries = [(resume, summary) for resume, summary in st.session_state.summaries 
                                            if resume not in selected_to_delete]
                # If all summaries are deleted, clear the current JD reference
                if not st.session_state.summaries:
                    st.session_state.current_summary_jd = None
                    
            delete_resumes(selected_jd, selected_to_delete)
            st.success(f"Deleted {len(selected_to_delete)} resume(s) from database.")
            st.rerun()
        else:
            st.warning("Please select resumes to delete.")
else:
    st.info("No resumes analyzed yet for the selected job description.")

st.subheader("🧠 LLM-Powered Summaries")

# Initialize session state for summaries if not exists
if "summaries" not in st.session_state:
    st.session_state.summaries = []
if "current_summary_jd" not in st.session_state:
    st.session_state.current_summary_jd = None

# Add clear summaries button
col1, col2 = st.columns([3, 1])
with col1:
    generate_button = st.button("Generate Summaries for Selected Resumes")
with col2:
    if st.button("🗑️ Clear Cached Summaries"):
        clear_summaries()
        st.session_state.summaries = []
        st.session_state.current_summary_jd = None
        st.success("Cleared all cached summaries!")

# Initialize selected_resumes as empty list if no resumes are loaded
selected_resumes = []
if 'edited_df' in locals() and not filtered.empty:
    selected_resumes = edited_df[edited_df['Select']]['resume'].tolist()

# Clear summaries if JD changed
if st.session_state.current_summary_jd is not None and st.session_state.current_summary_jd != selected_jd:
    st.session_state.summaries = []
    st.session_state.current_summary_jd = None

if generate_button:
    if not selected_resumes:
        st.warning("Please select at least one resume to summarize.")
    else:
        with st.spinner(f"Generating summaries for {len(selected_resumes)} resumes..."):
            resume_texts = []
            for resume_name in selected_resumes:
                resume_path = os.path.join(RESUME_DIR, resume_name)
                resume_text = extract_text_from_pdf(resume_path)
                resume_texts.append(resume_text)
            
            jd_text = open(os.path.join(JD_DIR, selected_jd), 'r', encoding='utf-8').read()
            st.session_state.summaries = summarize_resumes_with_jd(resume_texts, jd_text, selected_resumes, selected_jd)
            st.session_state.current_summary_jd = selected_jd

# Display summaries if they exist
if st.session_state.summaries:
    for resume_name, summary in st.session_state.summaries:
        with st.container():
            st.markdown(f"""
            <div style='background-color:#1e2230;padding:24px;border-radius:12px;margin-bottom:20px;'>
                <h4 style='color:#a3d3ff;margin-bottom:20px;font-size:1.3em;'>
                    <span style='margin-right:10px;'>📄</span>{resume_name}
                </h4>
                <div style='background-color:#23283b;padding:24px;border-radius:8px;'>
                    <div style='font-family:"Courier New", monospace;color:#e6e6e6;white-space:pre-wrap;line-height:1.8;font-size:1.05em;'>
                        {summary.strip()}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Add a subtle divider between summaries
            if resume_name != st.session_state.summaries[-1][0]:  # Don't add divider after last summary
                st.markdown("<hr style='border:none;border-top:1px solid #2d3747;margin:35px 0;'>", unsafe_allow_html=True)

st.divider()
csv_all = scores_df.to_csv(index=False).encode('utf-8')
st.download_button("⬇️ Download All Scores", csv_all, "all_jd_resume_scores.csv", "text/csv")

st.subheader("🗑️ Delete JD Records")
jds_to_delete = st.multiselect("Select JD(s) to delete from database and disk:", jd_files)
if st.button("Delete Selected JD(s)") and jds_to_delete:
    # Clear summaries if the current JD is being deleted
    if st.session_state.current_summary_jd in jds_to_delete:
        st.session_state.summaries = []
        st.session_state.current_summary_jd = None
    delete_jds(jds_to_delete)
    # Clear the selected JD if it was deleted
    if st.session_state.selected_jd in jds_to_delete:
        st.session_state.selected_jd = ""
    # Force refresh of the page to update all JD lists
    st.rerun()
