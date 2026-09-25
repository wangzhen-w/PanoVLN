"""Official full-checkpoint NaVid loader with portable vision asset overrides."""
from pathlib import Path
import json
import torch
from transformers import AutoTokenizer
from navid.model.language_model.llava_navid import LlavaConfig
from navid.model import LlavaLlamaAttForCausalLM
from navid.constants import DEFAULT_IMAGE_PATCH_TOKEN, DEFAULT_IM_START_TOKEN, DEFAULT_IM_END_TOKEN

def load_pretrained_model(model_path,model_base=None,model_name='navid',device_map='auto',device='cuda',
                          vision_tower=None,image_processor=None):
    if model_base is not None:
        raise ValueError('Use a merged/full NaVid navigation checkpoint')
    config=LlavaConfig.from_pretrained(model_path)
    indexes=list(Path(model_path).glob('*.index.json'))
    config.vision_tower_from_checkpoint=vision_tower is None and any(
        any(key.startswith('model.vision_tower.vision_tower.') for key in json.loads(p.read_text()).get('weight_map',{}))
        for p in indexes
    )
    if vision_tower is not None: config.mm_vision_tower=vision_tower
    if image_processor is not None:
        config.image_processor=image_processor
    elif getattr(config,'image_processor',None):
        # Resolve the official bundled processor relative to this checkout.
        relative=Path(config.image_processor)
        local=Path(__file__).resolve().parents[2]/relative
        if local.exists(): config.image_processor=str(local)
    tokenizer=AutoTokenizer.from_pretrained(model_path,use_fast=False)
    model=LlavaLlamaAttForCausalLM.from_pretrained(model_path,config=config,
                                                dtype=torch.float16,device_map=device_map,attn_implementation="eager")
    if getattr(config,'mm_use_im_patch_token',True):
        tokenizer.add_tokens([DEFAULT_IMAGE_PATCH_TOKEN],special_tokens=True)
    if getattr(config,'mm_use_im_start_end',False):
        tokenizer.add_tokens([DEFAULT_IM_START_TOKEN,DEFAULT_IM_END_TOKEN],special_tokens=True)
    model.resize_token_embeddings(len(tokenizer))
    tower=model.get_vision_tower()
    if not tower.is_loaded: tower.load_model()
    tower.to(device=device,dtype=torch.float16)
    model.config.model_path=model_path
    model.get_model().initialize_attention_modules(model.config,for_eval=True)
    return tokenizer,model,tower.image_processor,getattr(config,'max_sequence_length',2048)
