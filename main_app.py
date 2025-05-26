import os
import pandas as pd
from datetime import datetime
import streamlit as st
from resume_parser import extract_text_from_pdf, extract_sections, extract_email
from scorer import weighted_score, save_detailed_scores, preprocess_jd
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

st.set_page_config(
    page_title="Smart Resume Analyzer",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern UI
css = '''
<style>
    /* Main theme colors */
    :root {
        --primary-color: #4f46e5;
        --secondary-color: #818cf8;
        --background-color: #0f172a;
        --surface-color: #1e293b;
        --surface-color-light: #243147;
        --text-color: #f8fafc;
        --muted-text: #94a3b8;
        --success-color: #22c55e;
        --warning-color: #f59e0b;
        --error-color: #ef4444;
    }

    /* Global styles */
    .stApp {
        background-color: var(--background-color);
        color: var(--text-color);
    }

    .block-container {
        padding-top: 1rem !important;
    }

    /* Typography */
    h1, h2, h3 {
        color: var(--text-color);
        font-family: 'Inter', sans-serif;
        font-weight: 600;
    }

    /* Main heading */
    .main-heading {
        font-size: 2.5rem;
        text-align: center;
        margin: 1rem 0 2rem;
        color: var(--text-color);
        font-weight: 700;
        letter-spacing: -0.025em;
        line-height: 1.25;
    }

    .main-heading span {
        background: linear-gradient(120deg, #818cf8, #4f46e5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding: 0 0.5rem;
    }

    /* Cards */
    .stCard {
        background-color: var(--surface-color);
        border-radius: 1rem;
        padding: 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        margin-bottom: 1.5rem;
    }

    /* Completely reset and override Browse files button styling */
    button[data-testid="baseButton-secondary"],
    [data-testid="stFileUploader"] button[class*="css"],
    [data-testid="stFileUploader"] button,
    button[title="Browse files"],
    div[class*="stFileUploader"] button,
    div[class*="uploadButton"] button {
        background: linear-gradient(90deg, #818cf8, #4f46e5) !important;
        background-color: #818cf8 !important;
        border: none !important;
        color: white !important;
        font-weight: 500 !important;
        transition: all 0.2s !important;
        opacity: 1 !important;
        box-shadow: none !important;
        padding: 0.25rem 0.75rem !important;
        border-radius: 0.375rem !important;
    }

    button[data-testid="baseButton-secondary"]:hover,
    [data-testid="stFileUploader"] button[class*="css"]:hover,
    [data-testid="stFileUploader"] button:hover,
    button[title="Browse files"]:hover,
    div[class*="stFileUploader"] button:hover,
    div[class*="uploadButton"] button:hover {
        background: linear-gradient(90deg, #4f46e5, #818cf8) !important;
        background-color: #4f46e5 !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
    }

    /* Remove any default Streamlit button styles */
    [data-testid="stFileUploader"] button[class*="css"]::before,
    [data-testid="stFileUploader"] button[class*="css"]::after,
    div[class*="stFileUploader"] button::before,
    div[class*="stFileUploader"] button::after {
        display: none !important;
        content: none !important;
        background: none !important;
    }

    /* File uploader area styling */
    [data-testid="stFileUploader"] {
        background-color: var(--surface-color-light);
        border-radius: 0.5rem;
        padding: 1rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }

    [data-testid="stFileUploader"] > div > div {
        background-color: var(--surface-color);
        border: 1px dashed rgba(255, 255, 255, 0.2);
        color: var(--muted-text);
    }

    /* Text area styling */
    .stTextArea textarea {
        background-color: var(--surface-color-light) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: var(--text-color) !important;
    }

    /* Selectbox styling */
    .stSelectbox > div[data-baseweb="select"] > div {
        background-color: var(--surface-color-light) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }

    /* Score bar styling */
    [data-testid="stDataFrameCell"] div[data-testid="stProgressBar"] {
        min-width: 100px;
    }

    [data-testid="stDataFrameCell"] div[data-testid="stProgressBar"] > div {
        background-color: rgba(129, 140, 248, 0.1) !important;
    }

    [data-testid="stDataFrameCell"] div[data-testid="stProgressBar"] > div > div {
        background: linear-gradient(90deg, #818cf8, #4f46e5) !important;
        transition: width 0.3s ease-in-out;
    }

    /* Table cell styling */
    [data-testid="stDataFrameCell"] {
        background-color: var(--surface-color-light) !important;
    }

    /* Selected JD text area */
    div[data-baseweb="textarea"] {
        background-color: var(--surface-color-light) !important;
    }

    textarea[aria-label=""] {
        background-color: var(--surface-color-light) !important;
        color: var(--text-color) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }

    /* Multiselect styling */
    .stMultiSelect > div[data-baseweb="select"] {
        background-color: var(--surface-color-light);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }

    .stMultiSelect [role="option"] {
        background-color: var(--surface-color-light);
    }

    .stMultiSelect [role="option"]:hover {
        background-color: rgba(129, 140, 248, 0.1) !important;
    }

    /* Table header styling */
    [data-testid="stDataFrameCell"]:first-child {
        background-color: var(--surface-color) !important;
    }

    /* Checkbox styling */
    [data-testid="stCheckbox"] > div > div > div {
        background-color: var(--surface-color-light) !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
    }

    [data-testid="stCheckbox"] > div > div > div:hover {
        border-color: var(--secondary-color) !important;
    }

    /* Button styling - making all buttons consistent */
    button[kind="primary"],
    button[kind="secondary"],
    .stButton button,
    .stDownloadButton button {
        background: linear-gradient(90deg, #818cf8, #4f46e5) !important;
        border: none !important;
        color: white !important;
        font-weight: 500 !important;
        transition: all 0.2s !important;
        opacity: 1 !important;
        box-shadow: none !important;
        padding: 0.25rem 0.75rem !important;
        border-radius: 0.375rem !important;
    }

    button[kind="primary"]:hover,
    button[kind="secondary"]:hover,
    .stButton button:hover,
    .stDownloadButton button:hover {
        background: linear-gradient(90deg, #4f46e5, #818cf8) !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
        color: white !important;
        border: none !important;
    }

    /* Remove any old button styles */
    .primary-button button,
    .delete-button button,
    .success-button button {
        background: linear-gradient(90deg, #818cf8, #4f46e5) !important;
    }

    .primary-button button:hover,
    .delete-button button:hover,
    .success-button button:hover {
        background: linear-gradient(90deg, #4f46e5, #818cf8) !important;
    }

    /* Progress bars */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #818cf8, #4f46e5);
    }

    /* Data editor */
    [data-testid="stDataFrameCell"] {
        background-color: var(--surface-color);
        color: var(--text-color);
    }

    [data-testid="stDataFrameCell"] progress {
        background: linear-gradient(90deg, #818cf8, #4f46e5);
    }

    /* Summary cards */
    .summary-card {
        background-color: var(--surface-color);
        border-radius: 1rem;
        padding: 2rem;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    .summary-header {
        color: var(--secondary-color);
        font-size: 1.3rem;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .score-container {
        background: linear-gradient(90deg, 
            rgba(129, 140, 248, 0.1) 0%,
            rgba(79, 70, 229, 0.1) 100%) !important;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
    }

    .score-bar {
        height: 8px;
        background: linear-gradient(90deg, #818cf8, #4f46e5) !important;
        border-radius: 4px;
        transition: width 0.5s ease-in-out;
    }

    /* Table styles */
    [data-testid="stTable"] {
        background-color: var(--surface-color);
        border-radius: 0.5rem;
        overflow: hidden;
    }

    .table-actions {
        display: flex;
        justify-content: flex-end;
        gap: 1rem;
        margin-bottom: 1rem;
    }

    /* Selected Job Description Box */
    .selected-jd-box {
        background-color: var(--surface-color-light);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 0.5rem;
        padding: 1.5rem;
        margin: 1rem 0;
    }

    .selected-jd-box h4 {
        color: var(--text-color);
        margin-bottom: 1rem;
        font-size: 1.1rem;
        font-weight: 500;
    }

    /* Hide the empty box */
    [data-testid="stExpander"] {
        display: none !important;
    }

    /* Update the column configuration for the Match Score column */
    column_config={
        "Select": st.column_config.CheckboxColumn(
            "Select",
            help="Select resume for summarization",
            default=False,
            width="small"
        ),
        "resume": st.column_config.TextColumn(
            "Resume",
            help="Resume filename"
        ),
        "email": st.column_config.TextColumn(
            "Email",
            help="Candidate's email address"
        ),
        "score": st.column_config.TextColumn(
            "Match Score",
            help="Overall match score",
            width="medium",
            default=lambda x: f"""
                <div style="min-width: 100px;">
                    <div class="custom-progress-container">
                        <div class="custom-progress-bar" style="width: {x}%;"></div>
                    </div>
                    <div style="text-align: right; font-size: 0.9em; margin-top: 4px;">{x:.2f}%</div>
                </div>
            """
        ),
        "timestamp": st.column_config.DatetimeColumn(
            "Analyzed At",
            help="When the resume was analyzed"
        )
    }

    /* Match Score progress bar styling */
    div[data-testid="stDataFrameCell"] div.stProgress > div > div > div {
        background: linear-gradient(90deg, #818cf8, #4f46e5) !important;
    }

    div[data-testid="stDataFrameCell"] div.stProgress > div {
        background-color: rgba(129, 140, 248, 0.1) !important;
    }

    /* Ensure no other styles override our progress bar */
    div[data-testid="stDataFrameCell"] div[role="progressbar"] > div {
        background: linear-gradient(90deg, #818cf8, #4f46e5) !important;
    }

    /* Additional progress bar styling */
    .element-container div[data-testid="stDataFrameCell"] div[role="progressbar"] > div {
        background: linear-gradient(90deg, #818cf8, #4f46e5) !important;
    }

    /* Force progress bar color */
    div[data-testid="stDataFrameCell"] div[class*="Progress"] > div > div {
        background: linear-gradient(90deg, #818cf8, #4f46e5) !important;
    }

    /* Custom progress bar styling */
    .custom-progress-container {
        width: 100%;
        background-color: rgba(129, 140, 248, 0.1);
        border-radius: 4px;
        overflow: hidden;
    }

    .custom-progress-bar {
        height: 8px;
        background: linear-gradient(90deg, #818cf8, #4f46e5);
        transition: width 0.3s ease;
    }

    /* File uploader cross button and pagination styling */
    [data-testid="stFileUploader"] button[data-testid="stFileUploadedDownloadButton"] {
        padding: 0.25rem !important;
        height: 24px !important;
        width: 24px !important;
        min-height: 24px !important;
        min-width: 24px !important;
    }

    [data-testid="stFileUploader"] button[data-testid="stFileUploadedDownloadButton"] svg {
        height: 16px !important;
        width: 16px !important;
    }

    /* Pagination arrows */
    [data-testid="stFileUploader"] button[aria-label="Previous page"],
    [data-testid="stFileUploader"] button[aria-label="Next page"] {
        padding: 0.25rem !important;
        height: 24px !important;
        width: 24px !important;
        min-height: 24px !important;
        min-width: 24px !important;
    }

    [data-testid="stFileUploader"] button[aria-label="Previous page"] svg,
    [data-testid="stFileUploader"] button[aria-label="Next page"] svg {
        height: 16px !important;
        width: 16px !important;
    }
</style>
'''

st.markdown(css, unsafe_allow_html=True)

# App Header with enhanced visibility
st.markdown("""
<h1 class="main-heading">🎯 <span>Smart Resume Analyzer</span></h1>
""", unsafe_allow_html=True)

# Main content area with two columns
left_col, right_col = st.columns([3, 2])

with left_col:
    st.markdown("""
    <div class="stCard">
        <h3>📥 Resume</h3>
    """, unsafe_allow_html=True)
    
    uploaded_resumes = st.file_uploader(
        "Upload Resume(s)",
        type=["pdf"],
        accept_multiple_files=True,
        help="Upload one or more resumes in PDF format"
    )

    st.markdown("</div>", unsafe_allow_html=True)

with right_col:
    st.markdown("""
    <div class="stCard">
        <h3>📋 Job Description</h3>
    """, unsafe_allow_html=True)
    
    uploaded_jd = st.file_uploader(
        "Upload JD",
        type=["txt"],
        help="Upload a job description in TXT format"
    )
    
    jd_text_input = st.text_area(
        "Or paste JD below:",
        height=150,
        help="Paste the job description text here if not uploading a file"
    )
    
    jd_name_input = st.text_input(
        "JD Title",
        max_chars=100,
        help="Give this job description a title for reference"
    )

    st.markdown("</div>", unsafe_allow_html=True)

# JD Selection
jd_files = sorted(os.listdir(JD_DIR))

if "selected_jd" not in st.session_state:
    st.session_state.selected_jd = jd_files[0] if jd_files else ""

st.markdown("""
<div class="stCard">
    <h3>📊 Analysis Dashboard</h3>
""", unsafe_allow_html=True)

selected_jd = st.selectbox(
    "Select Job Description",
    jd_files,
    index=jd_files.index(st.session_state.selected_jd) if st.session_state.selected_jd in jd_files else 0,
    help="Choose a job description to analyze resumes against"
)

if selected_jd:
    with open(os.path.join(JD_DIR, selected_jd), 'r', encoding='utf-8') as f:
        jd_text = f.read()
    st.text_area("", jd_text, height=200, disabled=True)

st.markdown("</div>", unsafe_allow_html=True)

# Process uploaded files
uploaded_resume_names = []
if uploaded_resumes:
    for file in uploaded_resumes:
        resume_path = os.path.join(RESUME_DIR, file.name)
        uploaded_resume_names.append(file.name)
        with open(resume_path, 'wb') as f:
            f.write(file.read())

# Analysis Button
st.markdown('<div class="primary-button">', unsafe_allow_html=True)
if st.button("🔍 Analyze Resumes", help="Start analyzing the selected resumes"):
    jd_name = ""
    jd_text = ""
    
    # Determine JD source
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
        # Save JD if new
        jd_path = os.path.join(JD_DIR, jd_name)
        if not os.path.exists(jd_path):
            with open(jd_path, 'w', encoding='utf-8') as f:
                f.write(jd_text)
            jd_files = sorted(os.listdir(JD_DIR))

        # Process resumes
        db_df = load_scores()
        processed_resumes = set(db_df.query(f'jd == "{jd_name}"')['resume'])
        current_scores = []

        with st.spinner("📊 Analyzing resumes..."):
            progress = st.progress(0)
            for i, resume_file in enumerate(uploaded_resume_names):
                if resume_file in processed_resumes:
                    continue
                    
                resume_path = os.path.join(RESUME_DIR, resume_file)
                resume_text = extract_text_from_pdf(resume_path)
                sections = extract_sections(resume_text)
                scores = weighted_score(sections, jd_text)
                email = extract_email(resume_text)
                
                save_detailed_scores(jd_name, resume_file, scores)
                
                current_scores.append({
                    "jd": jd_name,
                    "resume": resume_file,
                    "email": email,
                    "score": scores["final_score"],
                    "timestamp": datetime.now().isoformat()
                })
                
                progress.progress((i + 1) / len(uploaded_resume_names))
            progress.empty()

        if current_scores:
            new_df = pd.DataFrame(current_scores)
            save_scores_to_db(new_df)
            st.success(f"✅ Successfully scored {len(current_scores)} new resume(s)!")
            st.session_state.selected_jd = jd_name
            st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# Results Display
st.markdown("""
<div class="stCard">
    <h3>📈 Analysis Results</h3>
""", unsafe_allow_html=True)

scores_df = load_scores()
filtered = scores_df[scores_df["jd"] == selected_jd].sort_values("score", ascending=False).reset_index(drop=True)

if not filtered.empty:
    delete_button = st.button("🗑️ Delete Resume", help="Delete selected resumes")
    
    # Create selection column
    filtered_display = filtered.copy()
    filtered_display.insert(0, 'Select', False)
    
    # Enhanced data editor
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
            "resume": st.column_config.TextColumn(
                "Resume",
                help="Resume filename"
            ),
            "email": st.column_config.TextColumn(
                "Email",
                help="Candidate's email address"
            ),
            "score": st.column_config.ProgressColumn(
                "Match Score",
                help="Overall match score",
                format="%.2f%%",
                min_value=0,
                max_value=100,
                width="medium"
            ),
            "timestamp": st.column_config.DatetimeColumn(
                "Analyzed At",
                help="When the resume was analyzed"
            )
        },
        use_container_width=True,
        height=350
    )

    if delete_button:
        selected_to_delete = edited_df[edited_df['Select']]['resume'].tolist()
        if selected_to_delete:
            if st.session_state.summaries:
                st.session_state.summaries = [(resume, summary) for resume, summary in st.session_state.summaries 
                                            if resume not in selected_to_delete]
                if not st.session_state.summaries:
                    st.session_state.current_summary_jd = None
                    
            delete_resumes(selected_jd, selected_to_delete)
            st.success(f"🗑️ Deleted {len(selected_to_delete)} resume(s) from database.")
            st.rerun()
        else:
            st.warning("⚠️ Please select resumes to delete.")
else:
    st.info("ℹ️ No resumes analyzed yet for the selected job description.")

st.markdown("</div>", unsafe_allow_html=True)

# LLM Summaries Section
st.markdown("""
<div class="stCard">
    <h3>🧠 AI-Powered Insights</h3>
""", unsafe_allow_html=True)

# Initialize session state
if "summaries" not in st.session_state:
    st.session_state.summaries = []
if "current_summary_jd" not in st.session_state:
    st.session_state.current_summary_jd = None

# Summary controls
col1, col2 = st.columns([3, 1])
with col1:
    generate_button = st.button("📝 Candidate's Fit Analysis", help="Generate AI-powered analysis for selected resumes")
with col2:
    if st.button("🗑️ Clear All Summaries", help="Clear all cached summaries"):
        clear_summaries()
        st.session_state.summaries = []
        st.session_state.current_summary_jd = None
        st.success("🧹 Cleared all cached summaries!")

# Initialize selected_resumes
selected_resumes = []
if 'edited_df' in locals() and not filtered.empty:
    selected_resumes = edited_df[edited_df['Select']]['resume'].tolist()

# Clear summaries if JD changed
if st.session_state.current_summary_jd is not None and st.session_state.current_summary_jd != selected_jd:
    st.session_state.summaries = []
    st.session_state.current_summary_jd = None

if generate_button:
    if not selected_resumes:
        st.warning("⚠️ Please select at least one resume to analyze.")
    else:
        with st.spinner(f"🤖 Generating analysis for {len(selected_resumes)} resume(s)..."):
            resume_texts = []
            for resume_name in selected_resumes:
                resume_path = os.path.join(RESUME_DIR, resume_name)
                resume_text = extract_text_from_pdf(resume_path)
                resume_texts.append(resume_text)
            
            raw_jd_text = open(os.path.join(JD_DIR, selected_jd), 'r', encoding='utf-8').read()
            processed_jd = preprocess_jd(raw_jd_text)
            
            st.session_state.summaries = summarize_resumes_with_jd(resume_texts, processed_jd, selected_resumes, selected_jd)
            st.session_state.current_summary_jd = selected_jd

# Display summaries
if st.session_state.summaries:
    for resume_name, summary in st.session_state.summaries:
        formatted_summary = summary.strip().replace("\n", "<br>")  # Replace newlines with HTML breaks
        st.markdown(f"""
        <div class="summary-card">
            <div class="summary-header">
                <span>📄</span> {resume_name}
            </div>
            <div class="summary-content">
                {formatted_summary}
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# Footer with export option
st.divider()
csv_all = scores_df.to_csv(index=False).encode('utf-8')
st.download_button(
    "⬇️ Export All Scores",
    csv_all,
    "resume_analysis_scores.csv",
    "text/csv",
    help="Download all analysis scores as CSV"
)

# Admin section for JD management
st.markdown("""
<div class="stCard">
    <h3>⚙️ Job Description Management</h3>
""", unsafe_allow_html=True)

jds_to_delete = st.multiselect(
    "Select Job Description(s) to Delete:",
    jd_files,
    help="Select one or more job descriptions to remove from the system"
)

if st.button("🗑️ Delete JD(s)") and jds_to_delete:
    if st.session_state.current_summary_jd in jds_to_delete:
        st.session_state.summaries = []
        st.session_state.current_summary_jd = None
    delete_jds(jds_to_delete)
    if st.session_state.selected_jd in jds_to_delete:
        st.session_state.selected_jd = ""
    st.rerun()

st.markdown("</div>", unsafe_allow_html=True)
