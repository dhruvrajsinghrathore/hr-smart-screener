from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer('all-MiniLM-L6-v2')

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
