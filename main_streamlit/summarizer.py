import os
import json
import ollama
from math import ceil
from langchain_ollama import ChatOllama
import shutil
import re

llm = ChatOllama(model='llama3.2')

SUMMARY_DIR = os.path.join("uploaded_data", "summaries")
os.makedirs(SUMMARY_DIR, exist_ok=True)

def clear_summaries():
    """Delete all existing summaries to force regeneration"""
    if os.path.exists(SUMMARY_DIR):
        shutil.rmtree(SUMMARY_DIR)
    os.makedirs(SUMMARY_DIR, exist_ok=True)

def summarize_batch_with_ollama(jd_text, resume_batch, resume_names):
    batch_prompts = ""
    for idx, (resume_text, resume_name) in enumerate(zip(resume_batch, resume_names), start=1):
        batch_prompts += f"\nRESUME_{idx}_START\n{resume_text}\nRESUME_{idx}_END\n"

    prompt = f"""
You are an expert recruiter evaluating candidates. For EACH resume provided, you MUST generate a summary using the EXACT format below.

For each resume, your response MUST start with [RESUME_SUMMARY_START] and end with [RESUME_SUMMARY_END].
You MUST provide a summary for EVERY resume, maintaining the exact order they were provided in.

Format for EACH resume:

[RESUME_SUMMARY_START]
📝 Relevance:
<1-2 sentences stating if and how the candidate's background matches the job requirements. Be direct about their fit or lack of fit.>

🔧 JD-Matched Skills:
• <skill 1>: <brief explanation of how this skill matches a specific JD requirement>
• <skill 2>: <brief explanation of how this skill matches a specific JD requirement>
• <skill 3>: <brief explanation of how this skill matches a specific JD requirement>
• <skill 4>: <brief explanation of how this skill matches a specific JD requirement>
[RESUME_SUMMARY_END]

Job Description:
{jd_text}

{batch_prompts}

Important Instructions:
1. You MUST generate a summary for EACH resume in the same order they were provided
2. Each summary MUST be wrapped in [RESUME_SUMMARY_START] and [RESUME_SUMMARY_END] markers
3. Each summary MUST include ALL section emojis (📝, 🔧)
4. For Relevance: Be direct about whether the candidate is a good fit or not
5. For Skills: Only list skills that SPECIFICALLY match JD requirements
6. If fewer than 4 relevant skills found, still list all matches but note "Limited relevant skills found"
7. DO NOT skip any resumes
8. DO NOT add any text between summaries
9. You MUST generate exactly {len(resume_batch)} summaries, one for each resume
"""

    try:
        response = ollama.chat(
            model='llama3.2',
            messages=[{"role": "user", "content": prompt}]
        )
        return response['message']['content'].strip()
    except Exception as e:
        return f"Error: {e}"

def parse_batch_summaries(batch_text):
    """Parse the batch response into individual summaries using strict markers"""
    summaries = []
    
    # Split by summary markers
    parts = batch_text.split('[RESUME_SUMMARY_START]')
    
    # Process each part (skip the first as it's before any marker)
    for part in parts[1:]:
        if '[RESUME_SUMMARY_END]' in part:
            summary = part.split('[RESUME_SUMMARY_END]')[0].strip()
            if summary:
                # Clean up any extra whitespace or newlines
                summary = re.sub(r'\n\s*\n\s*\n+', '\n\n', summary)
                summary = re.sub(r'^\s+', '', summary, flags=re.MULTILINE)
                summaries.append(summary)
    
    return summaries

def format_summary(summary_text):
    """Format the summary text for better display"""
    # The summary should already be properly formatted from the LLM
    # Just clean up any extra whitespace and ensure consistent newlines
    summary_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', summary_text)
    summary_text = re.sub(r'^\s+', '', summary_text, flags=re.MULTILINE)
    
    # Ensure each section has proper spacing
    sections = summary_text.split('\n\n')
    formatted_sections = []
    
    for section in sections:
        if section.strip():
            if '📝 Relevance:' in section:
                formatted_sections.append(section.strip())
            elif '🔧 JD-Matched Skills:' in section:
                # Ensure bullet points are properly formatted
                lines = section.split('\n')
                formatted_skills = [lines[0]]  # Add the header
                for line in lines[1:]:
                    if line.strip():
                        if not line.strip().startswith('•'):
                            line = f"• {line.strip()}"
                        formatted_skills.append(line.strip())
                formatted_sections.append('\n'.join(formatted_skills))
    
    return '\n\n'.join(formatted_sections)

def summarize_resumes_with_jd(resume_texts, jd_text, resume_names, jd_file):
    batch_size = 2  # Reduced batch size for better reliability
    all_summaries = []
    
    # First, check for existing summaries and collect resumes that need processing
    new_resume_texts = []
    new_resume_names = []
    processed_names = set()  # Keep track of processed resumes
    
    for resume_text, resume_name in zip(resume_texts, resume_names):
        summary_filename = f"{jd_file}_{resume_name}.txt".replace(" ", "_")
        summary_path = os.path.join(SUMMARY_DIR, summary_filename)
        
        if os.path.exists(summary_path):
            # Load existing summary
            with open(summary_path, 'r', encoding='utf-8') as f:
                all_summaries.append((resume_name, f.read()))
                processed_names.add(resume_name)
        else:
            # Add to list for processing
            new_resume_texts.append(resume_text)
            new_resume_names.append(resume_name)
    
    # Process resumes in smaller batches
    for i in range(0, len(new_resume_texts), batch_size):
        batch_texts = new_resume_texts[i:i+batch_size]
        batch_names = new_resume_names[i:i+batch_size]
        
        # Process the batch
        batch_result = summarize_batch_with_ollama(jd_text, batch_texts, batch_names)
        individual_summaries = parse_batch_summaries(batch_result)
        
        # Process each resume in the batch
        for j, (text, name) in enumerate(zip(batch_texts, batch_names)):
            if name in processed_names:
                continue  # Skip if already processed
                
            # Try to get summary from batch result first
            summary = individual_summaries[j] if j < len(individual_summaries) else None
            
            # If no summary from batch, process individually
            if not summary:
                print(f"Processing {name} individually...")
                single_result = summarize_batch_with_ollama(jd_text, [text], [name])
                single_summaries = parse_batch_summaries(single_result)
                if single_summaries:
                    summary = single_summaries[0]
            
            # If we have a summary, format and save it
            if summary:
                formatted_summary = format_summary(summary)
                summary_filename = f"{jd_file}_{name}.txt".replace(" ", "_")
                summary_path = os.path.join(SUMMARY_DIR, summary_filename)
                with open(summary_path, 'w', encoding='utf-8') as f:
                    f.write(formatted_summary)
                all_summaries.append((name, formatted_summary))
                processed_names.add(name)
    
    # Verify all resumes were processed
    missing_resumes = set(resume_names) - processed_names
    if missing_resumes:
        print(f"Warning: Some resumes were not processed: {missing_resumes}")
        # Process any missing resumes individually
        for name in missing_resumes:
            idx = resume_names.index(name)
            text = resume_texts[idx]
            print(f"Attempting to process missing resume: {name}")
            single_result = summarize_batch_with_ollama(jd_text, [text], [name])
            single_summaries = parse_batch_summaries(single_result)
            if single_summaries:
                formatted_summary = format_summary(single_summaries[0])
                summary_filename = f"{jd_file}_{name}.txt".replace(" ", "_")
                summary_path = os.path.join(SUMMARY_DIR, summary_filename)
                with open(summary_path, 'w', encoding='utf-8') as f:
                    f.write(formatted_summary)
                all_summaries.append((name, formatted_summary))
    
    # Sort summaries to maintain original order
    all_summaries.sort(key=lambda x: resume_names.index(x[0]))
    return all_summaries

# Keep the original single resume function for backward compatibility
def summarize_resume_with_jd(resume_text, jd_text, resume_file, jd_file):
    summary_filename = f"{jd_file}_{resume_file}.txt".replace(" ", "_")
    summary_path = os.path.join(SUMMARY_DIR, summary_filename)

    if os.path.exists(summary_path):
        with open(summary_path, 'r', encoding='utf-8') as f:
            return f.read()

    # Use the batch function with a single resume
    summaries = summarize_resumes_with_jd([resume_text], jd_text, [resume_file], jd_file)
    return summaries[0][1] if summaries else "Error generating summary"
