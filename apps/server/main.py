
from __future__ import annotations

import os
import uuid
from typing import Any

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import database as db
import worker
from fastapi.middleware.cors import CORSMiddleware

STORAGE_DIR = os.getenv("STORAGE_DIR", "/app/storage")

app = FastAPI(title="EchoInsight API")
db.init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    session = db.SessionLocal()
    try:
        yield session
    finally:
        session.close()

class YoutubeIn(BaseModel):
    url: str = Field(min_length=5)

class AskIn(BaseModel):
    task_id: str
    question: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)

def _ensure_storage_dir() -> None:
    os.makedirs(STORAGE_DIR, exist_ok=True)

@app.post("/upload")
async def upload_media(file: UploadFile = File(...), dbs: Session = Depends(get_db)):
    _ensure_storage_dir()
    task_id = str(uuid.uuid4())
    safe_name = os.path.basename(file.filename or "upload.bin")
    dest_path = os.path.join(STORAGE_DIR, f"{task_id}__{safe_name}")

    # save file to shared storage volume
    with open(dest_path, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)

    new_task = db.MediaTask(
        id=task_id,
        filename=safe_name,
        status="PENDING",
        source_type="upload",
        storage_path=dest_path,
    )
    dbs.add(new_task)
    dbs.commit()
    
    # Task an Celery übergeben
    worker.process_audio_task.delay(task_id)
    
    return {"task_id": task_id, "status": "queued"}

@app.post("/youtube")
async def submit_youtube(payload: YoutubeIn, dbs: Session = Depends(get_db)):
    task_id = str(uuid.uuid4())
    new_task = db.MediaTask(
        id=task_id,
        filename="youtube",
        status="PENDING",
        source_type="youtube",
        source_url=payload.url,
    )
    dbs.add(new_task)
    dbs.commit()

    worker.process_audio_task.delay(task_id)
    return {"task_id": task_id, "status": "queued"}

@app.get("/status/{task_id}")
async def get_status(task_id: str, dbs: Session = Depends(get_db)):
    task = dbs.query(db.MediaTask).filter(db.MediaTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "id": task.id,
        "status": task.status,
        "filename": task.filename,
        "summary": task.summary_text or task.result_text,
        "transcript": task.transcript_text,
        "error": task.error_text,
    }

@app.get("/tasks")
async def list_tasks(dbs: Session = Depends(get_db)):
    return dbs.query(db.MediaTask).order_by(db.MediaTask.created_at.desc()).all()

@app.post("/ask")
async def ask_question(payload: AskIn, dbs: Session = Depends(get_db)) -> dict[str, Any]:
    task = dbs.query(db.MediaTask).filter(db.MediaTask.id == payload.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "COMPLETED":
        raise HTTPException(status_code=409, detail=f"Task not ready (status={task.status})")

    answer = worker.answer_question(dbs, payload.task_id, payload.question, top_k=payload.top_k)
    return answer


@app.post("/reprocess/{task_id}")
async def reprocess(task_id: str, dbs: Session = Depends(get_db)):
    task = dbs.query(db.MediaTask).filter(db.MediaTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not task.storage_path and not task.source_url:
        raise HTTPException(status_code=409, detail="Task has no source (no storage_path and no source_url)")

    task.status = "PENDING"
    task.error_text = None
    dbs.commit()

    worker.process_audio_task.delay(task_id)
    return {"task_id": task_id, "status": "queued"}
