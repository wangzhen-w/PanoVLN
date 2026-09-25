from .siglip_encoder import SigLipVisionTower
from .clip_encoder import CLIPVisionTower

def build_vision_tower(config, **kwargs):
    name=getattr(config,'mm_vision_tower',getattr(config,'vision_tower',None))
    if 'siglip' in name.lower():
        return SigLipVisionTower(name,vision_tower_cfg=config,**kwargs)
    if 'clip' in name.lower():
        return CLIPVisionTower(name,args=config,**kwargs)
    raise ValueError(f'Unsupported StreamVLN vision tower: {name}; expected the official SigLIP/CLIP backbone')
