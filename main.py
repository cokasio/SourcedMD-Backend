"""
SourcedMD Medical Intelligence Backend
FastAPI service — port 8000

Endpoints:
  POST /api/healthcare/analyze   — master analysis endpoint
  POST /api/research/medical     — PubMed search + GRADE grading
  GET  /api/clinical-trials/search — ClinicalTrials.gov search
  POST /api/consensus/specialists — 62-specialist parallel consensus
  GET  /health                   — health check
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from routers import research, trials, consensus, healthcare, denials

load_dotenv()

app = FastAPI(
    title="SourcedMD Medical Intelligence API",
    description="GRADE-graded medical research. Not a clinical tool — a research tool.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research.router, prefix="/api")
app.include_router(trials.router, prefix="/api")
app.include_router(consensus.router, prefix="/api")
app.include_router(healthcare.router, prefix="/api")
app.include_router(denials.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "healthy", "service": "sourcedmd-backend", "version": "1.0.0"}


@app.get("/")
def root():
    return {
        "service": "SourcedMD Medical Intelligence API",
        "endpoints": {
            "health": "/health",
            "analyze": "POST /api/healthcare/analyze",
            "research": "POST /api/research/medical",
            "trials": "GET /api/clinical-trials/search",
            "consensus": "POST /api/consensus/specialists",
        }
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
