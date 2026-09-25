"""StreamVLN streaming conversations, KV cache and periodic memory injection."""
from .common import BasePredictor, InferenceConfig, parse_discrete
DEFAULT_MODEL_PATH='./checkpoints/StreamVLN'

class Predictor(BasePredictor):
    method='StreamVLN'
    action_sequence_length=4

    def load(self):
        from .runtime_paths import activate_model_code
        activate_model_code()
        import torch
        import json
        from pathlib import Path
        from transformers import AutoTokenizer
        from llava.model.language_model.llava_qwen import LlavaQwenConfig
        from streamvln.model.stream_video_vln import StreamVLNForCausalLM
        self.tokenizer=AutoTokenizer.from_pretrained(self.config.model_path,model_max_length=4096,padding_side='right')
        config=LlavaQwenConfig.from_pretrained(self.config.model_path)
        indexes=list(Path(self.config.model_path).glob('*.index.json'))
        config.vision_tower_from_checkpoint=self.config.vision_tower is None and any(
            any(key.startswith('model.vision_tower.vision_tower.') for key in json.loads(p.read_text()).get('weight_map',{}))
            for p in indexes
        )
        if self.config.vision_tower: config.mm_vision_tower=self.config.vision_tower
        self.model=StreamVLNForCausalLM.from_pretrained(self.config.model_path,config=config,
            dtype=torch.bfloat16,attn_implementation=self.config.attn_implementation,
            device_map={'':str(self.device)})
        self.model.model.num_history=self.config.num_history
        tower=self.model.get_vision_tower()
        if not getattr(tower,'is_loaded',True): tower.load_model()
        self.model.requires_grad_(False)
        self.model.to(self.device).eval()
        self.image_processor=tower.image_processor
        self.tokenizer.add_tokens(['<image>'],special_tokens=True)
        self.tokenizer.add_tokens(['<memory>'],special_tokens=True)
        self.model.reset(1)

    def reset(self):
        super().reset()
        self.model.reset_for_env(0)
        self.output_ids=None
        self.past_key_values=None
        self.cache_window=-1
        self.window_start=0

    def infer(self,instruction,new_images):
        import numpy as np
        import torch
        from .stream_prompt import preprocess_qwen
        step=len(self.images)-1
        window=step//self.config.num_frames
        if window!=self.cache_window:
            self.model.reset_for_env(0)
            self.output_ids=None
            self.past_key_values=None
            self.cache_window=window
            self.window_start=step
        if self.output_ids is None:
            text=('You are an autonomous navigation assistant. Your task is to <instruction>. '
                  'Devise an action sequence to follow the instruction using the four actions: '
                  'TURN LEFT (←) or TURN RIGHT (→) by 15 degrees, MOVE FORWARD (↑) by 25 centimeters, or STOP.')
            if step: text+=' You have visited these areas <memory>.'
            text=text.replace('<instruction>.',instruction)
            sources=[{'from':'human','value':text},{'from':'gpt','value':''}]
            add_system=True
        else:
            sources=[{'from':'human','value':''},{'from':'gpt','value':''}]
            add_system=False
        inputs,_=preprocess_qwen([sources],self.tokenizer,add_system=add_system)
        inputs=inputs.to(self.device)
        if self.output_ids is not None: inputs=torch.cat([self.output_ids,inputs],dim=1)
        selected=[self.images[-1]]
        if self.output_ids is None and step:
            # Exactly num_history frames before current observation. This is the
            # official stride sampling at normal 32-step reset boundaries.
            indices=np.linspace(0,step,num=self.config.num_history,endpoint=False,dtype=int)
            selected=[self.images[i] for i in indices]+selected
        pixels=torch.stack([self.image_processor.preprocess(images=im,return_tensors='pt')['pixel_values'][0]
                            for im in selected]).unsqueeze(0).to(self.device,dtype=torch.bfloat16)
        output,elapsed=self.generate(self.model.generate,inputs=inputs,images=pixels,
            depths=None,poses=None,intrinsics=None,env_id=0,time_ids=[list(range(self.window_start,step+1))],
            task_ids=[0],do_sample=False,num_beams=1,max_new_tokens=128,use_cache=True,
            return_dict_in_generate=True,past_key_values=self.past_key_values)
        self.output_ids=output.sequences
        self.past_key_values=output.past_key_values
        text=self.tokenizer.batch_decode(self.output_ids,skip_special_tokens=False)[0].strip()
        return text,len(selected),elapsed

    def parse(self,text):
        return parse_discrete(text,4)
