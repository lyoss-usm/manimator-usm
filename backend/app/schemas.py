from typing import Any, TypedDict

from pydantic import BaseModel


class RenderRequest(BaseModel):
    f_tex: str
    a_tex: str
    b_tex: str
    include_tangent: bool
    scene_config: SceneConfig

    
class SceneConfig(TypedDict):
    preserve_aspect_ratio: bool