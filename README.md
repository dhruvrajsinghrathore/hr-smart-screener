# Smart Resume Analyzer 🎯

A modern web application that analyzes resumes against job descriptions using AI and machine learning. The app uses a combination of BERT embeddings, LLaMA model, and keyword matching to provide comprehensive resume scoring and analysis.

## Features

- Upload multiple resumes (PDF format)
- Upload or paste job descriptions
- Multi-level resume scoring using:
  - BERT semantic similarity (60%)
  - LLaMA 3.2 evaluation (25%)
  - Keyword matching (15%)
- AI-powered candidate fit analysis
- Score history tracking
- Export results to CSV

## Prerequisites

- Python 3.8 or higher
- Git
- Ollama locally available

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/hr-smart-screener.git
cd hr-smart-screener
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Start the Streamlit app:
```bash
streamlit run main_app.py
```

2. Open your browser and navigate to:
```
http://localhost:8501
```

## Usage Guide 📖

1. **Upload Resumes**:
   - Click "Browse files" in the Resume section
   - Select one or more PDF resumes
   - Files will be stored in `uploaded_data/resumes/`

2. **Add Job Description**:
   - Either upload a TXT file or paste the job description
   - Give the JD a title only when you paste the JD in textbox
   - Automatically Saved after you click "Analyze Resumes"

3. **Analyze Resumes**:
   - Click "Analyze Resumes"
   - Wait for the analysis to complete
   - View scores and rankings

4. **View Detailed Analysis**:
   - Select resumes using checkboxes
   - Click "Candidate's Fit Analysis"
   - View AI-generated insights

5. **Export Results**:
   - Click "Export All Scores" to download CSV

## Project Structure

```
hr-smart-screener/
├── main_app.py          # Main Streamlit application
├── scorer.py            # Scoring logic and algorithms
├── summarizer.py        # AI summary generation
├── resume_parser.py     # PDF parsing and text extraction
├── db_utils.py         # Database operations
├── requirements.txt    # Python dependencies
├── .env               # Environment variables
└── uploaded_data/     # Storage for uploads
    ├── resumes/
    ├── jds/
    └── summaries/
```
