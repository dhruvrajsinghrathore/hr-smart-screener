import ollama
from math import ceil

def summarize_resume_with_jd(jd_text, resume_batch):
    batch_prompts = ""
    for idx, resume_text in enumerate(resume_batch, start=1):
        batch_prompts += f"\nResume {idx}:\n\"\"\"{resume_text}\"\"\"\n"

    prompt = f"""
You are an AI assistant helping recruiters evaluate candidates by comparing their resumes with a job description. For each resume, provide:

1. A 40-word summary of how the resume aligns with the JD.
2. A bullet list of 5 key relevant skills.
3. A one-line highlight of the candidate’s relevant experience.

Job Description:
\"\"\"{jd_text}\"\"\"

{batch_prompts}

Format output as:

Resume 1:
Summary: ...
Relevant Skills:
- ...
Main Highlight: ...

Resume 2:
...
"""

    try:
        response = ollama.chat(
            model="llama3.2",
            messages=[{"role": "user", "content": prompt}]
        )
        return response['message']['content'].strip()
    except Exception as e:
        return f"Error: {e}"

def summarize_resumes_with_ollama(jd_text, resume_texts):
    batch_size = 3
    results = []
    for i in range(0, len(resume_texts), batch_size):
        batch = resume_texts[i:i + batch_size]
        result = summarize_resume_with_jd(jd_text, batch)
        results.append(result)
    return "\n\n".join(results)
