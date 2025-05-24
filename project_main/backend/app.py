from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
import pandas as pd
from datetime import datetime
import os
import json
from sqlalchemy.orm import Session

from models import get_db, ResumeScore, JobDescription, Base, engine
from resume_utils import extract_text_from_pdf, extract_email
from match_engine import calculate_score
from summaries import summarize_resume_with_jd

# Ensure database tables are created
Base.metadata.create_all(bind=engine)

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory setup
UPLOAD_FOLDER = "uploads"
JD_FOLDER = os.path.join(UPLOAD_FOLDER, "jds")
RESUME_FOLDER = os.path.join(UPLOAD_FOLDER, "resumes")

# Ensure directories exist
for folder in [UPLOAD_FOLDER, JD_FOLDER, RESUME_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Mount uploads directory for static file serving
app.mount("/uploads", StaticFiles(directory=UPLOAD_FOLDER), name="uploads")

@app.post("/upload-jd")
async def upload_jd(
    jd_file: Optional[UploadFile] = None,
    jd_text: Optional[str] = Form(None),
    jd_name: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        if not jd_file and not jd_text:
            raise HTTPException(status_code=400, detail="Either file or text must be provided")
        
        content = jd_text if jd_text else (await jd_file.read()).decode()
        
        # Check if JD with same name exists
        existing_jd = db.query(JobDescription).filter(JobDescription.name == jd_name).first()
        if existing_jd:
            raise HTTPException(status_code=400, detail=f"Job description with name '{jd_name}' already exists")
        
        # Save to database
        jd = JobDescription(name=jd_name, content=content)
        db.add(jd)
        db.commit()
        
        # Save to file system
        jd_path = os.path.join(JD_FOLDER, f"{jd_name}.txt")
        with open(jd_path, "w", encoding='utf-8') as f:
            f.write(content)
        
        return {"message": "Job description saved successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jds")
async def get_jds(db: Session = Depends(get_db)):
    jds = db.query(JobDescription).all()
    return [{"name": jd.name, "timestamp": jd.timestamp} for jd in jds]

@app.delete("/jds/{jd_name}")
async def delete_jd(jd_name: str, db: Session = Depends(get_db)):
    jd = db.query(JobDescription).filter(JobDescription.name == jd_name).first()
    if jd:
        db.delete(jd)
        db.commit()
        
        # Delete file if exists
        jd_path = os.path.join(JD_FOLDER, f"{jd_name}.txt")
        if os.path.exists(jd_path):
            os.remove(jd_path)
        
        return {"message": "Job description deleted successfully"}
    raise HTTPException(status_code=404, detail="Job description not found")

@app.post("/analyze")
async def analyze_resumes(
    resumes: List[UploadFile] = File(...),
    jd_name: str = Form(...),
    db: Session = Depends(get_db)
):
    results = []
    jd = db.query(JobDescription).filter(JobDescription.name == jd_name).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")
    
    for resume in resumes:
        file_path = os.path.join(RESUME_FOLDER, resume.filename)
        content = await resume.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        resume_text = extract_text_from_pdf(file_path)
        email = extract_email(resume_text)
        score = calculate_score(resume_text, jd.content)
        
        # Save to database
        resume_score = ResumeScore(
            jd_name=jd_name,
            resume_name=resume.filename,
            email=email,
            score=float(score)
        )
        db.add(resume_score)
        db.commit()
        
        results.append({
            "resume_name": resume.filename,
            "email": email,
            "score": score,
            "timestamp": resume_score.timestamp
        })
    
    return results

@app.get("/scores/{jd_name}")
async def get_scores(jd_name: str, db: Session = Depends(get_db)):
    scores = db.query(ResumeScore).filter(ResumeScore.jd_name == jd_name).all()
    return [
        {
            "resume_name": score.resume_name,
            "email": score.email,
            "score": score.score,
            "timestamp": score.timestamp
        }
        for score in scores
    ]

@app.post("/summarize")
async def summarize(
    resume_names: List[str] = Form(...),
    jd_name: str = Form(...),
    db: Session = Depends(get_db)
):
    jd = db.query(JobDescription).filter(JobDescription.name == jd_name).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")
    
    summaries = []
    for resume_name in resume_names:
        resume_path = os.path.join(RESUME_FOLDER, resume_name)
        if not os.path.exists(resume_path):
            continue
        
        resume_text = extract_text_from_pdf(resume_path)
        summary = summarize_resume_with_jd(resume_text, jd.content)
        summaries.append({"resume_name": resume_name, "summary": summary})
    
    return summaries

@app.get("/export-scores")
async def export_scores(db: Session = Depends(get_db)):
    scores = db.query(ResumeScore).all()
    df = pd.DataFrame([
        {
            "jd_name": score.jd_name,
            "resume_name": score.resume_name,
            "email": score.email,
            "score": score.score,
            "timestamp": score.timestamp
        }
        for score in scores
    ])
    
    csv_path = os.path.join(UPLOAD_FOLDER, "scores_export.csv")
    df.to_csv(csv_path, index=False)
    return FileResponse(csv_path, filename="resume_scores.csv")
