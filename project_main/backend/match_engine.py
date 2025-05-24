from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("all-MiniLM-L6-v2")

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
    weights = {
        "skills": 0.1,
        "experience": 0.6,
        "projects": 0.3
    }

    score = 0.0
    for sec, text in resume_sections.items():
        if text.strip() == "":
            continue
        emb = model.encode(text, convert_to_tensor=True)
        sim = util.pytorch_cos_sim(emb, jd_emb).item()
        score += weights.get(sec, 0.0) * sim
    return round(score * 100, 2)

def calculate_score(resume_text, jd_text):
    sections = extract_sections(resume_text)
    score = weighted_score(sections, jd_text)
    return score
