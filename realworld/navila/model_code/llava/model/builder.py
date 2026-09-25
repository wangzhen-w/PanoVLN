"""NaVILA's official component loader, restricted to full navigation checkpoints."""
import torch
from transformers import AutoConfig
from llava.model import LlavaLlamaModel
from llava.constants import DEFAULT_IMAGE_PATCH_TOKEN, DEFAULT_IM_START_TOKEN, DEFAULT_IM_END_TOKEN

def load_pretrained_model(model_path,model_name='navila',model_base=None,device_map='auto',device='cuda',**kwargs):
    if model_base is not None:
        raise ValueError('Use a full NaVILA checkpoint containing llm, vision_tower and mm_projector')
    config=AutoConfig.from_pretrained(model_path)
    config.resume_path=model_path
    config._name_or_path=model_path
    if getattr(config,'vision_tower_cfg',None) is None:
        config.vision_tower_cfg=config.mm_vision_tower
    config.model_dtype='torch.float16'
    vision_tower=kwargs.pop('vision_tower',None)
    if vision_tower: config.vision_tower_cfg=vision_tower
    model=LlavaLlamaModel(config=config,low_cpu_mem_usage=True,device_map=device_map,**kwargs).eval()
    tokenizer=model.tokenizer
    if getattr(config,'mm_use_im_patch_token',True): tokenizer.add_tokens([DEFAULT_IMAGE_PATCH_TOKEN],special_tokens=True)
    if getattr(config,'mm_use_im_start_end',False): tokenizer.add_tokens([DEFAULT_IM_START_TOKEN,DEFAULT_IM_END_TOKEN],special_tokens=True)
    model.resize_token_embeddings(len(tokenizer))
    model.get_vision_tower().to(device=device,dtype=torch.float16)
    model.get_mm_projector().to(device=device,dtype=torch.float16)
    return tokenizer,model,model.get_vision_tower().image_processor,getattr(model.llm.config,'max_sequence_length',2048)
