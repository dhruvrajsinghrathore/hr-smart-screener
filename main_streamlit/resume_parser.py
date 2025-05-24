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
    """Extract email from text using robust pattern matching"""
    # First try to find email with domain tamu.edu specifically since it has special format
    tamu_pattern = r'(?:^|[^\w@])([a-zA-Z]+_?\d+@tamu\.edu)'
    tamu_match = re.search(tamu_pattern, text.lower())
    if tamu_match:
        return tamu_match.group(1)
    
    # Then try to find email with common academic domains
    academic_pattern = r'(?:^|[^\w@])([\w\.-]+(?:_[\w\.-]+)*@(?:[\w-]+\.)+(?:edu|ac\.[\w]{2,}))'
    academic_match = re.search(academic_pattern, text.lower())
    if academic_match:
        return academic_match.group(1)
    
    # Finally try to find any email
    email_pattern = r'(?:^|[^\w@])([\w\.-]+(?:_[\w\.-]+)*@[\w\.-]+\.\w+)'
    match = re.search(email_pattern, text.lower())
    if match:
        email = match.group(1)
        # Remove any unwanted prefixes
        if email.startswith('t') and '@' in email[1:]:
            email = email[1:]
        return email
    
    return ""
