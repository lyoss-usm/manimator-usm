from typing import Any, TypedDict

from pydantic import BaseModel


class RenderRequest(BaseModel):
    f_tex: str
    a_tex: str
    b_tex: str
    included_scenes: dict[str, bool]
    scene_config: SceneConfig


class IncludeScenes(TypedDict):
    tracing: bool
    rotation: bool
    tangent: bool
    normal: bool

    
class SceneConfig(TypedDict):
    preserve_aspect_ratio: bool