import re
import nltk
from sentence_transformers import SentenceTransformer, util
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
import pandas as pd
import os
from datetime import datetime

# Download required NLTK data
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

# Initialize models
bert_model = SentenceTransformer('all-MiniLM-L6-v2')
llm = ChatOllama(model='llama3.2')

# Common JD section headers to identify relevant parts
JD_HEADERS = [
    "required qualifications", "preferred qualifications", "skills needed", "you will",
    "job responsibilities", "minimum requirements", "what you'll work on", "what you bring",
    "bonus point for", "key responsibilities", "requirements", "what you'll do",
    "nice to have", "about you", "the following", "qualifications", "responsibilities",
    "about the role", "your role", "essential skills", "desired skills"
]

# Section headers & base weights (updated weights)
SECTION_MAP = {
    "skills": ["skills", "technical skills", "skill set"],
    "experience": ["experience", "professional experience", "technical experience", "work experience"],
    "projects": ["projects", "academic projects", "personal projects"]
}

BASE_WEIGHTS = {
    "skills": 0.10,
    "experience": 0.50,  # Reduced from 0.60
    "projects": 0.30,    # Increased from 0.20
    "other": 0.10
}

# Combined stopwords from NLTK and scikit-learn
STOPWORDS = set(stopwords.words('english')).union(ENGLISH_STOP_WORDS)

def preprocess_jd(text):
    """Extract relevant sections from job description for better scoring."""
    lines = text.splitlines()
    relevant_sections = []
    collecting = False
    current_section = []
    
    for line in lines:
        line = line.strip()
        if not line:
            if collecting and current_section:
                relevant_sections.extend(current_section)
                current_section = []
            continue
            
        line_lower = line.lower()
        
        # Check if this line starts a relevant section
        if any(header in line_lower for header in JD_HEADERS):
            if collecting and current_section:
                relevant_sections.extend(current_section)
            collecting = True
            current_section = [line]
            continue
            
        # If we're collecting and line seems to be a new major section (all caps),
        # stop collecting unless it's a known header
        if collecting and line.isupper() and not any(header in line_lower for header in JD_HEADERS):
            collecting = False
            if current_section:
                relevant_sections.extend(current_section)
                current_section = []
            continue
            
        if collecting:
            current_section.append(line)
    
    # Add any remaining section
    if collecting and current_section:
        relevant_sections.extend(current_section)
    
    processed_text = "\n".join(relevant_sections)
    return processed_text if processed_text.strip() else text  # Return original if no sections found

def clean_line(line):
    """Clean and normalize text line."""
    return re.sub(r'[^A-Za-z0-9\s]', '', line).strip().lower()

def extract_sections(text):
    """Extract sections from resume text with improved section detection."""
    sections = {k: "" for k in BASE_WEIGHTS}
    current = "other"
    
    for raw in text.splitlines():
        line = clean_line(raw)
        if not line:
            continue
        for key, aliases in SECTION_MAP.items():
            if any(alias in line for alias in aliases):
                current = key
                break
        sections[current] += raw + " "
    return sections

def keyword_overlap(jd_text, resume_text):
    """Calculate keyword overlap score between JD and resume."""
    jd_kw = {w for w in re.findall(r'\w+', jd_text.lower()) if w not in STOPWORDS}
    resume_kw = {w for w in re.findall(r'\w+', resume_text.lower()) if w not in STOPWORDS}
    return len(jd_kw & resume_kw) / max(len(jd_kw), 1)

def extract_job_role(jd_text):
    """Extract job role from JD text."""
    # Common position title patterns
    role_patterns = [
        r"([A-Za-z\s]+(?:Engineer|Developer|Scientist|Analyst|Manager|Designer|Architect|Intern|Associate|Lead|Director|Consultant)(?:\s*[A-Za-z\s]*)?)\s*(?:\(|$)",
        r"(?:Position|Role|Title|Job)[:]*\s*([A-Za-z\s]+)",
        r"([A-Za-z\s]+)\s+Position",
    ]
    
    # Try each pattern
    for pattern in role_patterns:
        matches = re.finditer(pattern, jd_text, re.IGNORECASE)
        for match in matches:
            role = match.group(1).strip()
            if 3 <= len(role.split()) <= 6:  # Reasonable title length
                return role
    
    return "this position"  # Fallback if no role found

def llama_similarity(jd_text, sections, job_role):
    """Get LLaMA's evaluation of resume relevance."""
    # Combine relevant sections with clear separation
    resume_text = (
        f"Skills:\n{sections.get('skills', '')}\n\n"
        f"Experience:\n{sections.get('experience', '')}\n\n"
        f"Projects:\n{sections.get('projects', '')}"
    )
    
    if not any(sections.get(k, '').strip() for k in ['skills', 'experience', 'projects']):
        print("Warning: All relevant sections are empty")
        return 0.1
        
    prompt = f"""You are a technical hiring assistant evaluating a candidate for {job_role}.
Based on the candidate's skills, experience, and projects, rate their relevance to the job requirements on a scale of 0-1.
Focus on technical skills alignment and potential to learn required technologies.
Respond with ONLY a number between 0 and 1.

Job Requirements:
{jd_text}

Candidate Information:
{resume_text}
"""
    
    try:
        reply = llm.invoke([HumanMessage(content=prompt)]).content.strip()
        print(f"DEBUG - Job Role: {job_role}")
        print(f"DEBUG - LLaMA raw response: {reply}")
        
        # First try: Look for a decimal between 0 and 1
        match = re.search(r"(?:0?\.\d+|1(?:\.0+)?)", reply)
        if match:
            score = float(match.group())
            print(f"DEBUG - Decimal match found: {score}")
            return score
            
        # Second try: Look for a percentage (0-100)
        match = re.search(r"(\d{1,3})(?:\.\d+)?%?", reply)
        if match:
            score = float(match.group(1))
            score = score / 100 if score > 1 else score
            print(f"DEBUG - Percentage match found: {score}")
            return score
            
        # Third try: Look for words that indicate score ranges
        low_indicators = ['low', 'poor', 'weak', 'minimal', 'limited', 'not relevant', 'irrelevant']
        med_indicators = ['moderate', 'fair', 'average', 'medium', 'partial', 'somewhat']
        high_indicators = ['high', 'strong', 'excellent', 'perfect', 'great', 'very relevant', 'highly']
        
        reply_lower = reply.lower()
        
        # Check for explicit negative statements
        if any(phrase in reply_lower for phrase in ['not relevant', 'irrelevant', 'no match']):
            print("DEBUG - Found explicit negative statement")
            return 0.1
            
        if any(word in reply_lower for word in high_indicators):
            print("DEBUG - High relevance words found")
            return 0.8
        elif any(word in reply_lower for word in med_indicators):
            print("DEBUG - Medium relevance words found")
            return 0.5
        elif any(word in reply_lower for word in low_indicators):
            print("DEBUG - Low relevance words found")
            return 0.2
            
        # If all else fails, do basic text analysis
        if len(reply.strip()) < 5:  # Very short or empty response
            print("DEBUG - Very short response, using fallback")
            return 0.1
            
        # Count any numbers in the text as a last resort
        numbers = re.findall(r'\d+', reply)
        if numbers:
            # Take the first number found and normalize it
            score = float(numbers[0])
            score = score / 100 if score > 1 else score
            print(f"DEBUG - Found number in text: {score}")
            return min(max(score, 0.1), 1.0)  # Clamp between 0.1 and 1.0
            
        print(f"WARNING - Could not extract score from LLaMA response: {reply}")
        return 0.1  # Minimum score as fallback
        
    except Exception as e:
        print(f"ERROR - LLaMA scoring error: {str(e)}")
        if "connection" in str(e).lower():
            print("WARNING - Possible connection issue with LLaMA")
        return 0.1  # Return minimum score instead of 0

def dynamic_weights(sections):
    """Adjust weights based on section content."""
    w = BASE_WEIGHTS.copy()
    has_exp = sections["experience"].strip() != ""
    has_prj = sections["projects"].strip() != ""
    
    if not has_exp and has_prj:  # move experience weight to projects
        w["projects"] += w["experience"]
        w["experience"] = 0.0
    elif has_exp and not has_prj:  # move projects weight to experience
        w["experience"] += w["projects"]
        w["projects"] = 0.0
    return w

def weighted_score(sections, jd_text):
    """Calculate final weighted score combining BERT, LLaMA, and keyword overlap."""
    # Extract job role from raw JD first
    job_role = extract_job_role(jd_text)
    
    # Preprocess JD text
    processed_jd = preprocess_jd(jd_text)
    
    # BERT section scoring
    weights = dynamic_weights(sections)
    jd_emb = bert_model.encode(processed_jd, convert_to_tensor=True)
    bert_total = 0.0
    
    for sec, text in sections.items():
        if not text.strip() or weights[sec] == 0:
            continue
        emb = bert_model.encode(text, convert_to_tensor=True)
        sim = util.pytorch_cos_sim(emb, jd_emb).item()
        bert_total += weights[sec] * sim

    # Keyword overlap scoring
    full_text = " ".join(sections.values())
    kw_overlap = keyword_overlap(processed_jd, full_text)

    # LLaMA scoring - now passing all sections and job role
    llama_score = llama_similarity(processed_jd, sections, job_role)

    # Final weighted combination
    final_score = (
        0.60 * bert_total +  # BERT semantic similarity
        0.25 * llama_score + # LLaMA evaluation
        0.15 * kw_overlap    # Keyword overlap
    )

    # Return all scores
    scores = {
        "bert_score": round(bert_total * 100, 2),
        "llama_score": round(llama_score * 100, 2),
        "keyword_overlap": round(kw_overlap * 100, 2),
        "final_score": round(final_score * 100, 2)
    }
    
    return scores

def save_detailed_scores(jd_name, resume_name, scores):
    """Save detailed scoring information to CSV."""
    csv_file = "scoring_analysis.csv"
    
    # Prepare the data
    data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "jd_name": jd_name,
        "resume_name": resume_name,
        "bert_score": scores["bert_score"],
        "llama_score": scores["llama_score"],
        "keyword_overlap": scores["keyword_overlap"],
        "final_score": scores["final_score"]
    }
    
    # Create or append to CSV
    df = pd.DataFrame([data])
    if os.path.exists(csv_file):
        df.to_csv(csv_file, mode='a', header=False, index=False)
    else:
        df.to_csv(csv_file, index=False)
