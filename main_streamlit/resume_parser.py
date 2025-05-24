import os
import PyPDF2
import re

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

def extract_email(text):
    match = re.search(r"[\w\.-]+@[\w\.-]+", text)
    return match.group(0) if match else "N/A"
