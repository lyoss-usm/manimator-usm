import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.schemas import RenderRequest
from app.tasks import render_manim_task
from celery.result import AsyncResult
from app.tasks import celery_app

MEDIA_DIR = "/manim/media/videos/720p30"
os.makedirs(MEDIA_DIR, exist_ok=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/videos", StaticFiles(directory=MEDIA_DIR), name="videos")

@app.post("/render")
def render(req: RenderRequest):
    task = render_manim_task.delay(req.f_tex, req.a_tex, req.b_tex, req.included_scenes, req.scene_config)
    return {"task_id": task.id}

@app.get("/status/{task_id}")
def get_status(task_id: str):
    result = AsyncResult(task_id, app=celery_app)

    if result.state == "PENDING":
        return {"status": "pending"}
    elif result.state == "SUCCESS":
        return {"status": "done", "video_urls": result.result}
    elif result.state == "PROGRESS":
        return {"status": "progress", "video_urls": result.result}
    elif result.state == "FAILURE":
        return {"status": "error", "error": str(result.result)}
    else:
        return {"status": result.state}