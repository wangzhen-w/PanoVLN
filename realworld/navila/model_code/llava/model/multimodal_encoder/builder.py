from transformers import AutoConfig
from .siglip_encoder import SiglipVisionTower, SiglipVisionTowerS2
from .clip_encoder import CLIPVisionTower, CLIPVisionTowerS2

def build_vision_tower(model_name_or_path, config):
    if model_name_or_path is None: return None
    architecture=AutoConfig.from_pretrained(model_name_or_path).architectures[0].lower()
    use_s2=getattr(config,'s2',False)
    if 'siglip' in architecture:
        cls=SiglipVisionTowerS2 if use_s2 else SiglipVisionTower
    elif 'clip' in architecture:
        cls=CLIPVisionTowerS2 if use_s2 else CLIPVisionTower
    else:
        raise ValueError(f'Unsupported NaVILA vision tower: {architecture}; expected official SigLIP/CLIP')
    tower=cls(model_name_or_path,config)
    config.mm_hidden_size=tower.hidden_size if use_s2 else tower.config.hidden_size
    return tower
