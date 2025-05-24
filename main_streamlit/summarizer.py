import os
from langchain_ollama import ChatOllama

llm = ChatOllama(model='llama3.2')

SUMMARY_DIR = os.path.join("uploaded_data", "summaries")
os.makedirs(SUMMARY_DIR, exist_ok=True)

def summarize_resume_with_jd(resume_text, jd_text, resume_file, jd_file):
    summary_filename = f"{jd_file}_{resume_file}.txt".replace(" ", "_")
    summary_path = os.path.join(SUMMARY_DIR, summary_filename)

    if os.path.exists(summary_path):
        with open(summary_path, 'r', encoding='utf-8') as f:
            return f.read()

    prompt = f"""
You are an AI assistant. Given the following resume and job description, generate a professional summary and key skills:

Job Description:
{jd_text}

Resume:
{resume_text[:2000]}

Return in this format:
Summary: <brief summary paragraph>
Key Skills: <comma-separated skills>
Experience: <brief experience sentence>
"""
    try:
        response = llm.invoke(prompt)
        summary_block = response.content.strip()
        summary_start = summary_block.find("Professional Summary:")
        final_summary = summary_block[summary_start:].strip() if summary_start != -1 else summary_block

        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(final_summary)

        return final_summary
    except Exception as e:
        return f"Error: {e}"
