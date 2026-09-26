import os
import uuid
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

tasks_status: Dict[str, Dict[str, Any]] = {}

def get_or_load_pipeline(repo_id: str, force_reanalyze: bool = False) -> CodeArchaeologistPipeline:
    if repo_id in pipelines and not force_reanalyze:
        return pipelines[repo_id]
    
    # Check DB
    repo_info = db_service.get_repository(repo_id)
    if not repo_info:
        raise HTTPException(status_code=404, detail=f"Repository '{repo_id}' not found.")
    
    pipeline = CodeArchaeologistPipeline(repo_id, repo_info["path"])
    if not force_reanalyze:
        loaded = pipeline.load_from_db()
        if loaded:
            logger.info(f"Loaded existing pipeline state for '{repo_id}' directly from SQLite database.")
            pipelines[repo_id] = pipeline
            return pipeline

    logger.info(f"Running full pipeline analysis for '{repo_id}'...")
    pipeline.run_full_pipeline()
    pipelines[repo_id] = pipeline
    return pipeline

def _run_ingest_background(task_id: str, repo_url_or_path: str, force_reclone: bool):
    tasks_status[task_id] = {"status": "processing", "progress": "Cloning repository..."}
    try:
        repo_id, local_path, meta = cloner.clone_or_load(repo_url_or_path, force_reclone)
        db_service.save_repository(
            repo_id=repo_id,
            name=meta.get("name", repo_id),
            path=local_path,
            url=meta.get("url", repo_url_or_path),
            default_branch=meta.get("default_branch", "main"),
            stats={}
        )
        tasks_status[task_id]["progress"] = f"Repository cloned. Running analysis for {repo_id}..."
        pipeline = CodeArchaeologistPipeline(repo_id, local_path)
        summary = pipeline.run_full_pipeline()
        pipelines[repo_id] = pipeline
        tasks_status[task_id] = {
            "status": "completed",
            "repo_id": repo_id,
            "summary": summary,
            "meta": meta
        }
    except Exception as e:
        logger.error(f"Async ingestion task {task_id} failed: {e}", exc_info=True)
        tasks_status[task_id] = {"status": "failed", "error": str(e)}

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
        db_service.save_repository(
            repo_id=repo_id,
            name=meta.get("name", repo_id),
            path=local_path,
            url=meta.get("url", req.repo_url_or_path),
            default_branch=meta.get("default_branch", "main"),
            stats={}
        )
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

@app.post("/api/ingest/async")
def ingest_repository_async(req: IngestRequest, bg_tasks: BackgroundTasks):
    import uuid
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    tasks_status[task_id] = {"status": "queued", "progress": "Queued for processing"}
    bg_tasks.add_task(_run_ingest_background, task_id, req.repo_url_or_path, req.force_reclone)
    return {"task_id": task_id, "status": "queued"}

@app.get("/api/tasks/{task_id}")
def get_task_status(task_id: str):
    if task_id not in tasks_status:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks_status[task_id]

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

@app.get("/{full_path:path}")
def catch_all(full_path: str):
    if full_path.startswith("api"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    file_candidate = FRONTEND_DIST / full_path
    if file_candidate.exists() and file_candidate.is_file():
        return FileResponse(str(file_candidate))
    index_html = FRONTEND_DIST / "index.html"
    if index_html.exists():
        return FileResponse(str(index_html))
    return {
        "system": "CodeArchaeologist",
        "tagline": "AI-Powered Software Evolution & Legacy Code Intelligence",
        "status": "ready"
    }
