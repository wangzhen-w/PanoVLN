"""PanoVLN server settings, importable without loading model libraries."""
from dataclasses import dataclass
from typing import Optional

DEFAULT_MODEL_PATH = "./checkpoints/PanoVLN_realworld"

@dataclass
class InferenceConfig:
    model_path: str = DEFAULT_MODEL_PATH
    panovggt_checkpoint_path: Optional[str] = None
    attn_implementation: Optional[str] = "flash_attention_2"
