from sqlalchemy import Column, Integer, String, Float, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class ResumeScore(Base):
    __tablename__ = "resume_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    jd_name = Column(String, index=True)
    resume_name = Column(String, index=True)
    email = Column(String)
    score = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

class JobDescription(Base):
    __tablename__ = "job_descriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./resume_analyzer.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 