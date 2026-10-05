"""FastAPI app for the learning service (AI that learns from the user's ratings).

Run:  uvicorn app.main:app --port 8003   (from learning_service/)
Env:  LEARNING_DATA_DIR (default ./data), LEARNING_LLM=auto|off (default auto)
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import ErrorBody, Feedback, FeedbackAck, FeedbackIn, Profile, ProfileAck
from .service import LearningService
from .store import LearningStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

SERVICE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="MobiusFinance learning service", version="0.1.0",
              description="Learns a per-project profile from brief ratings and notes. No UI.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST", "DELETE"], allow_headers=["*"])


@lru_cache
def get_service() -> LearningService:
    root = Path(os.getenv("LEARNING_DATA_DIR", SERVICE_DIR / "data"))
    use_llm = os.getenv("LEARNING_LLM", "auto").strip().lower() not in {"off", "0", "false", "no"}
    return LearningService(LearningStore(root), use_llm=use_llm)


@app.exception_handler(RequestValidationError)
async def _validation(_: Request, e: RequestValidationError):
    msg = "; ".join(f"{'.'.join(str(x) for x in err['loc'][1:])}: {err['msg']}" for err in e.errors())
    return JSONResponse(status_code=422, content={"error": "invalid_parameter", "detail": msg})


@app.get("/health")
def health(svc: LearningService = Depends(get_service)):
    return {"status": "ok", "llm": svc.use_llm}


@app.post("/feedback", response_model=FeedbackAck, responses={422: {"model": ErrorBody}})
def add_feedback(req: FeedbackIn, background: BackgroundTasks, svc: LearningService = Depends(get_service)):
    fb = svc.add(req)
    # The rule profile is updated immediately; the LLM summary follows in the background.
    background.add_task(svc.refresh_llm, fb.project_id)
    return FeedbackAck(**fb.model_dump(), feedback_count=len(svc.store.feedback(fb.project_id)))


@app.get("/feedback", response_model=list[Feedback])
def list_feedback(project_id: str = "default", svc: LearningService = Depends(get_service)):
    return svc.feedback(project_id)


@app.get("/profile", response_model=Profile)
def get_profile(project_id: str = "default", svc: LearningService = Depends(get_service)):
    return svc.profile(project_id)


@app.delete("/profile", response_model=ProfileAck)
def forget(project_id: str = "default", svc: LearningService = Depends(get_service)):
    svc.forget(project_id)
    return ProfileAck(**svc.profile(project_id).model_dump())


@app.post("/demo/seed", response_model=Profile)
def seed_demo(project_id: str = "demo", svc: LearningService = Depends(get_service)):
    """Load the scripted demo feedback (2 ratings) into a project; works offline."""
    return svc.seed_demo(project_id)
