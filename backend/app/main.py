import os
import logging
from typing import Dict, Any, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.app.phase1_ingestion.cloner import RepoCloner
from backend.app.phase1_ingestion.repo_db import RepoDatabaseService
from backend.app.pipeline import CodeArchaeologistPipeline
from backend.app.utils.sample_generator import create_sample_repository
from backend.app.models.schemas import (
    RAGAnswerResponse,
    BlastRadiusResult,
    ChangeImpactPrediction,
    OverallEvaluation,
    SoftwareGraph,
    SoftwareTimeline,
    FileEvolution
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("CodeArchaeologist")

app = FastAPI(
    title="CodeArchaeologist API",
    description="AI-Powered Software Evolution & Legacy Code Intelligence Engine",
    version="1.0.0"
)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

# Enable CORS for developer dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

# In-memory pipeline cache
pipelines: Dict[str, CodeArchaeologistPipeline] = {}
db_service = RepoDatabaseService()
cloner = RepoCloner()

class IngestRequest(BaseModel):
    repo_url_or_path: str
    force_reclone: bool = False

class ChatRequest(BaseModel):
    question: str

def get_or_load_pipeline(repo_id: str) -> CodeArchaeologistPipeline:
    if repo_id in pipelines:
        return pipelines[repo_id]
    
    # Check DB
    repo_info = db_service.get_repository(repo_id)
    if not repo_info:
        raise HTTPException(status_code=404, detail=f"Repository '{repo_id}' not found.")
    
    pipeline = CodeArchaeologistPipeline(repo_id, repo_info["path"])
    pipeline.run_full_pipeline()
    pipelines[repo_id] = pipeline
    return pipeline

@app.get("/")
def root():
    index_html = FRONTEND_DIST / "index.html"
    if index_html.exists():
        return FileResponse(str(index_html))
    return {
        "system": "CodeArchaeologist",
        "tagline": "AI-Powered Software Evolution & Legacy Code Intelligence",
        "status": "ready"
    }

@app.get("/api/health")
def health():
    return {
        "system": "CodeArchaeologist",
        "tagline": "AI-Powered Software Evolution & Legacy Code Intelligence",
        "status": "ready",
        "phases_active": [
            "Phase 1: Repository Ingestion",
            "Phase 2: Code Understanding & AST",
            "Phase 3: Architecture & Call Graph",
            "Phase 4: Software Archaeology",
            "Phase 5: Knowledge Layer & Evidence RAG",
            "Phase 6: Blast Radius & ML Prediction",
            "Phase 7: Evaluation Engine",
            "Phase 8: Developer Dashboard"
        ]
    }

@app.post("/api/ingest")
def ingest_repository(req: IngestRequest):
    try:
        repo_id, local_path, meta = cloner.clone_or_load(req.repo_url_or_path, req.force_reclone)
        pipeline = CodeArchaeologistPipeline(repo_id, local_path)
        summary = pipeline.run_full_pipeline()
        pipelines[repo_id] = pipeline
        return {
            "success": True,
            "repo_id": repo_id,
            "meta": meta,
            "summary": summary
        }
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/load-sample")
def load_sample():
    """
    Creates and analyzes the rich 2022-2026 enterprise ecommerce repository.
    """
    try:
        sample_path = create_sample_repository()
        repo_id = "sample_enterprise_ecommerce"
        pipeline = CodeArchaeologistPipeline(repo_id, sample_path)
        summary = pipeline.run_full_pipeline()
        pipelines[repo_id] = pipeline
        return {
            "success": True,
            "repo_id": repo_id,
            "summary": summary
        }
    except Exception as e:
        logger.error(f"Sample load failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/repositories")
def list_repositories():
    return db_service.list_repositories()

@app.get("/api/repo/{repo_id}/files")
def get_files(repo_id: str):
    pipeline = get_or_load_pipeline(repo_id)
    return {
        "repo_id": repo_id,
        "files": pipeline.files_data
    }

@app.get("/api/repo/{repo_id}/file-content")
def get_file_content(repo_id: str, path: str = Query(...)):
    content_info = db_service.get_file_content(repo_id, path)
    if not content_info:
        raise HTTPException(status_code=404, detail="File not found")
    return content_info

@app.get("/api/repo/{repo_id}/graph", response_model=SoftwareGraph)
def get_graph(repo_id: str):
    pipeline = get_or_load_pipeline(repo_id)
    return pipeline.software_graph

@app.get("/api/repo/{repo_id}/timeline", response_model=SoftwareTimeline)
def get_timeline(repo_id: str):
    pipeline = get_or_load_pipeline(repo_id)
    return pipeline.timeline

@app.get("/api/repo/{repo_id}/file-intelligence", response_model=FileEvolution)
def get_file_intelligence(repo_id: str, file_path: str = Query(...)):
    pipeline = get_or_load_pipeline(repo_id)
    return pipeline.evolution_archaeologist.get_file_evolution(repo_id, file_path)

@app.get("/api/repo/{repo_id}/blast-radius", response_model=BlastRadiusResult)
def calculate_blast_radius(repo_id: str, target_file: str = Query(...)):
    pipeline = get_or_load_pipeline(repo_id)
    return pipeline.blast_calculator.calculate_blast_radius(target_file)

@app.get("/api/repo/{repo_id}/predict-impact", response_model=ChangeImpactPrediction)
def predict_change_impact(repo_id: str, target_file: str = Query(...)):
    pipeline = get_or_load_pipeline(repo_id)
    return pipeline.change_predictor.predict_impact(target_file)

@app.post("/api/repo/{repo_id}/ask", response_model=RAGAnswerResponse)
def ask_ai(repo_id: str, req: ChatRequest):
    pipeline = get_or_load_pipeline(repo_id)
    return pipeline.rag_engine.answer_question(req.question)

@app.get("/api/repo/{repo_id}/evaluation", response_model=OverallEvaluation)
def get_evaluation(repo_id: str):
    pipeline = get_or_load_pipeline(repo_id)
    return pipeline.evaluation_result
