from typing import Any

from celery import Celery

from app.manim_generator import render_scene

celery_app = Celery(
    "tasks",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)

@celery_app.task(bind=True)
def render_manim_task(
    self: Celery,
    f_tex: str,
    a_tex: str,
    b_tex: str,
    include_tangent: bool,
    scene_config: dict[str, Any],
) -> str:
    scene_dict = {
        "tracing": True,
        "tangent": include_tangent,
    }
    scene_urls = {key: None for key in scene_dict}
    for scene_key, render in scene_dict.items():
        if render:
            video_path = render_scene(f_tex, a_tex, b_tex, scene_key, scene_config)
            scene_urls[scene_key] = video_path
            self.update_state(state="PROGRESS", meta=scene_urls)
    
    return scene_urls